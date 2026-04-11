from claude_ai.schemas import *
from chatbot_models.claude_model import *

from ninja import Router, Form

router = Router(tags=["Claude_AI"])

@router.post("/ask-claude", 
             summary="Use Claude Sonnet 4.5 for Prompts", 
             tags=["Claude"], 
            #  response={200: ChatbotOutput, 400: BadRequestSchema}, 
             exclude_none=True)
def ask_claude(request, data:Form[PromptInput]):
    prompt = data.prompt
    prompt_response = claude_sonnet(prompt=prompt)

    response = {
        'response': prompt_response
    }
    return response