from typing import Optional, List, Dict, Union

from ninja import Schema, ModelSchema
from typing import Optional


# Input Schema
class PromptInput(Schema):
    prompt: str = None
    agent: Optional[str] = "External Sources" # <--- ADD THIS LINEagent: Optional[str] = "BIR AI"
    # History is sent as a JSON string from Streamlit
    history: Optional[str] = "[]"

    class Config:
        extra = 'forbid'


# Output Schema
class ChatbotOutput(Schema):
    response: str
    search_results: str = None
    content: str = None
    usage_info: str = None

# Error Schema
class BadRequestSchema(Schema):
    messages: Optional[str] = None
    error: Optional[str] = None