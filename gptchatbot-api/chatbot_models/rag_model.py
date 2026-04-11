from openai import OpenAI
from gptchatbot.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """
You are BIR Internal Knowledge Assistant for the Bureau of Internal Revenue (Philippines).

You must answer ONLY using provided context.

========================
RULES
========================
- Use ONLY the provided context
- Do NOT require exact sentence match (IMPORTANT)
- OCR text may be noisy, interpret meaning
- You may combine multiple chunks if related
- Do NOT hallucinate missing facts
- If context is unrelated, say:
  "Not found in uploaded BIR document."
- If context is partial, still answer using best interpretation
- If unclear, say:
  "Not enough information in uploaded BIR document."

========================
OUTPUT STYLE
========================
- Direct answer only
- No explanations
"""


def build_prompt(prompt, context=None):

    if not context or len(context.strip()) < 20:
        return f"""
QUESTION:
{prompt}

ANSWER:
Not found in uploaded BIR document.
"""

    return f"""
CONTEXT:
{context}

QUESTION:
{prompt}

INSTRUCTIONS:
- Use ONLY context above
- Do NOT require exact match (important for OCR)
- Combine related chunks if needed
- If not relevant → "Not found in uploaded BIR document."
"""


def openai_gpt45(prompt, context=None):

    full_prompt = build_prompt(prompt, context)

    response = client.responses.create(
        model="gpt-4o-mini",
        instructions=SYSTEM_PROMPT,
        input=full_prompt,
        temperature=0.2,
        top_p=0.9
    )

    return response.output_text