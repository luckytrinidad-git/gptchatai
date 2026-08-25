import streamlit as st
import pandas as pd
import requests
import time
import os
import sys
import django
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
# 1. CROSS-PROJECT DJANGO SETUP
# =========================
# On Linux/Docker, we use the volume path /gptchatbot-api
if os.name != 'nt': 
    api_path = "/gptchatbot-api"
    if api_path not in sys.path:
        sys.path.append(api_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gptchatbot.settings')

try:
    django.setup()
except Exception as e:
    st.error(f"Django Setup Error: {e}")
    st.info(f"Paths: {sys.path}")
    st.stop()

from django.db import connections

# =========================
# 2. CONFIG & ENDPOINTS
# =========================
from app import API_URL, REVIE_URL, REVIE_API_KEY
INGEST_API_URL = f"{API_URL}/rag/ingest-knowledge"
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
            
        o1, o2, o3 = st.columns(3)
        with o1: o_type = st.text_input("Office Type")
        with o2: division = st.text_input("Division")
        with o3: classif = st.selectbox("Classification", ["Simple", "Complex", "Highly Technical"])

        up_file = st.file_uploader("Upload Source", type=FILE_EXTENSIONS)
        submit = st.form_submit_button("Upload & Process", use_container_width=True, type="primary")

        if submit and title and up_file:
            with st.status("Processing...", expanded=True) as status:
                try:
                    files = {"file": (up_file.name, up_file.getvalue(), up_file.type)}
                    payload = {
                        "title": title, "agent": agent_id, "uploaded_by": uploaded_by,
                        "office_type": o_type, "division": division, "classification": classif
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
# 4. VIEW REPOSITORY (Direct DB Read)
# =========================
st.subheader("Unified Knowledge Repository")
try:
    #birai_db must be defined in your settings.py DATABASES
    view_df = pd.read_sql("""
        SELECT t.id, t.topic_title, t.agent, t.file_name, t.uploaded_at
        FROM kx_topics t 
        LEFT JOIN rag_birdocument r ON t.id = r.topic_id 
        GROUP BY t.id, t.topic_title, t.agent, t.file_name, t.uploaded_at
        ORDER BY t.uploaded_at DESC
    """, connections["birai_db"])
    st.dataframe(view_df, use_container_width=True, hide_index=True)
except Exception as e:
    st.info(f"Database connection issues: {e}")