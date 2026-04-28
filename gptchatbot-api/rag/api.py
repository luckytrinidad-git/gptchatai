from ninja import Router, Form, File
from ninja.files import UploadedFile

from rag.schemas import PromptInput
from rag.models import BIRDocument

from rag.utils import extract_text, chunk_text
from rag.embeddings import get_embedding
from rag.search import search_similar

from chatbot_models.rag_model import openai_gpt45

import psycopg2
from psycopg2.extras import execute_values

from django.db import connections

router = Router(tags=["Internal BIR AI"])

def search_similar(query_embedding, agent_name, limit=5):
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    query = """
        SELECT r.content, t.topic_title, t.file_name
        FROM rag_birdocument r
        JOIN kx_topics t ON r.topic_id = t.id
        WHERE t.agent = %s
        ORDER BY r.embedding <=> %s::vector
        LIMIT %s;
    """
    
    docs = []
    with connections['birai_db'].cursor() as cursor:
        cursor.execute(query, [agent_name, embedding_str, limit])
        rows = cursor.fetchall()
        for row in rows:
            docs.append(f"Source: {row[1]} ({row[2]})\nContent: {row[0]}")
            
    return docs

@router.post("/ask-bir")
def ask_bir(request, data: Form[PromptInput], file: UploadedFile = File(None)):

    prompt = data.prompt

    # =========================
    # UPLOAD MODE (INDEXING)
    # =========================
    if file:

        file_bytes = file.read()

        text = extract_text(file.name, file_bytes)

        # CLEAN TEXT
        text = text.replace("\x00", "").strip()

        chunks = chunk_text(text)

        indexed_count = 0

        for i, chunk in enumerate(chunks):

            chunk = chunk.strip()

            # SKIP BAD CHUNKS
            if not chunk or len(chunk) < 30:
                continue

            embedding = get_embedding(chunk)

            # OPTIONAL: normalize embedding (VERY GOOD FOR COSINE SEARCH)
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

    # =========================
    # 2. QUERY RAG
    # =========================
    agent_name = data.agent
    
    # 1. Parse Chat History
    try:
        chat_history = json.loads(data.history)
    except:
        chat_history = []

    # 2. Vector Search (RAG)
    try:
        query_embedding = get_embedding(prompt)
        docs = search_similar(query_embedding, agent_name, limit=5)
        context = "\n\n---\n\n".join(docs)
        print(f"DEBUG: Found {len(docs)} docs for {agent_name}")
    except Exception as e:
        print(f"Search Error: {e}")
        context = ""

    # 3. Call Conversational LLM
    response = openai_gpt45(
        prompt=prompt, 
        context=context, 
        history=chat_history
    )

    return {"response": response}

# ==========================================
# 2. UNIFIED KX INGESTION ENDPOINT
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
        
        # DEBUG PRINTS - Check your terminal for these!
        print(f"--- INGESTION START ---")
        print(f"Target DB: {conn.settings_dict.get('NAME')} @ {conn.settings_dict.get('HOST')}")
        print(f"File: {file.name} | Chunks: {len(chunks)}")

        with conn.cursor() as cursor:
            # 3. Insert Master Record
            cursor.execute("""
                INSERT INTO kx_topics (
                    topic_title, agent, office_type, office_division, 
                    classification, file_name, file_data, uploaded_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, [title, agent, office_type, division, classification, file.name, psycopg2.Binary(file_bytes), uploaded_by])
            
            topic_id = cursor.fetchone()[0]
            print(f"Master Record Created: ID {topic_id}")

            # 4. Embed and Prepare Chunks
            rag_entries = []
            for idx, chunk in enumerate(chunks):
                if len(chunk.strip()) < 30: continue
                vector = get_embedding(chunk)
                rag_entries.append((file.name, chunk, idx, len(chunk), topic_id, vector))
            
            # 5. Bulk Insert
            if rag_entries:
                execute_values(cursor, """
                    INSERT INTO rag_birdocument (filename, content, chunk_index, chunk_length, topic_id, embedding)
                    VALUES %s
                """, rag_entries)
                print(f"Inserted {len(rag_entries)} vector chunks.")

        # 6. THE MOST IMPORTANT PART: FORCE COMMIT
        conn.commit()
        print(f"--- TRANSACTION COMMITTED ---")

        return {
            "status": "success", 
            "topic_id": topic_id, 
            "chunks": len(rag_entries)
        }

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"!!! INGESTION ERROR: {str(e)}")
        return {"status": "error", "message": str(e)}