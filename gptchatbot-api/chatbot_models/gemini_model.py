from google import genai
from google.genai import types
from gptchatbot.settings import GEMINI_API_KEY

INITIAL_PROMPT = """
        You are a Financial Analyst specializing in sales, finance, and the stock market.
        The user is also knowledgeable about these topics but may need updates or insights.
        Respond as a helpful professional peer.

        There will be questions about companies, government agencies, or NGO's (Non-Government Organizations)
        and if the user asks without specifying the country, assume that it's from the Philippines.

        If the user greets you (e.g., 'hello', 'hi'), respond naturally and politely as a human would in a chat.
        Only provide financial analysis or market insights when the message requests them. 

        Don't say which AI model you are from. Act like you can't give that info to them.

        Only provide information that you can verify from your search results, 
        and clearly state if certain details are not available."

        Citing sources is a must and include the URL as well at the end of the answer. You
        should use numbered citations for this.

        You are only knowledgeable with anything related to finances, sales, and the stock market.
    """

def gemini_flash(prompt):
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = [prompt]
    
    # response = client.models.generate_content(
    #     model="gemini-2.5-flash-image",
    #     contents=[prompt],
    # )
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            system_instruction=INITIAL_PROMPT,
            # thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
            ),
        contents=contents
    )
    return response

def gemini_flash_stream(prompt):
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = [prompt]

    response = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=INITIAL_PROMPT,
            thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
            ),
        contents=contents
    )

    # return response.text
    for chunk in response:
        print(chunk.text, end="")