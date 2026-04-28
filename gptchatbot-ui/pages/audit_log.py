import streamlit as st
import pandas as pd
import os
import sys
import django
from datetime import datetime

# ==========================================
# 1. CROSS-PROJECT DJANGO SETUP
# ==========================================
# Path logic to find gptchatbot-api from gptchatbot-ui/pages/
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

# Helper to hide the "Running..." man
try:
    from ui_utils import hide_running_man
except ImportError:
    def hide_running_man(): pass

# =========================
# 2. UI CONFIGURATION
# =========================
# set_page_config MUST be the first streamlit command
st.set_page_config(page_title="Audit Log - BIR AI System", layout="wide")
hide_running_man()

def get_db_connection():
    """Uses the central Django connection instead of hardcoded credentials."""
    try:
        return connections["birai_db"]
    except Exception as e:
        st.error(f"Connection to Audit Database failed: {e}")
        return None

# =========================
# 3. UI HEADER
# =========================
st.title("System Audit Log")
st.markdown("Official chronological record of system activities and data modifications.")

# =========================
# 4. DATA FETCHING & LOGIC
# =========================
conn = get_db_connection()

if conn:
    try:
        # Fetch data
        query = "SELECT timestamp, username, action, module, status FROM audit_logs ORDER BY timestamp DESC"
        df_raw = pd.read_sql(query, conn)
        
        # Note: We don't manually close conn here because Django manages the lifecycle

        if not df_raw.empty:
            # Force rename for UI consistency
            df = df_raw.rename(columns={
                'timestamp': 'Timestamp',
                'username': 'User',
                'action': 'Action',
                'module': 'Module',
                'status': 'Status'
            })

            # --- KPI METRICS ---
            total_logs = len(df)
            success_count = len(df[df['Status'].str.lower() == 'success'])
            fail_count = total_logs - success_count
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Events", f"{total_logs:,}")
            m2.metric("Success Rate", f"{(success_count/total_logs*100):.1f}%" if total_logs > 0 else "0%")
            m3.metric("Failed Attempts", fail_count, delta_color="inverse")

            st.divider()

            # --- SIDEBAR FILTERS ---
            with st.sidebar:
                st.header("Filter Records")
                
                selected_user = st.multiselect("Filter by User", options=sorted(df['User'].unique().tolist()))
                selected_status = st.multiselect("Filter by Status", options=sorted(df['Status'].unique().tolist()))
                selected_module = st.multiselect("Filter by Module", options=sorted(df['Module'].unique().tolist()))

                st.divider()
                st.subheader("Data Export")
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Audit Report (CSV)",
                    data=csv_data,
                    file_name=f"BIR_Audit_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            # --- DATA FILTERING LOGIC ---
            if selected_user:
                df = df[df['User'].isin(selected_user)]
            if selected_status:
                df = df[df['Status'].isin(selected_status)]
            if selected_module:
                df = df[df['Module'].isin(selected_module)]

            # --- DATA DISPLAY ---
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Timestamp": st.column_config.DatetimeColumn("Date & Time", format="D MMM YYYY, h:mm a"),
                    "Status": st.column_config.TextColumn("Status"),
                    "User": st.column_config.TextColumn("Actor"),
                }
            )

            if st.button("Refresh Logs"):
                st.rerun()

        else:
            st.info("No audit logs recorded in the database yet.")

    except Exception as e:
        st.error(f"Error processing logs: {e}")
else:
    st.warning("Database configuration 'birai_db' not found in Django settings.")