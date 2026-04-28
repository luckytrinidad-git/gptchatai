from openai import OpenAI
from gptchatbot.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# YOUR AUTHENTIC PERSONA
SYSTEM_PROMPT = """
You are BIR Internal Knowledge Base AI, an expert assistant specializing in Philippine taxation and compliance.
Instructions:
- Use the provided context to answer. 
- If info is missing from context, check Chat History.
- If still missing, say: "Not found in Internal Knowledge Base."
- Format: 1. Direct Answer, 2. Explanation, 3. Reference.
- Tone: Professional, clear, and helpful.
"""

def openai_gpt45(prompt, context=None, history=None):
    # Prepare messages with System Persona
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add Chat History
    if history:
        # Pass only relevant history to save tokens (last 10 messages)
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Prepare current prompt with RAG Context
    ctx_text = f"\n\nINTERNAL DATABASE CONTEXT:\n{context}" if context else ""
    user_message = f"{prompt}\n{ctx_text}"
    
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content