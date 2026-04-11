import perplexity
from perplexity import Perplexity

# Initialize the client (uses PERPLEXITY_API_KEY environment variable)
client = Perplexity()

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

        If current data is not available, always provide the most recent one.

        You are only knowledgeable with anything related to finances, sales, and the stock market.
    """

def perplexity_sonar(prompt):
    messages = []
    initial_prompt = INITIAL_PROMPT

    initial_context = {"role": "system", "content": initial_prompt,}
    messages.append(initial_context)

    if prompt:
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model="sonar",
            messages= messages,
            # temperature=0.7
        )
        source_list = []
        for index, url in enumerate(completion.citations, start=1):
            source = f"{index}. {url}"
            source_list.append(source)
        return completion.choices[0].message.content, source_list
    else:
        return 400, {'message':'No prompt received.'}
    

def perplexity_sonar_streaming(prompt):
    messages = []
    initial_prompt = INITIAL_PROMPT

    initial_context = {"role": "system", "content": initial_prompt,}
    messages.append(initial_context)

    if prompt:
        messages.append({"role": "user", "content": prompt})

        try:
            stream = client.chat.completions.create(
                model="sonar",
                messages= messages,
                temperature=0.7,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except perplexity.APIConnectionError as e:
            error = "Network connection failed: " + e
            return 400, {'message':error}
        except perplexity.RateLimitError as e:
            error = "Rate limit exceeded, please retry later: " + e
            return 400, {'message':error}
        except perplexity.APIStatusError as e:
            error = "API error "+ e.status_code + ": " + e.response
            return 400, {'message':error}
        except Exception as e:
            error = "Unexpected error: " + e
            return 400, {'message':error}
    else:
        return 400, {'message':'No prompt received.'}