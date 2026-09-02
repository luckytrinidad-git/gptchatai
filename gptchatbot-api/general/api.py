from django.db import connections
from ninja import Router
from ninja.files import UploadedFile

router = Router(tags=["Internal BIR AI"])

@router.get("/agents")
def get_agents(request):
    with connections["birai_db"].cursor() as cursor:
        cursor.execute("""
            SELECT id, agent
            FROM kx_agents
            ORDER BY agent;
        """)

        return [
            {
                "id": row[0],
                "agent": row[1]
            }
            for row in cursor.fetchall()
        ]

@router.get("/topics")
def get_topics(request):
    
    with connections["birai_db"].cursor() as cursor:
        cursor.execute("""
            SELECT
                t.id,
                t.topic_title,
                t.agent,
                t.file_name,
                t.uploaded_at,
                t.file_cid
            FROM kx_topics t
            LEFT JOIN rag_birdocument r
                ON t.id = r.topic_id
            GROUP BY
                t.id,
                t.topic_title,
                t.agent,
                t.file_name,
                t.uploaded_at,
                t.file_cid
            ORDER BY t.uploaded_at DESC
        """)

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]
    

@router.get("/audit_log")
def get_audit_log(request):
    
    with connections["birai_db"].cursor() as cursor:
        cursor.execute("""
            SELECT timestamp as Timestamp, username as Username, action as Action, module as Module, status as Status 
            FROM audit_logs 
            ORDER BY timestamp DESC
        """)

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]