import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# =========================
# DATABASE CONNECTION
# =========================
def get_birai_conn():
    try:
        return psycopg2.connect(
            host="13.215.160.167",
            database="birai_db",
            user="birai_admin",
            password="fortis12#$%",
            port="5432",
            connect_timeout=5
        )
    except Exception as e:
        st.error(f"Connection to Audit Database failed: {e}")
        return None

st.set_page_config(page_title="Audit Log - BIR AI System", layout="wide")

# =========================
# UI HEADER
# =========================
st.title("System Audit Log")
st.markdown("Official chronological record of system activities and data modifications.")

# =========================
# DATA FETCHING
# =========================
conn = get_birai_conn()
if conn:
    try:
        # 1. Fetch data using lowercase names (default Postgres behavior)
        query = "SELECT timestamp, username, action, module, status FROM audit_logs ORDER BY timestamp DESC"
        df_raw = pd.read_sql(query, conn)
        conn.close()

        if not df_raw.empty:
            # 2. FORCE RENAME columns to match the UI logic below
            # This prevents 'Status' vs 'status' errors
            df = df_raw.rename(columns={
                'timestamp': 'Timestamp',
                'username': 'User',
                'action': 'Action',
                'module': 'Module',
                'status': 'Status'
            })

            # --- 1. KPI METRICS ---
            total_logs = len(df)
            # Use lowercase in the logic to be safe when checking values
            success_count = len(df[df['Status'].str.lower() == 'success'])
            fail_count = total_logs - success_count
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Events", f"{total_logs:,}")
            m2.metric("Success Rate", f"{(success_count/total_logs*100):.1f}%" if total_logs > 0 else "0%")
            m3.metric("Failed Attempts", fail_count, delta_color="inverse")

            st.divider()

            # --- 2. SIDEBAR FILTERS ---
            with st.sidebar:
                st.header("Filter Records")
                
                selected_user = st.multiselect("Filter by User", options=df['User'].unique().tolist())
                selected_status = st.multiselect("Filter by Status", options=df['Status'].unique().tolist())
                selected_module = st.multiselect("Filter by Module", options=df['Module'].unique().tolist())

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

            # --- 3. DATA FILTERING LOGIC ---
            if selected_user:
                df = df[df['User'].isin(selected_user)]
            if selected_status:
                df = df[df['Status'].isin(selected_status)]
            if selected_module:
                df = df[df['Module'].isin(selected_module)]

            # --- 4. DATA DISPLAY ---
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

        else:
            st.info("No audit logs recorded in the database yet.")

    except Exception as e:
        st.error(f"Error processing logs: {e}")
else:
    st.warning("Ensure the database server is reachable.")

# =========================
# MANUAL REFRESH
# =========================
if st.button("Refresh Logs"):
    st.rerun()