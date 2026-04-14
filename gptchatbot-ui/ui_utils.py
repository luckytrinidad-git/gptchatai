import streamlit as st

def hide_running_man():
    st.markdown(
        """
        <style>
        /* Hides the top-right running indicator */
        [data-testid="stStatusWidget"] {
            visibility: hidden;
            display: none !important;
        }
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )