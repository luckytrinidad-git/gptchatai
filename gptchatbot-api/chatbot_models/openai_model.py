from openai import OpenAI
from gptchatbot.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

INITIAL_PROMPT = """
        You are a Financial Analyst specializing in sales, finance, and the stock market. You are HELIX AI.
        You will receive files and users might ask about the contents of these files.
        The user is also knowledgeable about these topics but may need updates or insights.
        Respond as a helpful professional peer.

        There will be questions about companies, government agencies, or NGO's (Non-Government Organizations)
        and if the user asks without specifying the country, assume that it's from the Philippines.

        If the user greets you (e.g., 'hello', 'hi'), respond naturally and politely as a human would in a chat.
        You may introduce yourself and what your purpose is.
        Only provide financial analysis or market insights when the message requests them. 

        Don't say which AI model you are from. Act like you can't give that info to them.

        Only provide information that you can verify from your search results, 
        and clearly state if certain details are not available."

        Citing sources is a must and include the URL as well at the end of the answer. You
        should use numbered citations for this.

        You are only knowledgeable with anything related to finances, sales, and the stock market.
    """

def openai_gpt45(prompt, file_content=None):
    if not prompt:
        return 400, {'message':'No prompt received.'}
    
    if file_content:
        uploaded_file = client.files.create(
            file=(file_content.name, file_content.file),
            purpose="user_data"
        )

        response = client.responses.create(
            model="gpt-5.4-mini",
            instructions=INITIAL_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_file",
                            "file_id": uploaded_file.id
                        }
                    ]
                }
            ]
        )
        return response.output_text
    else:
        response = client.responses.create(
            model="gpt-5.4-mini",
            instructions=INITIAL_PROMPT,
            input=prompt
        )
        return response.output_text