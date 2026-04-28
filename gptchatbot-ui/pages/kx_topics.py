import streamlit as st
import pandas as pd
import requests
import time
import os
import sys
import django
import psycopg2 # Required for the Binary wrapper
 
st.set_page_config(page_title="KX Topics - Knowledge Manager", layout="wide")

# Endpoint Configuration
API_URL = "http://13.213.49.77:8000/gptchatbot/rag/ingest-knowledge"

st.title("KX Topics: Knowledge Manager")
# ==========================================
# 1. CROSS-PROJECT DJANGO SETUP
# ==========================================
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
api_path = os.path.join(project_root, "gptchatbot-api")

if api_path not in sys.path:
    sys.path.append(api_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gptchatbot.settings')

try:
    django.setup()
except Exception as e:
    st.error(f"Django Setup Error: {e}")
    st.stop()

from django.db import connections

try:
    from ui_utils import hide_running_man
except ImportError:
    def hide_running_man(): pass

# =========================
# 2. INGESTION FORM
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
            with st.status("Uploading to Knowledge base...", expanded=True) as status:
                try:
                    # Prepare multi-part form data
                    files = {"file": (up_file.name, up_file.getvalue(), up_file.type)}
                    payload = {
                        "title": title,
                        "agent": agent,
                        "uploaded_by": uploaded_by,
                        "office_type": o_type,
                        "division": division,
                        "classification": classif
                    }

                    # Call the Django API
                    response = requests.post(API_URL, data=payload, files=files, timeout=300)

                    if response.status_code == 200:
                        status.update(label="Upload Complete!", state="complete")
                        st.success(f"Successfully processed: {title}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"API Error ({response.status_code}): {response.text}")
                
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# =========================
# 2. VIEW REPOSITORY (Direct DB Read)
# =========================
st.subheader("Unified Knowledge Repository")
try:
    # Direct read remains faster for the table view
    view_df = pd.read_sql("""
        SELECT t.id, t.topic_title, t.agent, t.file_name, COUNT(r.id) as chunks, t.uploaded_at
        FROM kx_topics t 
        LEFT JOIN rag_birdocument r ON t.id = r.topic_id 
        GROUP BY t.id, t.topic_title, t.agent, t.file_name, t.uploaded_at
        ORDER BY t.uploaded_at DESC
    """, connections["birai_db"])
    st.dataframe(view_df, use_container_width=True, hide_index=True)
except:
    st.info("Database not reachable or library empty.")