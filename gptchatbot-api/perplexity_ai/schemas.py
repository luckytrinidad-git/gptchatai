from typing import Optional, List, Dict, Union

from ninja import Schema, ModelSchema

# Input Schema
class PromptInput(Schema):
    prompt: str = None

    class Config:
        extra = 'forbid'


# Output Schema
class ChatbotOutput(Schema):
    response: str
    source_list: list
    search_results: str = None
    content: str = None
    usage_info: str = None

# Error Schema
class BadRequestSchema(Schema):
    messages: Optional[str] = None
    error: Optional[str] = None