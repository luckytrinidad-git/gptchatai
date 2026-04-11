import streamlit as st
import requests
import os
import time
import re
import html
import st_yled

from dotenv import load_dotenv
load_dotenv()

API_SERVER_URL = os.getenv("API_SERVER_URL")
PERPLEXITY_API = API_SERVER_URL + "/perplexity/ask-perplexity"
GEMINI_API = API_SERVER_URL + "/gemini/ask-gemini"
CLAUDE_API = API_SERVER_URL + "/claude/ask-claude"
OPENAI_API = API_SERVER_URL + "/openai/ask-openai"

# Initialize styling - set for each app page
st_yled.init()

st.set_page_config(
    page_title="Helix AI",
    # page_title="Bureau Intelligent Response (BIR)",
    # page_icon="💬",
    # page_icon="BIR FINAL LOGO.png",
    layout="centered",
    initial_sidebar_state="auto"
)

# st.logo(
#     "bir-white-long-logo.png",
#     # link="https://streamlit.io/gallery",
#     icon_image="BIR FINAL LOGO.png",
#     size="large"
# )

# st.title("Smart Engagement Console")
titlecol1, titlecol2, = st.columns([1,0.1], vertical_alignment="bottom")

# with titlecol1:
# st.image("BIR FINAL LOGO.png",width=80)

# with titlecol2:
# st.title(" Bureau Intelligent Response (BIR)",width="content")
st.title("HelixAI",width="content")
st.write("Ask anything related to finance, economy, or investing.")

# Placeholder to properly control elements
col1,col2 = st.columns([0.4,0.6],vertical_alignment='bottom',)

with col1:
    model_selection_placeholder = st.empty()
    # text_message = st.empty()


submit_form_placeholder = st.empty()
# with st.form("Submit form",clear_on_submit=True,border=False):
#     prompt_placeholder = st.empty()
#     button_container =  st.container(horizontal=True,vertical_alignment='bottom',horizontal_alignment='right')
#     with button_container:
#         button_container.space('stretch')
#         button_placeholder = button_container.empty()


model_list = [
    'HelixAI',
    # 'GPT-5.4-mini',
    # 'Perplexity',
    'Gemini',
    # 'Claude'
    ]

# with col2:
    # if model_selection == 'Google Gemini':
    #     st.image("https://upload.wikimedia.org/wikipedia/commons/8/8f/Google-gemini-icon.svg",width=40)
    # if model_selection == 'Perplexity':
    #     st.markdown('<img src="https://upload.wikimedia.org/wikipedia/commons/b/b5/Perplexity_AI_Turquoise_on_White.png" width="40" style="margin:15px 0px">', unsafe_allow_html=True)

ask_container = st.container(vertical_alignment="bottom",horizontal=True,gap="large",horizontal_alignment="right")
# ask_container.space('stretch')
# ask_container.space('stretch')
# ask_container.space('stretch')
response_container = st.container()

with ask_container:
    model_selection = model_selection_placeholder.selectbox('Model', 
                                    model_list, 
                                    index=0)

# if model_selection == "HelixAI":
#     # submit_form_placeholder.write('hello')
#     uploaded_file = col1.file_uploader('Document upload',width='stretch',max_upload_size=10,label_visibility='visible',accept_multiple_files=False,)
    # if uploaded_file is not None:
    #     # To read file as bytes:
    #     bytes_data = uploaded_file.getvalue()
    #     st.write(bytes_data)

    #     # To convert to a string based IO:
    #     stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    #     st.write(stringio)

    #     # To read file as string:
    #     string_data = stringio.read()
    #     st.write(string_data)

    #     # Can be used wherever a "file-like" object is accepted:
    #     dataframe = pd.read_csv(uploaded_file)
    #     st.write(dataframe)
if model_selection:
    accept_file = False
    model_disabled = False
    if model_selection in ['Claude','Perplexity']:
        model_disabled = True
    elif model_selection in ['Helix','TEST']:
        accept_file = True
    
    with submit_form_placeholder.form("Submit form",clear_on_submit=True,border=True):
        prompt_placeholder = st.empty()
        button_container =  st.container(horizontal=True,vertical_alignment='bottom',horizontal_alignment='right')
        with button_container:
            file_upload_button = button_container.empty()
            button_placeholder = button_container.empty()

        uploaded_file = None
        if not model_selection == 'Gemini':
            with file_upload_button:
                uploaded_file = st_yled.file_uploader(
                    'Document Upload',
                    width='stretch',
                    max_upload_size=10,
                    label_visibility='collapsed',
                    accept_multiple_files=False,
                    type=["pdf", "csv", "txt", "xlsx", "docx"],
                    border_style="none",
                    background_color="#ffffff00"
                    )
        
            
    # ask_clicked = ask_container.button("Ask", use_container_width=True, disabled=model_disabled,type='secondary')
    # file_upload_button = file_upload_button.button('Upload file')
    button_placeholder.space('large')
    ask_button = button_placeholder.form_submit_button('Ask')
    prompt = prompt_placeholder.text_area("Enter your question:", height=150, disabled=model_disabled)
    # prompt = prompt_placeholder.chat_input("Ask your question", disabled=model_disabled,accept_file=accept_file)
    # if model_disabled == True:
    #     text_message.caption('Model currently not available.')

    # response_container = st.container()

    if ask_button:
        if not prompt.strip():
            response_container.warning("Please enter a prompt.")
        else:
            response_container.write('Response:')
            # Chat input, reuse later
            # if model_selection == 'TEST':
            #     with st.chat_message("user"):
            #         st.write(prompt.text)
            with st.chat_message("user"):
                st.write(prompt)
            with st.spinner("Thinking..."):
                if model_selection == 'Perplexity':
                    # api_url = PERPLEXITY_API
                    st.info("Perplexity isn't available right now.")
                elif model_selection == 'Gemini':
                    api_url = GEMINI_API
                elif model_selection == 'Claude':
                    st.info("Claude isn't available right now.")
                    # api_url = CLAUDE_API
                # elif model_selection == 'GPT-5.4-mini':
                elif model_selection == 'HelixAI':
                    api_url = OPENAI_API

                try:
                    if uploaded_file:
                        files = {
                            "file": (uploaded_file.name, uploaded_file.getvalue())
                        }
                        response = requests.post(
                            api_url,
                            data={"prompt": prompt},
                            files=files
                        )
                    else:
                        response = requests.post(api_url, data={"prompt": prompt})

                    if response.status_code == 200:
                        data = response.json()
                        text = data.get("response", "No response received.")

                        if model_selection == 'Perplexity':
                            source_list = data.get("source_list", "No sources received.")

                            # Maps citation numbers with their actual reference URL
                            source_map = {}
                            for src in source_list:
                                num, url = src.split(". ", 1)
                                source_map[num] = url

                            # Replace citations with clickable markdown links
                            def replace_citation(match):
                                num = match.group(1)
                                if num in source_map:
                                    return f" [[{num}]]({source_map[num]}) "
                                return match.group(0)

                            clickable_text = re.sub(r"\[(\d+)\]", replace_citation, text)
                            text = clickable_text
                        # with st.chat_message("user"):
                        #     st.write(prompt)
                        with st.chat_message("assistant"):
                            # Simulate typing effect
                            placeholder = st.empty()
                            displayed = ""
                            for char in text:
                                displayed += char
                                placeholder.markdown(displayed)
                                time.sleep(0.01)  # adjust typing speed here

                            # List down sources/references for Perplexity
                            if model_selection == 'Perplexity':
                                cited_numbers = re.findall(r"\[(\d+)\]", text)
                                cited_numbers = sorted(set(map(int, cited_numbers)))

                                st.markdown("---")
                                expanded_state = True if cited_numbers else False

                                with st.expander("References:", expanded=expanded_state):
                                    if not cited_numbers:
                                        st.write("No sources cited in the response.")
                                    else:
                                        for num in cited_numbers:
                                            # Find the matching source in the list
                                            idx = num - 1  # because your list is 1-indexed
                                            if 0 <= idx < len(source_list):
                                                st.markdown(f"{num}. [{source_list[idx].split('. ',1)[1]}]({source_list[idx].split('. ',1)[1]})")

                    else:
                        # st.error(f"Error {response.status_code}: {response.text}")
                        st.error(f"There seems to be a problem with {model_selection} AI. Please try another model.")
                except Exception as e:
                    st.error(f"Request failed: {e}")
