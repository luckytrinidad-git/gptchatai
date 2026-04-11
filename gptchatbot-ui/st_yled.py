import streamlit as st

def init():
    st.markdown("""
    <style>

    /* App background */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }

    /* Main container padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }

    /* Chat input styling */
    textarea {
        border-radius: 10px !important;
    }

    /* Buttons */
    div.stButton > button {
        background-color: #4f46e5;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
    }

    div.stButton > button:hover {
        background-color: #4338ca;
        color: white;
    }

    /* File uploader box */
    div[data-testid="stFileUploader"] {
        border-radius: 10px;
        padding: 10px;
    }

    /* Chat message styling */
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
    }

    /* Hide Streamlit default menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    </style>
    """, unsafe_allow_html=True)