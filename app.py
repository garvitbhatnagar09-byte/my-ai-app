import urllib.parse
import requests
import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="My Conversational AI", page_icon="🤖", layout="wide"
)

# App Title
st.title("🤖 My Conversational AI")

# Sidebar for API Key input
st.sidebar.header("Configuration")
api_key_input = st.sidebar.text_input("Enter OpenRouter API Key", type="password")

# API Key Resolution Strategy
api_key = api_key_input
if not api_key and "OPENROUTER_API_KEY" in st.secrets:
    api_key = st.secrets["OPENROUTER_API_KEY"]

if not api_key:
    st.info("Please enter your OpenRouter API Key in the sidebar to start chatting.")
    st.stop()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []


def generate_pollinations_image(prompt, width=1024, height=1024, model="flux"):
    """
    Automatically enhances short user prompts to generate high-quality realistic images.
    """
    enhanced_prompt = f"high quality, realistic, detailed photograph of {prompt}"
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&enhance=true&nologo=true"


# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.image(message["content"], caption=message.get("prompt", ""))
        else:
            st.markdown(message["content"])

# User Input Box
user_prompt = st.chat_input("Ask a question or type /image <description>...")

if user_prompt:
    # Handle Image Generation Command
    if user_prompt.startswith("/image"):
        image_query = user_prompt.replace("/image", "").strip()

        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            if not image_query:
                error_msg = "Please provide a description after `/image`. Example: `/image cricket bat`"
                st.warning(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
            else:
                with st.spinner("Generating image..."):
                    img_url = generate_pollinations_image(image_query)
                    st.image(img_url, caption=image_query)
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "type": "image",
                            "content": img_url,
                            "prompt": image_query,
                        }
                    )

    # Handle Standard Text Chat
    else:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }

                    # Filter history to only include text messages for API request
                    api_messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                        if m.get("type") != "image"
                    ]

                    payload = {
                        "# NEW LINE 90:
                           "model": "google/gemini-2.5-flash",
                        "messages": api_messages,
                    }

                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code == 200:
                        reply = response.json()["choices"][0]["message"]["content"]
                        st.markdown(reply)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": reply}
                        )
                    else:
                        err_text = f"API Error ({response.status_code}): {response.text}"
                        st.error(err_text)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": err_text}
                        )

                except Exception as e:
                    st.error(f"Error connecting to OpenRouter: {str(e)}")
