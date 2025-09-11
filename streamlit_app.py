import import streamlit as st
from openai import OpenAI
import os

client = OpenAI(api_key=st.secrets("API_KEY"))

st.title("GST & Taxation Assistant")

user_input = st.text_area("Enter calculation or upload invoice:")
uploaded_file = st.file_uploader("Upload Invoice Image", type=["png", "jpg", "jpeg"])

if st.button("Process"):
    inputs = [{"role": "user", "content": [{"type": "input_text", "text": user_input}]}]

    if uploaded_file:
        inputs[0]["content"].append({
            "type": "input_image",
            "image_url": uploaded_file.getvalue()  # sends bytes
        })

    response = client.responses.create(
        model="gpt-5-mini",
        input=inputs
    )

    st.write("### Result")
    st.text(response.output[0].content[0].text) as st


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

