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
        /* Hides the main menu if you want a cleaner look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )