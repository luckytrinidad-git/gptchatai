from django.db import models
from pgvector.django import VectorField

class BIRDocument(models.Model):
    filename = models.CharField(max_length=255)
    content = models.TextField()

    # NEW: chunk-based embedding
    chunk_index = models.IntegerField(default=0)
    embedding = VectorField(dimensions=1536)  # for text-embedding-3-small
    #embedding = VectorField(null=True, blank=True)
    chunk_length = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)