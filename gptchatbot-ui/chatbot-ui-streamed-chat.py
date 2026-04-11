import streamlit as st
import requests
import os
import time
import re
from dotenv import load_dotenv
load_dotenv()

API_SERVER_URL = os.getenv("API_SERVER_URL")
API_URL = API_SERVER_URL + "/perplexity/ask-perplexity-streamed"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        output_placeholder = st.empty()
        full_response = ""

        try:
            # Streaming request to PerplexityAI API
            with requests.post(API_URL, data={"prompt": prompt}, stream=True) as r:
                if r.status_code == 200:
                    buffer = ""
                    for chunk in r.iter_content(chunk_size=1024):
                        if not chunk:
                            continue

                        decoded = chunk.decode("utf-8")
                        buffer += decoded

                        # SSE events are separated by double newline
                        while "\n\n" in buffer:
                            event, buffer = buffer.split("\n\n", 1)
                            if not event.startswith("data:"):
                                continue
                            text = event[len("data:"):]
                            full_response += text

                            # Just display the raw text
                            output_placeholder.text(full_response)

                    # Display any leftover text
                    if buffer.strip():
                        full_response += buffer
                        output_placeholder.text(full_response)

                else:
                    st.error(f"Error {r.status_code}: {r.text}")

        except Exception as e:
            st.error(f"Request failed: {e}")

        # Save assistant message to session state
        st.session_state.messages.append({"role": "assistant", "content": full_response})