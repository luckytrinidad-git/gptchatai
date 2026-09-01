from django.db import models
from pgvector.django import VectorField

class RevieIntent(models.Model):

    intent_id = models.IntegerField(unique=True)
    answer = models.TextField()
    kx_topics_id = models.IntegerField()
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = "revie_intents"
        managed = False


class RevieQuestion(models.Model):

    intent = models.ForeignKey(
        RevieIntent,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question = models.TextField()
    embedding = VectorField(
        dimensions=1536,
        null=True,
    )

    class Meta:
        db_table = "revie_questions"
        managed = False
