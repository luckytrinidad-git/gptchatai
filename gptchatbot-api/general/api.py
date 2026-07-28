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