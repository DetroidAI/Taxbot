import streamlit as st
from openai import OpenAI
import os

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["API_KEY"])

# App config
st.set_page_config(page_title="GST & Tax Assistant", page_icon="💼", layout="wide")

# Custom CSS for dark theme + chat bubbles
st.markdown("""
    <style>
    body {
        background-color: #1e1e1e;
        color: #f5f5f5;
    }
    .chat-bubble-user {
        background-color: #3a3a3a;
        color: #fff;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px;
        text-align: right;
    }
    .chat-bubble-assistant {
        background-color: #2d2d2d;
        color: #0f0;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px;
        text-align: left;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("💼 GST & Taxation Assistant")

# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# File upload
uploaded_file = st.file_uploader("📎 Upload an invoice or bill", type=["txt", "pdf", "jpg", "png"])

if uploaded_file:
    st.success("✅ File uploaded. (Currently placeholder – parsing logic can be added)")

# Chat input
user_input = st.chat_input("Type your query here...")

if user_input:
    # Store user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # OpenAI response
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": "You are a professional GST and taxation assistant for Chartered Accountants."},
            *[{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages]
        ]
    )

    reply = response.output[0].content[0].text

    # Store assistant message
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Display chat
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-assistant'>{msg['content']}</div>", unsafe_allow_html=True)