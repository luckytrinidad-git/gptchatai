from django.urls import path
from .api import api as api

urlpatterns = [
    path("gptchatbot/", api.urls),
]