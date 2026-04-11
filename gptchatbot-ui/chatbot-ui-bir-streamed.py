import streamlit as st
import requests
import time

# =========================
# CONFIG
# =========================
API_SERVER_URL = "http://13.213.49.77:5432/gptchatbot"

ENDPOINTS = {
    "openai": API_SERVER_URL + "/openai/ask-openai",
    "gemini": API_SERVER_URL + "/gemini/ask-gemini",
    "internal": API_SERVER_URL + "/rag/ask-bir",
}

st.set_page_config(page_title="BIR AI System", layout="wide")

# =========================
# SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "mode" not in st.session_state:
    st.session_state.mode = "chat"

# Internal DB flag only
if "internal_file_uploaded" not in st.session_state:
    st.session_state.internal_file_uploaded = False

# =========================
# HEADER
# =========================
st.title("BIR AI Assistant")
st.caption("AI-powered assistant for Bureau of Internal Revenue.")

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("Control Panel")

    model = st.selectbox(
        "AI Model",
        ["External AI", "Internal AI"]
    )

    st.divider()

    st.subheader("Document Upload")

    uploaded_file = st.file_uploader(
        "Upload receipts, forms, PDFs",
        type=["pdf", "csv", "txt", "xlsx", "docx"]
    )

    # =========================
    # INTERNAL AI → SAVE TO DB
    # =========================
    if model == "Internal AI":

        if uploaded_file and st.button("Upload to Knowledge Base"):

            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type
                )
            }

            data = {
                "prompt": "upload"
            }

            res = requests.post(
                ENDPOINTS["internal"],
                data=data,
                files=files,
                timeout=60
            )

            #st.write("STATUS:", res.status_code)
            #st.write("RESPONSE:", res.text)

            if res.status_code == 200:
                st.success(res.json()["response"])
            else:
                st.error("Upload failed")

    # =========================
    # EXTERNAL AI (NO DB, DIRECT FILE USE)
    # =========================
    if model == "External AI":

        if uploaded_file:
            st.info("File will be sent directly to AI (not stored)")

    st.divider()

    st.subheader("Tools")

    if st.button("Chat Mode"):
        st.session_state.mode = "chat"

    if st.button("Tax Calculator"):
        st.session_state.mode = "calculator"

# =========================
# CHAT HISTORY
# =========================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# =========================
# INPUT
# =========================
prompt = st.chat_input("Ask about anything...")

# =========================
# API ROUTER
# =========================
def select_api():
    if model == "External AI":
        return ENDPOINTS["openai"]
    elif model == "Gemini":
        return ENDPOINTS["gemini"]
    else:
        return ENDPOINTS["internal"]

# =========================
# PROCESS INPUT
# =========================
if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    api_url = select_api()

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):

            try:
                # =========================
                # BASE PAYLOAD
                # =========================
                payload = {
                    "prompt": prompt
                }

                files = None

                # =========================
                # EXTERNAL AI - SEND FILE DIRECTLY
                # =========================
                if model == "External AI" and uploaded_file:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue()
                        )
                    }

                # =========================
                # INTERNAL AI - NO FILE HERE (DB HANDLES IT)
                # =========================
                response = requests.post(
                    api_url,
                    data=payload,
                    files=files
                )

                if response.status_code == 200:

                    text = response.json().get("response", "No response")

                    placeholder = st.empty()
                    output = ""

                    for char in text:
                        output += char
                        placeholder.markdown(output)
                        time.sleep(0.003)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": text
                    })

                else:
                    st.error(f"API Error: {response.status_code}")

            except Exception as e:
                st.error(f"Request failed: {str(e)}")

# =========================
# FOOTER
# =========================
st.divider()
st.caption(
    "BIR AI is an advisory system and does not represent the Bureau of Internal Revenue. "
    "All outputs are for informational purposes only."
)