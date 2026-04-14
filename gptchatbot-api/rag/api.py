from ninja import Router, Form, File
from ninja.files import UploadedFile

from rag.schemas import PromptInput
from rag.models import BIRDocument

from rag.utils import extract_text, chunk_text
from rag.embeddings import get_embedding
from rag.search import search_similar

from chatbot_models.rag_model import openai_gpt45

router = Router(tags=["Internal BIR AI"])


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
    query_embedding = get_embedding(prompt)

    try:
        docs = search_similar(query_embedding, limit=5)
    except Exception as e:
        print("Search error:", e)
        docs = []

    context = "\n\n".join(docs[:5])

    print("DEBUG DOCS:", docs)

    response = openai_gpt45(
        prompt=prompt,
        context=context[:12000]
    )

    return {"response": response}


    