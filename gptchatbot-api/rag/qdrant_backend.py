from django.conf import settings
from qdrant_client import QdrantClient

def get_qdrant_client():
    """
    Initializes and returns an authenticated Qdrant client 
    forcing plain HTTP to avoid Windows SSL version bugs.
    """
    config = settings.QDRANT_CONFIG
    
    return QdrantClient(
        host=config["HOST"],
        port=config["PORT"],
        api_key=config["API_KEY"],
        # FORCE PLAIN HTTP FOR LOCAL DOCKER
        prefer_grpc=False,
        https=False,
        check_compatibility=False  # Wipes out that server version warning too!
    )

def get_qdrant_collection():
    """Helper to quickly grab the active collection name"""
    return settings.QDRANT_CONFIG["COLLECTION_NAME"]