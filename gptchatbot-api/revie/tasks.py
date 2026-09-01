from celery import shared_task
from openai import OpenAI
from django.db import transaction
from revie.models import RevieIntent, RevieQuestion


client = OpenAI()

BATCH_SIZE = 100

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def import_revie_data(
    self,
    topic_id,
    data,
):

    print("=" * 70)
    print("STARTING REVIE DATA IMPORT")
    print(f"Topic ID: {topic_id}")
    print(f"Items: {len(data)}")
    print("=" * 70)

    imported_intents = 0
    imported_questions = 0

    ###########################################################
    # 1. DATABASE TRANSACTION
    ###########################################################

    try:

        with transaction.atomic(
            using="birai_db"
        ):

            for index, item in enumerate(data):

                intent_id = item["id"]

                ################################################
                # INSERT / UPDATE INTENT
                ################################################

                intent, created = (
                    RevieIntent.objects
                    .using("birai_db")
                    .update_or_create(
                        intent_id=intent_id,
                        defaults={
                            "answer": item["answer"],
                            "kx_topics_id": topic_id,
                        },
                    )
                )

                imported_intents += 1

                ################################################
                # REMOVE EXISTING QUESTIONS
                ################################################

                RevieQuestion.objects.using(
                    "birai_db"
                ).filter(
                    intent=intent
                ).delete()

                ################################################
                # PREPARE QUESTIONS
                ################################################

                questions_to_create = []

                for question in item["questions"]:

                    if question is None:
                        continue

                    question = str(
                        question
                    ).strip()

                    if not question:
                        continue

                    questions_to_create.append(
                        RevieQuestion(
                            intent=intent,
                            question=question,
                        )
                    )

                ################################################
                # BULK INSERT QUESTIONS
                ################################################

                if questions_to_create:

                    RevieQuestion.objects.using(
                        "birai_db"
                    ).bulk_create(
                        questions_to_create,
                        batch_size=500,
                    )

                    imported_questions += (
                        len(questions_to_create)
                    )

                ################################################
                # PROGRESS LOG
                ################################################

                if (
                    index + 1
                ) % 100 == 0:

                    print(
                        f"Processed "
                        f"{index + 1}/{len(data)} items"
                    )

        print("=" * 70)
        print("REVIE DATABASE IMPORT COMPLETE")
        print(
            f"Intents: {imported_intents}"
        )
        print(
            f"Questions: {imported_questions}"
        )
        print("=" * 70)

    except Exception as e:

        print(
            "=" * 70
        )
        print(
            "REVIE DATABASE IMPORT FAILED"
        )
        print(
            str(e)
        )
        print(
            "=" * 70
        )

        raise

    ###########################################################
    # 2. START EMBEDDING GENERATION
    ###########################################################

    try:

        print(
            "Starting REVIE embedding generation..."
        )

        embedding_task = (
            generate_revie_embeddings.delay()
        )

        print(
            "Embedding task queued:"
        )

        print(
            embedding_task.id
        )

    except Exception as e:

        print(
            "Database import succeeded, "
            "but embedding task failed:"
        )

        print(str(e))

        return {
            "success": True,
            "intents": imported_intents,
            "questions": imported_questions,
            "embedding_status": "failed",
            "embedding_error": str(e),
        }

    ###########################################################
    # 3. RETURN TASK RESULT
    ###########################################################

    return {
        "success": True,
        "intents": imported_intents,
        "questions": imported_questions,
        "embedding_status": "queued",
        "embedding_task_id": embedding_task.id,
    }

@shared_task
def generate_revie_embeddings():

    questions = list(
        RevieQuestion.objects
        .using("birai_db")
        .filter(
            embedding__isnull=True
        )
    )

    total = len(questions)
    processed = 0
    failed = 0

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        batch = questions[
            start:start + BATCH_SIZE
        ]

        texts = [
            question.question
            for question in batch
        ]

        try:

            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )

            for question, embedding_data in zip(
                batch,
                response.data,
            ):

                question.embedding = (
                    embedding_data.embedding
                )

                question.save(
                    using="birai_db",
                    update_fields=[
                        "embedding"
                    ],
                )

                processed += 1

        except Exception as e:

            failed += len(batch)

            print(
                f"Failed batch "
                f"{start}-{start + len(batch)}: {e}"
            )

    return {
        "total": total,
        "processed": processed,
        "failed": failed,
    }
