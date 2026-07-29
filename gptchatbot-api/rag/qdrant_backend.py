from django.conf import settings
from django.db import connections
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchText,
    MatchValue,
)

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


def find_matching_topic_ids(
    client,
    collection_name,
    agent_name,
    title_variants,
):
    """
    Finds all topic_ids whose topic_title contains
    one of the requested variants.

    No vector search is used.
    """

    topic_ids = set()

    for variant in title_variants:

        offset = None

        while True:

            records, offset = client.scroll(

                collection_name=collection_name,

                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent",
                            match=MatchValue(value=agent_name),
                        ),
                        FieldCondition(
                            key="topic_title",
                            match=MatchText(text=variant),
                        ),
                    ]
                ),

                limit=100,

                with_payload=True,

                with_vectors=False,

                offset=offset,
            )

            if not records:
                break

            for record in records:

                topic_id = record.payload.get("topic_id")

                if topic_id:
                    topic_ids.add(topic_id)

            if offset is None:
                break

    return list(topic_ids)

def load_document_chunks(
    client,
    collection_name,
    topic_ids,
):
    """
    Loads every chunk belonging to the matched document.
    """

    if not topic_ids:
        return []

    records = []

    for topic_id in topic_ids:

        offset = None

        while True:

            chunk_records, offset = client.scroll(

                collection_name=collection_name,

                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="topic_id",
                            match=MatchValue(value=topic_id),
                        )
                    ]
                ),

                limit=500,

                with_payload=True,

                with_vectors=False,

                offset=offset,
            )

            if not chunk_records:
                break

            records.extend(chunk_records)

            if offset is None:
                break

    return records

def run_exact_document_lookup(
    client,
    collection_name,
    agent_name,
    title_variants,
):
    """
    Exact lookup.

    No embeddings.

    No score.

    Returns every chunk
    belonging to the matched document.
    """

    print("=" * 70)
    print("EXACT DOCUMENT LOOKUP")
    print(title_variants)
    print("=" * 70)

    topic_ids = find_matching_topic_ids(
        client=client,
        collection_name=collection_name,
        agent_name=agent_name,
        title_variants=title_variants,
    )

    if not topic_ids:

        print("No matching topic title found.")

        return []

    print(f"Matched Topic IDs: {topic_ids}")

    return load_document_chunks(
        client=client,
        collection_name=collection_name,
        topic_ids=topic_ids,
    )
    
def run_semantic_search(
    client,
    collection_name,
    embedding,
    agent_name,
    limit=5,
    threshold=0.70,
):
    """
    Pure semantic search.

    Used AFTER exact document lookup fails.
    """

    return client.query_points(

        collection_name=collection_name,

        query=embedding,

        query_filter=Filter(

            must=[

                FieldCondition(
                    key="agent",
                    match=MatchValue(value=agent_name),
                )

            ]

        ),

        limit=limit,

        score_threshold=threshold,

    ).points
def run_semantic_search(
    client,
    collection_name,
    embedding,
    agent_name,
    limit=5,
    threshold=0.70,
):
    """
    Pure semantic search.

    Used AFTER exact document lookup fails.
    """

    return client.query_points(

        collection_name=collection_name,

        query=embedding,

        query_filter=Filter(

            must=[

                FieldCondition(
                    key="agent",
                    match=MatchValue(value=agent_name),
                )

            ]

        ),

        limit=limit,

        score_threshold=threshold,

    ).points
    
def semantic_with_fallback(
    client,
    collection_name,
    embedding,
    agent_name,
    limit=5,
):
    """
    Enterprise semantic retrieval.

    Try:

    70%

    ↓

    50%

    Returns

    (
        results,
        match_type,
        best_score
    )
    """

    ####################################################
    # HIGH CONFIDENCE
    ####################################################

    print("=" * 70)
    print("SEMANTIC SEARCH (>= 0.70)")
    print("=" * 70)

    results = run_semantic_search(

        client=client,

        collection_name=collection_name,

        embedding=embedding,

        agent_name=agent_name,

        limit=limit,

        threshold=0.70,

    )

    if results:

        best = max(hit.score for hit in results)

        print(f"Found {len(results)} chunks")
        print(f"Best score : {best:.3f}")

        return (
            results,
            "semantic_high",
            best,
        )

    ####################################################
    # RELAXED
    ####################################################

    print("=" * 70)
    print("SEMANTIC FALLBACK (>= 0.50)")
    print("=" * 70)

    results = run_semantic_search(

        client=client,

        collection_name=collection_name,

        embedding=embedding,

        agent_name=agent_name,

        limit=limit,

        threshold=0.50,

    )

    if results:

        best = max(hit.score for hit in results)

        print(f"Found {len(results)} chunks")
        print(f"Best score : {best:.3f}")

        return (
            results,
            "semantic_low",
            best,
        )

    ####################################################
    # NOTHING
    ####################################################

    return (
        [],
        "none",
        0,
    )