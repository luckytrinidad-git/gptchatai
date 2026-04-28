import streamlit as st
import pandas as pd
import requests
import time
import os
import sys
import django

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
# REVIE CONFIG
REVIE_URL = "http://13.215.160.167:8000/gptchatbot/revie/ask-revie"
REVIE_API_KEY = "ef12476b-98f5-4f45-a6f5-23a0eab05d9a"

# INGESTION CONFIG
INGEST_API_URL = "http://birgptchatbot-api:8000/gptchatbot/rag/ingest-knowledge"

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
            agent = st.selectbox("Agent Responsible", ["Tax Information","Revenue Issuances","Registration Requirements","International Tax Matters","Legal Matters","Human Resources"])
        with col3:
            uploaded_by = st.text_input("Uploaded By", value="Admin")
            
        o1, o2, o3 = st.columns(3)
        with o1: o_type = st.text_input("Office Type")
        with o2: division = st.text_input("Division")
        with o3: classif = st.selectbox("Classification", ["Simple", "Complex", "Highly Technical"])

        up_file = st.file_uploader("Upload Source", type=["pdf", "xlsx", "xls", "docx", "txt", "json", "csv"])
        submit = st.form_submit_button("Upload & Process", use_container_width=True, type="primary")

        if submit and title and up_file:
            with st.status("Processing...", expanded=True) as status:
                try:
                    files = {"file": (up_file.name, up_file.getvalue(), up_file.type)}
                    payload = {
                        "title": title, "agent": agent, "uploaded_by": uploaded_by,
                        "office_type": o_type, "division": division, "classification": classif
                    }
                    response = requests.post(INGEST_API_URL, data=payload, files=files, timeout=300)

                    if response.status_code == 200:
                        status.update(label="Upload Complete!", state="complete")
                        st.success(f"Successfully processed: {title}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"API Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# =========================
# 4. VIEW REPOSITORY (Direct DB Read)
# =========================
st.subheader("Unified Knowledge Repository")
try:
    #birai_db must be defined in your settings.py DATABASES
    view_df = pd.read_sql("""
        SELECT t.id, t.topic_title, t.agent, t.file_name, COUNT(r.id) as chunks, t.uploaded_at
        FROM kx_topics t 
        LEFT JOIN rag_birdocument r ON t.id = r.topic_id 
        GROUP BY t.id, t.topic_title, t.agent, t.file_name, t.uploaded_at
        ORDER BY t.uploaded_at DESC
    """, connections["birai_db"])
    st.dataframe(view_df, use_container_width=True, hide_index=True)
except Exception as e:
    st.info(f"Database connection issues: {e}")