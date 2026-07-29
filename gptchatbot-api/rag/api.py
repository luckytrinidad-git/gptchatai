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
from rag.qdrant_backend import run_exact_document_lookup, run_semantic_search, semantic_with_fallback

from rag.schemas import PromptInput
from rag.models import BIRDocument
from rag.utils import extract_text, chunk_text, upload_to_ipfs
from rag.embeddings import get_embedding
from chatbot_models.rag_model import openai_gpt45

import os
from rag.utils import build_title_variants, normalize_document_number, extract_document_reference, DOCUMENT_MAP 

router = Router(tags=["Internal BIR AI"])

def search_bir_knowledge_base(
    query_embedding,
    agent_name,
    user_question,
    limit=5,
):
    """
    Enterprise retrieval pipeline.

    Stage 1
        Exact document lookup

    Stage 2
        Semantic search (70%)

    Stage 3
        Semantic fallback (50%)
    """

    ############################################################
    # CONNECT TO QDRANT
    ############################################################

    config = settings.QDRANT_CONFIG

    client = qdrant_client.QdrantClient(
        host=config["HOST"],
        port=config["PORT"],
        api_key=config["API_KEY"],
        https=False,
        prefer_grpc=False,
        check_compatibility=False,
    )

    collection_name = config.get(
        "COLLECTION_NAME",
        "bir_rag_documents",
    )

    ############################################################
    # DOCUMENT DETECTION
    ############################################################

    document = extract_document_reference(user_question)

    results = []
    match_type = "semantic"
    best_score = 0

    ############################################################
    # STAGE 1
    ############################################################

    if document:

        print("=" * 70)
        print("DOCUMENT DETECTED")
        print(document)
        print("=" * 70)

        results = run_exact_document_lookup(
            client=client,
            collection_name=collection_name,
            agent_name=agent_name,
            title_variants=document["variants"],
        )
        
        print("=" * 80)
        print("EXACT LOOKUP RESULTS")
        print("=" * 80)
            
        if results:

            match_type = "exact"

            # Exact lookup isn't vector-based.
            best_score = 1.0

    ############################################################
    # STAGE 2 + 3
    ############################################################

    if not results:

        (
            results,
            match_type,
            best_score,
        ) = semantic_with_fallback(
            client=client,
            collection_name=collection_name,
            embedding=query_embedding,
            agent_name=agent_name,
            limit=limit,
        )

    ############################################################
    # NOTHING FOUND
    ############################################################

    if not results:

        return {
            "contexts": [],
            "match_type": "none",
            "best_score": 0,
        }

    ############################################################
    # GROUP RESULTS
    ############################################################

    grouped = {}

    topic_ids = set()

    for hit in results:

        payload = hit.payload

        topic_id = payload.get("topic_id")

        if not topic_id:
            continue

        topic_ids.add(topic_id)

        grouped.setdefault(topic_id, [])

        grouped[topic_id].append({

            "content": payload.get("content", ""),

            "filename": payload.get("filename", ""),

            "topic_title": payload.get("topic_title", ""),

            "chunk_index": payload.get("chunk_index", 0),

            "score": getattr(hit, "score", 1.0),

        })

    ############################################################
    # SORT CHUNKS
    ############################################################

    for topic_id in grouped:

        grouped[topic_id].sort(
            key=lambda x: x["chunk_index"]
        )

    ############################################################
    # LOAD POSTGRES METADATA
    ############################################################

    metadata = {}

    if topic_ids:

        placeholders = ",".join(
            ["%s"] * len(topic_ids)
        )

        sql = f"""
        SELECT
            id,
            topic_title,
            office_type,
            office_division,
            classification,
            uploaded_by
        FROM kx_topics
        WHERE id IN ({placeholders})
        """

        with connections["birai_db"].cursor() as cursor:

            cursor.execute(
                sql,
                list(topic_ids),
            )

            for row in cursor.fetchall():

                metadata[row[0]] = {

                    "title": row[1],

                    "office_type": row[2],

                    "division": row[3],

                    "classification": row[4],

                    "uploaded_by": row[5],

                }

    ############################################################
    # BUILD CONTEXT
    ############################################################

    contexts = []

    for topic_id, chunks in grouped.items():

        meta = metadata.get(topic_id, {})

        title = meta.get(
            "title",
            chunks[0]["topic_title"],
        )

        office = meta.get(
            "office_type",
            "",
        )

        division = meta.get(
            "division",
            "",
        )

        classification = meta.get(
            "classification",
            "",
        )

        uploader = meta.get(
            "uploaded_by",
            "",
        )

        ####################################################
        # Merge ALL chunks into ONE document
        ####################################################

        merged_text = "\n\n".join(

            chunk["content"]

            for chunk in chunks

        )

        ####################################################
        # Highest score among chunks
        ####################################################

        highest_score = max(

            chunk["score"]

            for chunk in chunks

        )

        ####################################################
        # Context
        ####################################################

        context = f"""
==================================================

Document Title:
{title}

Filename:
{chunks[0]['filename']}

Match Type:
{match_type}

Similarity Score:
{highest_score:.3f}

Office:
{office}

Division:
{division}

Classification:
{classification}

Uploaded By:
{uploader}

Content:

{merged_text}

==================================================
"""

        contexts.append(context)

    ############################################################
    # SORT DOCUMENTS
    ############################################################

    contexts.sort()

    ############################################################
    # DEBUG
    ############################################################

    print("=" * 70)
    print(f"Match Type : {match_type}")
    print(f"Best Score : {best_score:.3f}")
    print(f"Documents  : {len(contexts)}")
    print("=" * 70)

    ############################################################
    # RETURN
    ############################################################

    return {

        "contexts": contexts,

        "match_type": match_type,

        "best_score": round(best_score, 3),

    }


@router.post("/ask-bir")
def ask_bir(request, data: Form[PromptInput], file: UploadedFile = File(None)):
    prompt = data.prompt

    ###########################################################
    # 1. INDEXING (BACKWARD COMPATIBILITY)
    ###########################################################

    if file:

        file_bytes = file.read()

        text = extract_text(
            file.name,
            file_bytes,
        )

        text = text.replace("\x00", "").strip()

        chunks = chunk_text(text)

        indexed_count = 0

        for i, chunk in enumerate(chunks):

            chunk = chunk.strip()

            if len(chunk) < 30:
                continue

            embedding = get_embedding(chunk)
            embedding = [float(x) for x in embedding]

            BIRDocument.objects.using("birai_db").create(

                filename=file.name,

                content=chunk,

                chunk_index=i,

                embedding=embedding,

                chunk_length=len(chunk),

            )

            indexed_count += 1

        return {
            "response": f"Indexed {indexed_count} chunks."
        }

    ###########################################################
    # 2. CHAT HISTORY
    ###########################################################

    agent_name = data.agent

    try:
        history = json.loads(data.history)

    except Exception:
        history = []

    ###########################################################
    # 3. EMBEDDING
    ###########################################################

    query_embedding = get_embedding(prompt)

    ###########################################################
    # 4. RETRIEVAL
    ###########################################################

    retrieval = search_bir_knowledge_base(

        query_embedding=query_embedding,

        agent_name=agent_name,

        user_question=prompt,

        limit=5,

    )

    if retrieval["contexts"]:

        context = "\n\n".join(
            retrieval["contexts"]
        )

    else:

        context = (
            "No relevant documents were found in the "
            "Internal Knowledge Base."
        )

    print("=" * 70)
    print(f"Match Type : {retrieval['match_type']}")
    print(f"Best Score : {retrieval['best_score']}")
    print(f"Documents  : {len(retrieval['contexts'])}")
    print("=" * 70)

    ###########################################################
    # 5. GPT
    ###########################################################

    response = openai_gpt45(

        prompt=prompt,

        context=context,

        history=history,

        match_type=retrieval["match_type"],

        best_score=retrieval["best_score"],

    )

    ###########################################################
    # 6. RETURN
    ###########################################################
    
    return {

        "response": response,

        "match_type": retrieval["match_type"],

        "score": retrieval["best_score"],

        "documents": len(retrieval["contexts"]),

    }


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
        file.seek(0)
        file_cid = upload_to_ipfs(file)        
        
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
            
            cursor.execute(
                """
                SELECT agent
                FROM kx_agents
                WHERE id = %s
                """,
                (agent,),
            )

            row = cursor.fetchone()

            agent_name = row[0] if row else None
            
            title = title if title else os.path.splitext(file.name)[0]
            
            cursor.execute("""
                INSERT INTO kx_topics (
                    topic_title, agent, office_type, office_division, 
                    classification, file_name, file_data, uploaded_by,
                    agent_id, file_cid
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, [title, agent_name, office_type, division, classification, 
                  file.name, psycopg2.Binary(file_bytes), uploaded_by,
                  agent, file_cid])
            
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
                
                print("agent: ",agent_name)
                qdrant_points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "topic_id": topic_id,
                            "topic_title": title,
                            "agent": agent_name,
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