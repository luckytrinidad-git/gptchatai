from pgvector.django import CosineDistance
from revie.models import RevieQuestion

def search_revie_knowledge_base(
    query_embedding,
    limit=5,
    score_threshold=0.50,
):
    """
    Search REVIE questions using PostgreSQL pgvector.

    The user's question is compared against stored REVIE
    questions. The matched question's intent provides the
    authoritative answer.
    """

    questions = (
        RevieQuestion.objects
        .using("birai_db")
        .filter(
            embedding__isnull=False
        )
        .annotate(
            distance=CosineDistance(
                "embedding",
                query_embedding,
            )
        )
        .order_by("distance")[:limit]
    )

    results = []

    for question in questions:

        # Cosine distance:
        # 0.0 = identical
        # 1.0 = very different
        similarity = 1 - float(
            question.distance
        )

        if similarity < score_threshold:
            continue

        intent = question.intent

        results.append({
            "question_id": question.id,
            "question": question.question,
            "intent_id": intent.intent_id,
            "answer": intent.answer,
            "topic_id": intent.kx_topics_id,
            "score": similarity,
        })

    if not results:

        print("=" * 70)
        print("REVIE: No matching questions found")
        print("=" * 70)

        return {
            "contexts": [],
            "match_type": "none",
            "best_score": 0,
        }

    best_score = results[0]["score"]

    ###########################################################
    # DETERMINE MATCH TYPE
    ###########################################################

    if best_score >= 0.70:

        match_type = "exact"

    elif best_score >= 0.55:

        match_type = "semantic"

    else:

        match_type = "semantic_low"

    ###########################################################
    # BUILD CONTEXT
    ###########################################################

    contexts = []

    for result in results:

        contexts.append(
            f"""
==================================================

REVIE INTENT

Intent ID:
{result["intent_id"]}

Matched Question:
{result["question"]}

Similarity Score:
{result["score"]:.3f}

Known REVIE Answer:
{result["answer"]}

==================================================
"""
        )

    ###########################################################
    # LOG
    ###########################################################

    print("=" * 70)
    print("REVIE RETRIEVAL")
    print(f"Match Type : {match_type}")
    print(f"Best Score : {best_score:.3f}")
    print(f"Matches    : {len(results)}")
    print("=" * 70)

    return {
        "contexts": contexts,
        "match_type": match_type,
        "best_score": round(
            best_score,
            3
        ),
    }