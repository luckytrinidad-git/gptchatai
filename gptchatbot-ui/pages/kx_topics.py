import streamlit as st
import pandas as pd
import psycopg2
import time

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
        st.error(f"Connection failed: {e}")
        return None

st.set_page_config(page_title="KX Topics - Knowledge Manager", layout="wide")

# =========================
# UI HEADER
# =========================
st.title("KX Topics: Knowledge Manager")

# =========================
# KNOWLEDGE LIBRARY VIEW
# =========================
st.subheader("Indexed Knowledge Library")

conn = get_birai_conn()
if conn:
    try:
        query = """
        SELECT id, topic_title, office_type, classification, transaction_type, uploaded_at 
        FROM kx_topics 
        ORDER BY uploaded_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("The knowledge base is currently empty.")
    except Exception as e:
        st.error(f"Library Load Error: {e}")
st.divider()
st.markdown("Populate the **BIR Knowledge Base** using the official Citizen's Charter schema.")

# =========================
# UPLOAD & ENTRY FORM
# =========================
with st.expander("Add Service Guideline", expanded=True):
    with st.form("kx_form", clear_on_submit=True):
        
        # --- Row 1: Primary Identification ---
        col1, col2 = st.columns([3, 1])
        with col1:
            title = st.text_input("Topic Title (Service Name)", placeholder="e.g., Approval of Application for TIN of Local Employee")
        with col2:
            uploaded_by = st.text_input("Uploaded By", value="Admin")

        # --- Row 2: Office & Division ---
        o1, o2 = st.columns(2)
        with o1:
            o_type = st.text_input("Office Type", placeholder="e.g., Revenue District Office (RDO) / National Office")
        with o2:
            division = st.text_input("Office / Division", placeholder="e.g., Client Support Section (CSS) / ELTRD")

        # --- Row 3: Service Metadata ---
        m1, m2, m3 = st.columns(3)
        with m1:
            classif = st.selectbox("Classification", ["Simple", "Complex", "Highly Technical"])
        with m2:
            trans_type = st.selectbox("Transaction Type", ["G2C – Govt to Citizen", "G2B – Govt to Business", "G2G – Govt to Govt"])
        with m3:
            hours = st.text_input("Operating Hours", value="8:00 AM – 5:00 PM")

        # --- Row 4: Availability & Eligibility ---
        a1, a2 = st.columns(2)
        with a1:
            avail = st.text_area("Who may avail?", placeholder="e.g., All Hired Employees without existing TIN...")
        with a2:
            where = st.text_area("Where to avail", placeholder="e.g., Online thru ORUS (https://orus.bir.gov.ph) or Walk-in at RDO")

        # --- Row 5: File Upload ---
        st.markdown("### 📎 Reference Document")
        # Fixed: Closed the function call correctly
        up_file = st.file_uploader(
            "Upload PDF, DOCX, TXT, or XLSX", 
            type=["pdf", "docx", "txt", "xlsx"],
            disabled=not title
        )

        st.divider()
        
        # --- Form Validation Logic ---
        # The button will be disabled if there's no title OR no file uploaded
        is_form_invalid = not title or up_file is None
        
        # Fixed: Corrected string quotes and parentheses
        submit = st.form_submit_button(
            "Upload to Knowledge base", 
            use_container_width=True, 
            type="primary",
            disabled=is_form_invalid
        )
        
        if is_form_invalid:
            st.caption("⚠️ **Title** and **File** are required to enable the upload button.")

        if submit:
            conn = get_birai_conn()
            if conn:
                with st.status("Storing Knowledge in PostgreSQL...", expanded=True) as status:
                    try:
                        cur = conn.cursor()
                        file_bytes = up_file.getvalue()
                        
                        sql = """
                        INSERT INTO kx_topics (
                            topic_title, office_type, office_division, classification, 
                            transaction_type, who_may_avail, where_to_avail, operating_hours, 
                            file_name, file_data, uploaded_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        cur.execute(sql, (
                            title, o_type, division, classif, 
                            trans_type, avail, where, hours, 
                            up_file.name, file_bytes, uploaded_by
                        ))
                        
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        status.update(label="Sync Complete!", state="complete")
                        st.success(f"Successfully indexed: **{title}**")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database Error: {e}")

