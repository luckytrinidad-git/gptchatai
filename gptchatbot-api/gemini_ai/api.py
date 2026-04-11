from gemini_ai.schemas import *
from chatbot_models.gemini_model import *

from ninja import Router, Form
from django.http import StreamingHttpResponse

router = Router(tags=["Gemini_AI"])

@router.post("/ask-gemini", 
             summary="Use Gemini 2.5 Flash Model for Prompts", 
             tags=["Gemini"], 
            #  response={200: ChatbotOutput, 400: BadRequestSchema}, 
             exclude_none=True)
def ask_gemini(request, data:Form[PromptInput]):
    prompt = data.prompt
    prompt_response = gemini_flash(prompt=prompt)

    response = {
        'response': prompt_response.text
    }
    return response