import re
import json
import uuid
import psycopg2
from psycopg2.extras import execute_values

from django.db import connections
from django.conf import settings
from ninja import Router, Form, File
from ninja.files import UploadedFile

# Standardized Qdrant structure imports
import qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, MatchText

from rag.schemas import PromptInput
from rag.models import BIRDocument
from rag.utils import extract_text, chunk_text
from rag.embeddings import get_embedding
from chatbot_models.rag_model import openai_gpt45

router = Router(tags=["Internal BIR AI"])


def search_bir_knowledge_base(query_embedding, agent_name, user_question, limit=5, score_threshold=0.50):
    """
    Enhanced Hybrid Search using the updated Qdrant v1.10+ query_points API interface.
    """
    # 1. Advanced Regex for Document Extraction (Cleaned trailing characters)
    bir_pattern = r'\b(RMC|RAO|RDAO|RR|RMO|RAMO|CMC|Form|Sec|Section)\b\s*(?:No\.?)?\s*([\d\s\-–\/]+)'
    match = re.search(bir_pattern, user_question, re.IGNORECASE)
    
    query_filter = None
    
    if match:
        doc_type = match.group(1).upper()
        doc_num = match.group(2).strip()
        if doc_type == "SEC":
            doc_type = "SECTION"
            
        normalized_num = re.sub(r'^0+', '', doc_num)
        
        # Generate the 3 common ways a document title might be written
        topic_filter_clean = f"{doc_type} {normalized_num}"       # e.g., "RMC 63-2026"
        topic_filter_raw = f"{doc_type} {doc_num}"               # e.g., "RMC 63-2026"
        topic_filter_with_no = f"{doc_type} NO. {normalized_num}" # e.g., "RMC NO. 63-2026"

        query_filter = Filter(
            must=[FieldCondition(key="agent", match=MatchValue(value=agent_name))],
            should=[
                FieldCondition(key="topic_title", match=MatchText(text=topic_filter_clean)),
                FieldCondition(key="topic_title", match=MatchText(text=topic_filter_raw)),
                FieldCondition(key="topic_title", match=MatchText(text=topic_filter_with_no)) # <--- Added this safety net
            ]
        )
        print(f"--- QDRANT: Strict Filter Mode [{topic_filter_clean} / {topic_filter_with_no}] ---")
    else:
        query_filter = Filter(must=[FieldCondition(key="agent", match=MatchValue(value=agent_name))])
        print("--- QDRANT: General Semantic Mode ---")

    # 2. Setup Configuration
    config = settings.QDRANT_CONFIG
    collection_name = config.get("COLLECTION_NAME", "bir_rag_documents")
    
    # Initialize connection using the strict module class
    client = qdrant_client.QdrantClient(
        host=config["HOST"],
        port=config["PORT"],
        api_key=config["API_KEY"],
        prefer_grpc=False,
        https=False,
        check_compatibility=False
    )

    # Execute Search using the modern query_points interface
    response = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold
    )
    search_results = response.points

    # --- FALLBACK MECHANISM ---
    if not search_results and match:
        print("--- QDRANT WARNING: Strict match found 0 results. Retrying with pure Semantic Fallback... ---")
        response = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            query_filter=Filter(must=[FieldCondition(key="agent", match=MatchValue(value=agent_name))]),
            limit=limit,
            score_threshold=score_threshold
        )
        search_results = response.points

    if not search_results:
        return []

    # 3. Process Hits & Fetch PostgreSQL Metadata
    qdrant_data_map = {}
    topic_ids = set()
    
    for hit in search_results:
        p = hit.payload
        t_id = p.get("topic_id")
        if t_id:
            topic_ids.add(t_id)
            if t_id not in qdrant_data_map:
                qdrant_data_map[t_id] = []
            qdrant_data_map[t_id].append({
                "content": p.get("content"),
                "filename": p.get("filename"),
                "score": hit.score if hasattr(hit, 'score') else 1.0
            })

    enriched_docs = []
    postgres_metadata = {}
    
    if topic_ids:
        placeholders = ", ".join(["%s"] * len(topic_ids))
        sql_query = f"""
            SELECT id, topic_title, office_type, office_division, classification, uploaded_by
            FROM kx_topics WHERE id IN ({placeholders});
        """
        with connections['birai_db'].cursor() as cursor:
            cursor.execute(sql_query, list(topic_ids))
            rows = cursor.fetchall()
            for row in rows:
                postgres_metadata[row[0]] = {
                    "title": row[1], "office_type": row[2], "division": row[3], "classification": row[4], "uploaded_by": row[5]
                }

    # 4. Generate context payload for LLM window (With robust fallback)
    for topic_id, chunks in qdrant_data_map.items():
        # Fallback to standard placeholders if Postgres lookup returns nothing
        meta = postgres_metadata.get(topic_id, {
            "title": chunks[0].get("topic_title", "Unknown Document"), 
            "office_type": "N/A", 
            "division": "N/A", 
            "classification": "N/A", 
            "uploaded_by": "System"
        })
        
        for chunk in chunks:
            formatted_context = (
                f"Source Document: {meta['title']} ({chunk['filename']})\n"
                f"Extract Content:\n{chunk['content']}\n"
                f"---"
            )
            enriched_docs.append(formatted_context)
            
    return enriched_docs


@router.post("/ask-bir")
def ask_bir(request, data: Form[PromptInput], file: UploadedFile = File(None)):
    prompt = data.prompt

    # ==========================================
    # 1. UPLOAD MODE (INDEXING BACKWARDS COMPAT)
    # ==========================================
    if file:
        file_bytes = file.read()
        text = extract_text(file.name, file_bytes)
        text = text.replace("\x00", "").strip()
        chunks = chunk_text(text)

        indexed_count = 0
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk or len(chunk) < 30:
                continue

            embedding = get_embedding(chunk)
            embedding = [float(x) for x in embedding]

            BIRDocument.objects.using("birai_db").create(
                filename=file.name,
                content=chunk,
                chunk_index=i,
                embedding=embedding,
                chunk_length=len(chunk)
            )
            indexed_count += 1

        return {
            "response": f"Indexed {indexed_count} chunks into vector DB."
        }

    # ==========================================
    # 2. QUERY HYBRID RAG (INTEGRATED)
    # ==========================================
    agent_name = data.agent
    
    try:
        chat_history = json.loads(data.history)
    except Exception:
        chat_history = []

    try:
        query_embedding = get_embedding(prompt)
        docs = search_bir_knowledge_base(
            query_embedding=query_embedding, 
            agent_name=agent_name, 
            user_question=prompt, 
            limit=5
        )
        
        print(f"DEBUG: Found {len(docs)} integrated documents for agent '{agent_name}'")
        
        if docs:
            # Structuring the context cleanly so the LLM prompt wrapper reads it explicitly
            context = "\n\n".join(docs)
        else:
            print("DEBUG: docs list was completely empty.")
            context = "No relevant reference documents found in the database."
            
    except Exception as e:
        print(f"Search Integration Error: {e}")
        context = "No relevant reference documents found due to a system lookup error."

    # ==========================================
    # 3. Call Conversational LLM Pipeline
    # ==========================================
    # Force pass the valid context variable directly into the pipeline
    response = openai_gpt45(
        prompt=prompt, 
        context=context, 
        history=chat_history
    )

    # Return the direct answer string payload
    return {"response": response}


# ==========================================
# 3. UNIFIED KX INGESTION ENDPOINT
# ==========================================
@router.post("/ingest-knowledge")
def ingest_knowledge(
    request, 
    file: UploadedFile = File(...),
    title: str = Form(...),
    agent: str = Form(...),
    office_type: str = Form(""),
    division: str = Form(""),
    classification: str = Form(""),
    uploaded_by: str = Form("Admin")
):
    conn = None
    try:
        file_bytes = file.read()
        
        # 1. Extraction
        text_content = extract_text(file.name, file_bytes)
        if not text_content:
            return {"status": "error", "message": "Text extraction failed"}
            
        clean_content = text_content.replace('\x00', '').strip()
        chunks = chunk_text(clean_content, chunk_size=800, overlap=150)

        # 2. Database Connection Check
        conn = connections['birai_db']
        
        print(f"--- INGESTION START ---")
        print(f"Target DB: {conn.settings_dict.get('NAME')} @ {conn.settings_dict.get('HOST')}")
        print(f"File: {file.name} | Chunks: {len(chunks)}")

        with conn.cursor() as cursor:
            # 3. Insert Master Record into PostgreSQL
            cursor.execute("""
                INSERT INTO kx_topics (
                    topic_title, agent, office_type, office_division, 
                    classification, file_name, file_data, uploaded_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, [title, agent, office_type, division, classification, file.name, psycopg2.Binary(file_bytes), uploaded_by])
            
            topic_id = cursor.fetchone()[0]
            print(f"Master Record Created: ID {topic_id}")

            # 4. Standardized Client Initialization for Chunk Processing
            config = settings.QDRANT_CONFIG
            collection_name = config.get("COLLECTION_NAME", "bir_rag_documents")
            
            # Using 'client' prevents scoping conflicts with the module name 'qdrant_client'
            client = qdrant_client.QdrantClient(
                host=config["HOST"],
                port=config["PORT"],
                api_key=config["API_KEY"],
                prefer_grpc=False,
                https=False,
                check_compatibility=False
            )
            
            qdrant_points = []
            for idx, chunk in enumerate(chunks):
                if len(chunk.strip()) < 30: 
                    continue
                
                enriched_chunk = f"Document: {title}. Bureau of Internal Revenue Philippines. Section Content:\n{chunk}"
                vector = get_embedding(enriched_chunk)
                point_id = str(uuid.uuid4())
                
                qdrant_points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "topic_id": topic_id,
                            "topic_title": title,
                            "agent": agent,
                            "filename": file.name,
                            "content": chunk,
                            "chunk_index": idx,
                            "chunk_length": len(chunk),
                            "office_type": office_type,
                            "office_division": division,
                            "classification": classification
                        }
                    )
                )
            
            # 5. Bulk Insert into Qdrant Vector Engine with verified variable names
            if qdrant_points:
                client.upsert(
                    collection_name=collection_name,
                    wait=True,
                    points=qdrant_points
                )
                print(f"Inserted {len(qdrant_points)} vector chunks into Qdrant Container.")

        # 6. Force Commit relational records
        conn.commit()
        print(f"--- TRANSACTION COMMITTED ---")

        return {
            "status": "success", 
            "topic_id": topic_id, 
            "chunks": len(qdrant_points)
        }

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"!!! INGESTION ERROR: {str(e)}")
        return {"status": "error", "message": str(e)}