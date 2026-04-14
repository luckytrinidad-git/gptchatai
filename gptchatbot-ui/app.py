import streamlit as st
from pathlib import Path

# =========================
# DYNAMIC PATH RESOLUTION
# =========================
# Ensures the app finds the folder whether on Windows or Linux
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()

# Define paths for your different logo versions
full_logo = current_dir / "logo" / "sidebar.png"
favicon = current_dir / "logo" / "logo.png" 

# =========================
# CONFIG & BRANDING
# =========================
st.set_page_config(
    page_title="BIR AI System",
    page_icon=str(favicon), # Use the small logo as the browser favicon
    initial_sidebar_state='expanded',
    layout="wide"
)

# Safety check for file existence to prevent the StreamlitAPIException
if full_logo.exists() and favicon.exists():
    st.logo(
        image=str(full_logo),      # Shown when sidebar is open
        size="large",
        icon_image=str(favicon)   # Shown when sidebar is closed (Navigation Logo)
    )
else:
    st.sidebar.error("One or more logo files are missing in ./bir_logo/")

# =========================
# NAVIGATION SETUP
# =========================
# Each Page points to a separate .py file in your /pages folder
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page("pages/chat.py", title="Chat Assistant", icon=":material/chat:"),
    st.Page("pages/history.py", title="Recent Prompts", icon=":material/history:"),
    st.Page("pages/audit_log.py", title="Audit Log", icon=":material/fact_check:"),
]

pg = st.navigation(pages, position="sidebar")

# =========================
# RUN NAVIGATION
# =========================
pg.run()