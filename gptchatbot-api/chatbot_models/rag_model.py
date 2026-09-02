import json
from openai import OpenAI
from gptchatbot.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# REFINED PERSONA: Emphasizes history as a secondary knowledge source
SYSTEM_PROMPT = """
You are BIR Internal Knowledge Base AI, an expert assistant specializing in Philippine taxation.

Your primary responsibility is to answer using ONLY the Internal Knowledge Base.

====================================================
RETRIEVAL PRIORITY
====================================================

1. INTERNAL DATABASE CONTEXT
   This is the authoritative source.

2. CHAT HISTORY
   Only use previous conversation if the Internal Database
   does not contain the requested information.

3. If neither contains the answer, reply exactly:

   "Not found in Internal Knowledge Base."

Do NOT use outside knowledge.

====================================================
DOCUMENT MATCH TYPES
====================================================

The retrieval system provides one of the following:

EXACT
- The requested document was found.
- Treat it as authoritative.

SEMANTIC
- The requested document was not found exactly.
- Similarity >= 0.70.
- These are highly related documents.
- You may summarize and explain them confidently,
  but never claim they are the exact requested document.

SEMANTIC_LOW
- Similarity between approximately 0.50 and 0.70.
- These documents are only partially related.
- Answer cautiously.
- Clearly mention uncertainty.
- Never invent missing facts.

NONE
- No relevant documents found.
- Use chat history only.
- Otherwise reply:
  "Not found in Internal Knowledge Base."

====================================================
SUMMARIES / ANALYSIS
====================================================

When the user asks for:

• Summary
• Insight
• Analysis
• Key Points
• Implications

You should synthesize information from ALL retrieved
chunks that belong to the same document.

Do NOT summarize each chunk independently.

====================================================
REFERENCES
====================================================

Always include the document title(s) used.

If multiple documents contributed,
mention all of them.

====================================================
STYLE
====================================================

Professional

Objective

Concise

Never hallucinate.

Never fabricate missing provisions.

Never state assumptions as facts.

====================================================
RESPONSE FORMAT
====================================================

1. Direct Answer: (Concise)
2. Explanation: (Detailed analysis)
3. Reference
"""

def openai_gpt45(
    prompt,
    context="",
    history=None,
    match_type="none",
    best_score=0,
):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    ####################################################
    # CHAT HISTORY
    ####################################################

    if history:

        if isinstance(history, str):

            try:
                history = json.loads(history)

            except Exception:
                history = []

        for msg in history[-10:]:

            if (
                isinstance(msg, dict)
                and "role" in msg
                and "content" in msg
            ):

                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

    ####################################################
    # USER PROMPT
    ####################################################

    if match_type == "exact":

        user_prompt = f"""
USER QUESTION

{prompt}

================================================

MATCH TYPE

EXACT

================================================

INTERNAL DATABASE CONTEXT

{context}

Instructions

• The requested document was found.

• Treat it as authoritative.

• Use every relevant section.

• If summarizing,
produce ONE coherent summary.

• If analysing,
base the analysis only on the retrieved document.

• Never invent missing information.

• Always cite the document title.
"""

    elif match_type == "semantic":

        user_prompt = f"""
USER QUESTION

{prompt}

================================================

MATCH TYPE

SEMANTIC

Similarity Score

{best_score:.3f}

================================================

RELATED DOCUMENTS

{context}

Instructions

• The requested document was NOT found exactly.

• These documents are highly related.

• Answer ONLY using these documents.

• Do NOT state they are the exact requested document.

• If appropriate, begin with:

"The requested document was not found exactly in the Internal Knowledge Base. Based on the closest related documents..."

• Provide a professional answer.

• Cite every document used.
Citation rules:
- Cite only the actual source document(s) used to support the answer.
- Do not cite or mention chunk numbers, chunk IDs, similarity scores, or internal retrieval metadata.
- When multiple documents are used, cite each actual document that supports the relevant information.
- Do not cite documents that were not used to formulate the answer.
- If the retrieved context does not contain enough information to support a claim, say so rather than citing an unrelated document or relying on an unsupported reference.
- Preserve the document title/reference as provided in the retrieved context when citing the source.
"""

    elif match_type == "semantic_low":

        user_prompt = f"""
USER QUESTION

{prompt}

================================================

MATCH TYPE

SEMANTIC_LOW

Similarity Score

{best_score:.3f}

================================================

RELATED DOCUMENTS

{context}

Instructions

• The requested document was NOT found.

• The retrieved documents are only partially related.

• Use ONLY the retrieved information.

• Never infer missing provisions.

• Clearly mention uncertainty.

• If appropriate, begin with:

"The Internal Knowledge Base does not contain an exact match. The closest available documents suggest..."

• Your answer should reflect approximately 50-70% confidence.

• Cite every document used.
"""

    else:

        user_prompt = f"""
USER QUESTION

{prompt}

================================================

MATCH TYPE

NONE

================================================

No relevant documents were retrieved.

If the answer exists in CHAT HISTORY,
use that.

Otherwise reply exactly:

Not found in Internal Knowledge Base.
"""

    messages.append({
        "role": "user",
        "content": user_prompt,
    })

    ####################################################
    # GENERATE RESPONSE
    ####################################################

    try:

        response = client.chat.completions.create(

            model="gpt-4o-mini",

            messages=messages,

            temperature=0.2,

            max_tokens=1000,

        )

        return response.choices[0].message.content

    except Exception as e:

        return f"Error generating AI response: {e}"