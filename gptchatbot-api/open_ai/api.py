from open_ai.schemas import *
from chatbot_models.openai_model import *

from ninja import Router, Form, File
from ninja.files import UploadedFile
# from django.http import StreamingHttpResponse


router = Router(tags=["GPT 4.5-mini"])

@router.post("/ask-openai", 
             summary="Use OpenAI GPT 4.5-mini Model for Prompts", 
             tags=["OpenAI"], 
            #  response={200: ChatbotOutput, 400: BadRequestSchema}, 
             exclude_none=True)
def ask_gpt(request, data:Form[PromptInput],file: UploadedFile = File(None)):
    prompt = data.prompt
    uploaded_file = None
    
    if file:
        prompt_response = openai_gpt45(
            prompt=prompt,
            file_content=file
        )
    else:
        prompt_response = openai_gpt45(prompt=prompt)

    response = {
        'response': prompt_response
    }
    return response