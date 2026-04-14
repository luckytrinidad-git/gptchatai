import streamlit as st
import requests
import time

# =========================
# CONFIG & ENDPOINTS
# =========================
API_SERVER_URL = "http://13.213.49.77:8000/gptchatbot"
ENDPOINTS = {
    "openai": API_SERVER_URL + "/openai/ask-openai",
    "gemini": API_SERVER_URL + "/gemini/ask-gemini",
    "internal": API_SERVER_URL + "/rag/ask-bir",
}

# =========================
# INITIALIZATION
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Chat Assistant")

# =========================
# SIDEBAR SETTINGS
# =========================
with st.sidebar:
    # st.markdown("### Configuration")
    with st.container():
        model = st.selectbox(
            "Intelligence Engine", 
            ["BIR AI"],
            help="Choose 'BIR AI' for BIR knowledge-based answers."
        )
    # st.subheader("Document Upload")
    uploaded_file = st.file_uploader(
        "Document Upload", 
        type=["pdf", "csv", "txt", "xlsx", "docx"],
    )

    # Internal AI Knowledge Base Upload
    if model == "Internal AI" and uploaded_file:
        if st.button("Upload to Knowledge Base", use_container_width=True):
            with st.spinner("Indexing document..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    res = requests.post(ENDPOINTS["internal"], data={"prompt": "upload"}, files=files, timeout=60)
                    if res.status_code == 200:
                        st.success("Document Indexed")
                    else:
                        st.error("Upload failed")
                except Exception as e:
                    st.error(f"Error: {e}")

    if model == "BIR AI" and uploaded_file:
        st.info("Document successfully indexed.")

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# =========================
# CHAT INTERFACE
# =========================
# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask about anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Determine API Endpoint
    api_map = {"BIR AI": ENDPOINTS["openai"], "Internal AI": ENDPOINTS["internal"]}
    api_url = api_map.get(model)

# Process Assistant Response
    with st.chat_message("assistant"):
        # Use st.spinner for a clean "Loading..." look without the running icon
        with st.spinner("Loading..."):
            try:
                payload = {"prompt": prompt}
                files = None
                
                if model == "BIR AI" and uploaded_file:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

                response = requests.post(api_url, data=payload, files=files, timeout=45)
                
                if response.status_code == 200:
                    text = response.json().get("response", "No response")
                else:
                    st.error(f"API Error {response.status_code}")
                    st.stop()
            except Exception as e:
                st.error(f"Request failed: {str(e)}")
                st.stop()

        # Smooth Typewriter Effect
        placeholder = st.empty()
        full_response = ""
        for chunk in text.split(" "):
            full_response += chunk + " "
            placeholder.markdown(full_response + "▌")
            time.sleep(0.04)
        placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": text})