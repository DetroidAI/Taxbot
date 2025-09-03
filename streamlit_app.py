import streamlit as st
from openai import OpenAI
import os

# --- Config ---
st.set_page_config(page_title="💬 GST & Tax Assistant", page_icon="💰", layout="wide")

API_KEY = st.secrets["API_KEY"]
client = OpenAI(api_key=API_KEY)

# --- Custom Theme (Grok/ChatGPT style vibes) ---
st.markdown("""
    <style>
        body {
            background-color: #0f172a; /* dark slate background */
            color: #f1f5f9;
        }
        .stTextInput, .stTextArea {
            background-color: #1e293b !important;
            color: #f1f5f9 !important;
            border-radius: 10px;
        }
        .chat-bubble-user {
            background-color: #2563eb; 
            color: white;
            padding: 10px 15px;
            border-radius: 12px;
            margin: 5px 0px 5px auto;
            max-width: 70%;
        }
        .chat-bubble-assistant {
            background-color: #334155; 
            color: #e2e8f0;
            padding: 10px 15px;
            border-radius: 12px;
            margin: 5px auto 5px 0px;
            max-width: 70%;
        }
    </style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown("<h2 style='text-align: center;'>💰 GST & Taxation Chat Assistant</h2>", unsafe_allow_html=True)

# --- Session state for chat ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- Display chat history ---
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-assistant'>{msg['content']}</div>", unsafe_allow_html=True)

# --- Input box at bottom ---
with st.container():
    user_input = st.text_input("Type your query here...", key="input_box")
    if st.button("Send"):
        if user_input.strip():
            # Save user msg
            st.session_state["messages"].append({"role": "user", "content": user_input})
            
            try:
                # Call OpenAI
                response = client.responses.create(
                    model="gpt-5-mini",
                    input=[
                        {"role": "developer", "content": [{"type": "input_text", "text": "You are a GST/taxation assistant. Respond concisely with calculations only."}]},
                        {"role": "user", "content": [{"type": "input_text", "text": user_input}]}
                    ]
                )
                output = response.output_text
                st.session_state["messages"].append({"role": "assistant", "content": output})
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ Error: {e}")