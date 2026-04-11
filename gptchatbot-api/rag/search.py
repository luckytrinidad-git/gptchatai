from django.db import connections

def search_similar(embedding, limit=5):
    conn = connections["birai_db"]

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT content
            FROM rag_birdocument
            ORDER BY embedding <-> %s::vector
            LIMIT %s;
        """, (embedding, limit))

        return [row[0] for row in cursor.fetchall()]