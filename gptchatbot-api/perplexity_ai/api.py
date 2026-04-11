# from django.db.models import CharField, Value, F, IntegerField, Q, BooleanField
# from django.http import JsonResponse
# from typing import Union
from perplexity_ai.schemas import *
from chatbot_models.perplexity_model import *

from ninja import Router, Form
from django.http import StreamingHttpResponse


router = Router(tags=["Perplexity_SonarModel"])

@router.post("/ask-perplexity", 
             summary="Use Perplexity Sonar Model for Prompts", 
             tags=["Perplexity"], 
             response={200: ChatbotOutput, 400: BadRequestSchema}, 
             exclude_none=True)
def ask_perplexity(request, data:Form[PromptInput]):
    prompt = data.prompt
    prompt_response, source_list = perplexity_sonar(prompt=prompt)

    response = {
        'response': prompt_response,
        'source_list': source_list
    }

    return response

@router.post("/ask-perplexity-streamed", 
             summary="Perplexity Sonar Streaming Response", 
             tags=["Perplexity"],
             exclude_none=True)
def ask_streaming_perplexity(request, data:Form[PromptInput]):
    prompt = data.prompt

    def event_stream():
        for piece in perplexity_sonar_streaming(prompt):
            yield f"data: {piece}\n\n"
    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # important if behind Nginx
    return resp