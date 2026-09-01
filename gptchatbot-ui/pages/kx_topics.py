import streamlit as st
import pandas as pd
import requests
import time
import os
from logger_utils import log_action
FILE_EXTENSIONS = [
    ext.strip().lower()
    for ext in os.getenv(
        "FILE_EXTENSIONS",
        ""
    ).split(",")
    if ext.strip()
]

print(FILE_EXTENSIONS)

# =========================
# 2. CONFIG & ENDPOINTS
# =========================
from app import API_URL, REVIE_URL, REVIE_API_KEY
INGEST_API_URL = f"{API_URL}/rag/ingest-knowledge"
REVIE_INGEST_URL = f"{API_URL}/revie/intents/import"
GENERAL_API_URL = f"{API_URL}/general"

st.title("KX Topics: Knowledge Manager")

# =========================
# 3. INGESTION FORM
# =========================
with st.expander("Ingest New Document", expanded=True):
    with st.form("kx_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            title = st.text_input("Topic Title")
        with col2:
            response = requests.get(f"{GENERAL_API_URL}/agents")
            agents = response.json()

            with col2:
                selected_agent = st.selectbox(
                    "Agent Responsible",
                    options=agents,
                    format_func=lambda x: x["agent"]
                )

            agent_id = selected_agent["id"]
            agent_name = selected_agent["agent"]
        with col3:
            uploaded_by = st.text_input("Uploaded By", value="Admin")

        up_file = st.file_uploader("Upload Source", type=FILE_EXTENSIONS)
        submit = st.form_submit_button("Upload & Process", use_container_width=True, type="primary")

        if submit and title and up_file:
            with st.status("Processing...", expanded=True) as status:
                try:
                    if agent_name == "Revie":
                        files = {"file": (up_file.name, up_file.getvalue(), up_file.type)}
                        payload = {
                            "title": title, "agent": agent_id, "uploaded_by": uploaded_by
                        }
                        response = requests.post(REVIE_INGEST_URL, data=payload, files=files, timeout=300)
                    else:
                        files = {"file": (up_file.name, up_file.getvalue(), up_file.type)}
                        payload = {
                            "title": title, "agent": agent_id, "uploaded_by": uploaded_by
                        }
                        response = requests.post(INGEST_API_URL, data=payload, files=files, timeout=300)

                    if response.status_code == 200:
                        # LOG THE ACTION
                        log_action(
                            username=uploaded_by, 
                            action=f"Ingested Doc: {title}", 
                            module="KX Topics: Knowledge Manager",
                            status="success"
                        )
                        status.update(label="Upload Complete!", state="complete")
                        st.success(f"Successfully processed: {title}")
                        time.sleep(1)
                        st.rerun()

                        
                    else:
                        st.error(f"API Error: {response.text}")

                        # LOG THE ACTION
                        log_action(
                            username=uploaded_by, 
                            action=f"Failed Ingestion: {title}", 
                            module="KX Topics: Knowledge Manager",
                            status="failed"
                        )
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# =========================
# 4. VIEW REPOSITORY
# =========================
st.subheader("Unified Knowledge Repository")
response = requests.get(f"{GENERAL_API_URL}/topics")

if response.status_code == 200:
    view_df = pd.DataFrame(response.json())
    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.error(f"Failed to load repository: {response.text}")