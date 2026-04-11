from ninja import NinjaAPI

from perplexity_ai.api import router as perplexity_router
from gemini_ai.api import router as gemini_router
from claude_ai.api import router as claude_router
from open_ai.api import router as openai_router
from rag.api import router as rag_router
from helix.api import router as helix_router

# class ApiKey(APIKeyHeader):
#     param_name = "Authorization"

#     def authenticate(self, request, key):
#         api_key_list = [API_KEY]
#         if key in api_key_list:
#             return key 

api = NinjaAPI(
                # auth=ApiKey(),
                title="GPTChatbot",
                description="GPTChatbot for some company",
                openapi_url="/gptchatbot.json"
                )

api.add_router("/perplexity/", perplexity_router)
api.add_router("/gemini/", gemini_router)
api.add_router("/claude/", claude_router)
api.add_router("/openai/", openai_router)
api.add_router("/rag/", rag_router)
api.add_router("/helix/", helix_router)