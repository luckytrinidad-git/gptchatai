import streamlit as st

# =========================
# CONFIG & INITIALIZATION
# =========================
st.title("Recent Prompts")
st.markdown("Review your recent consultations and AI interactions.")

# Check if history exists
if "messages" not in st.session_state or not st.session_state.messages:
    st.info("No recent prompts found. Start a conversation in the AI Interface to see history here.")
    if st.button("Go to Chat Assistant"):
        st.switch_page("pages/ai_interface.py")
    st.stop()

# =========================
# SIDEBAR TOOLS
# =========================
with st.sidebar:
    search_query = st.text_input("Filter History", placeholder="e.g. Income Tax")
    
    if st.button("Clear All History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# =========================
# DISPLAY LOGIC
# =========================

# Filter messages based on search (if any)
filtered_messages = st.session_state.messages
if search_query:
    filtered_messages = [
        m for m in st.session_state.messages 
        if search_query.lower() in m["content"].lower()
    ]

if not filtered_messages:
    st.warning(f"No results found for '{search_query}'")
else:
    # We display them in reverse order (newest at the top)
    # Since chat_message pairs User and Assistant, we iterate through pairs
    st.write(f"Showing {len(filtered_messages)} messages:")
    
    # We use a container for a cleaner scrollable look
    with st.container():
        for i in range(len(filtered_messages)):
            msg = filtered_messages[i]
            
            # Use columns to add a "time" or "index" label subtly
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                st.caption(f"#{i+1}")
            
            with col2:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # Add a subtle divider between pairs
            if msg["role"] == "assistant":
                st.markdown("---")