from django.db import models
from pgvector.django import VectorField

class BIRDocument(models.Model):

    filename = models.CharField(
        max_length=500
    )

    content = models.TextField()

    chunk_index = models.IntegerField()

    embedding = VectorField(
        dimensions=1536,
        null=True,
    )

    chunk_length = models.IntegerField()

    kx_topics_id = models.IntegerField(
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "bir_document"
        managed = False