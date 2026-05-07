import json
from openai import OpenAI
from gptchatbot.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# REFINED PERSONA: Emphasizes history as a secondary knowledge source
SYSTEM_PROMPT = """
You are BIR Internal Knowledge Base AI, an expert assistant specializing in Philippine taxation.

STRICT PROTOCOL:
1. PRIMARY SOURCE: Use the [INTERNAL DATABASE CONTEXT] provided to answer.
2. SECONDARY SOURCE: If the info is not in the context, look at the [CHAT HISTORY]. If the topic was discussed previously, use that information.
3. FALLBACK: Only if the information is completely missing from both the Context AND the History, say: "Not found in Internal Knowledge Base."
4. ANALYSIS: When asked for 'insight', 'analysis', or 'summary', synthesize the known facts from the document to provide professional value.

RESPONSE FORMAT:
1. Direct Answer: (Concise)
2. Explanation: (Detailed analysis)
3. Reference

Tone: Professional, clear, and helpful.
"""

def openai_gpt45(prompt, context=None, history=None):
    """
    Handles conversational RAG logic.
    history: Expected as a JSON string or a list of dicts.
    """
    # Initialize with the Persona
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # --- 1. ROBUST HISTORY PARSING ---
    if history:
        # If history arrives as a JSON string from the API (requests.post), decode it
        if isinstance(history, str):
            try:
                history_data = json.loads(history)
            except (json.JSONDecodeError, TypeError):
                history_data = []
        else:
            history_data = history

        # Append last 10 messages to keep the model focused and save tokens
        for msg in history_data[-10:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})

    # --- 2. CONTEXTUAL PROMPT CONSTRUCTION ---
    # We explicitly label the context so the model understands it's a retrieval result
    if context and context.strip():
        ctx_text = f"\n\n[INTERNAL DATABASE CONTEXT]:\n{context}"
    else:
        ctx_text = "\n\n[INTERNAL DATABASE CONTEXT]: No specific document chunks found for this query."

    # Combine the user's specific query with the retrieved context
    user_message = f"USER QUERY: {prompt}{ctx_text}"
    messages.append({"role": "user", "content": user_message})

    # --- 3. GENERATE RESPONSE ---
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2, # Low temperature for high factual accuracy
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating AI response: {str(e)}"