import streamlit as st
import requests
import time
import json
from ui_utils import hide_running_man
from logger_utils import log_action

st.set_page_config(page_title="Chat Assistant", layout="wide")
hide_running_man() 

# =========================
# CONFIG & ENDPOINTS
# =========================
API_SERVER_URL = "http://13.213.49.77:8000/gptchatbot"
REVIE_URL = "http://13.215.160.167:8000/gptchatbot/revie/ask-revie"
REVIE_API_KEY = "ef12476b-98f5-4f45-a6f5-23a0eab05d9a"

ENDPOINTS = {
    "openai": API_SERVER_URL + "/openai/ask-openai",
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
    with st.container():
        model = st.selectbox(
            "Agent", 
            ["External Source", "Revie", "Tax Information", "Revenue Issuances", 
             "Registration Requirements", "International Tax Matters", 
             "Legal Matters", "Human Resource"],
            help="Select the specific knowledge base for your inquiry."
        )

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# =========================
# CHAT INTERFACE
# =========================

# 1. Redraw history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 2. Handle new User Input
if prompt := st.chat_input("Ask about anything..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Process Assistant Response
    with st.chat_message("assistant"):
        with st.spinner(f"Agent {model} is thinking..."):
            try:
                # --- NEW ENDPOINT LOGIC ---
                if model == "Revie":
                    # Logic: If model is Revie -> use Revie Endpoint
                    headers = {
                        "X-GPT-API-Key": REVIE_API_KEY, 
                        "Content-Type": "application/json"
                    }
                    data = {"prompt": prompt}
                    response = requests.post(REVIE_URL, json=data, headers=headers, timeout=60)
                
                elif model = "External Source":
                    # Logic: If NOT External Source (and not Revie) -> Internal
                    payload = {
                        "prompt": prompt,
                        "agent": model,
                        "history": json.dumps(st.session_state.messages[:-1])
                    }
                    response = requests.post(ENDPOINTS["openai"], data=payload, timeout=60)
                
                else:
                    # Logic: Else (is External Source) -> OpenAI
                    payload = {
                        "prompt": prompt,
                        "agent": model,
                        "history": json.dumps(st.session_state.messages[:-1])
                    }
                    response = requests.post(ENDPOINTS["internal"], data=payload, timeout=60)
                
                # 4. ROBUST RESPONSE PARSING
                if response.status_code == 200:
                    res_json = response.json()
                    text = (
                        res_json.get("answer") or 
                        res_json.get("response") or 
                        res_json.get("output") or 
                        res_json.get("text") or 
                        "Error: Response format not recognized."
                    )
                    status_log = "success"
                else:
                    text = f"API Error {response.status_code}: {response.text}"
                    status_log = "failed"
            
            except Exception as e:
                text = f"Connection error: {e}"
                status_log = "error"

        # 5. Typewriter Effect
        placeholder = st.empty()
        full_res = ""
        words = text.split(" ")
        for chunk in words:
            full_res += chunk + " "
            placeholder.markdown(full_res + "▌")
            time.sleep(0.02)
        placeholder.markdown(full_res)

        # 6. Log Action (Must happen before rerun)
        log_action(
            username="End User", 
            action=f"Queried Agent: {model}", 
            module="Chat Assistant",
            status=status_log
        )

        # 7. Save Assistant Response and Rerun
        st.session_state.messages.append({"role": "assistant", "content": text})
        st.rerun()