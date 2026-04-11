import streamlit as st
import requests
import os
import time
import re
from dotenv import load_dotenv
load_dotenv()

API_SERVER_URL = os.getenv("API_SERVER_URL")
API_URL = API_SERVER_URL + "/perplexity/ask-perplexity-streamed"

st.set_page_config(
    page_title="Perplexity Chat",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="auto"
)

st.title("💬 Finance and Sales Assistant")
st.write("Ask anything related to finance, economy, or investing.")

prompt = st.text_area("Enter your question:", height=150)

col1, col2, col3 = st.columns([0.9,1,0.2], vertical_alignment="bottom")

with col1:
    model_selection = st.selectbox('Model Selection', ['Perplexity','Claude'], index=0)
with col2:
    pass

with col3:
    ask_clicked = st.button("Ask", use_container_width=True)

response_container = st.container()


if ask_clicked:
    if not prompt.strip():
        response_container.warning("Please enter a prompt.")
    else:
        response_container.write('Response:')
        with st.spinner("Thinking..."):
            if model_selection == 'Perplexity':
                try:
                    output_placeholder = response_container.empty()
                    full_response = ""

                    # Make streaming request
                    with requests.post(API_URL, data={"prompt": prompt}, stream=True) as r:
                        if r.status_code == 200:
                            for chunk in r.iter_content(chunk_size=1024):
                                if chunk:
                                    decoded = chunk.decode("utf-8")
                                    # Split multiple lines in one chunk
                                    for line in decoded.split("\n"):
                                        if line.startswith("data:"):
                                            text = line[len("data:"):]
                                            if not text:
                                                continue
                                            
                                            # Split into tokens (words, punctuation, etc.)
                                            tokens = re.findall(r'\S+|\s+', text)
                                            for token in tokens:
                                                full_response += token
                                                # Optional: highlight the current token
                                                display_text = full_response[:-len(token)] + f"**{token}**"
                                                display_text = full_response.replace("\n", "  \n")
                                                output_placeholder.markdown(display_text)
                                                time.sleep(0.03)  # small delay for typing effect

                            # Final output without bold
                            output_placeholder.text(full_response)
                        else:
                            st.error(f"Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"Request failed: {e}")
            elif model_selection == 'Claude':
                st.write("Claude isn't available right now.")

