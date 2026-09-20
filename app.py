import random
import urllib.parse
from datetime import datetime
from PIL import Image
import streamlit as st
from duckduckgo_search import DDGS
from openai import OpenAI
from streamlit_mic_recorder import speech_to_text

st.set_page_config(
    page_title="All-in-One AI Assistant", page_icon="🤖", layout="wide"
)

# --- SIDEBAR: Settings & Secrets ---
st.sidebar.title("⚙️ Control Panel")

# Retrieve API key from Secrets or Sidebar
api_key_input = st.sidebar.text_input(
    "Enter OpenRouter API Key (Optional if set in Secrets)", type="password"
)

if api_key_input:
  api_key = api_key_input
elif "OPENROUTER_API_KEY" in st.secrets:
  api_key = st.secrets["OPENROUTER_API_KEY"]
else:
  api_key = None

# Display System Time
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.sidebar.write(f"📅 **Current Time:** {current_time}")

# Feature Selection
enable_web_search = st.sidebar.checkbox("🌐 Enable Web Search (DuckDuckGo)")

# Chat History Management
if "messages" not in st.session_state:
  st.session_state.messages = []

if st.sidebar.button("🗑️ Clear Chat History"):
  st.session_state.messages = []
  st.rerun()

st.title("🤖 All-in-One Free AI Assistant")


# --- HELPER FUNCTIONS ---
def generate_pollinations_image(prompt, width=1280, height=720):
  seed = random.randint(1, 999999)
  # Adding explicit photographic and spatial instructions
  enhanced_prompt = (
      f"full view studio product photo of {prompt}, entire object visible,"
      " centered, no cropping, professional studio lighting, 8k quality"
  )
  encoded_prompt = urllib.parse.quote(enhanced_prompt)

  # Using width=1280 & height=720 for a landscape aspect ratio
  return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux-realism&seed={seed}&nologo=true"


def generate_pollinations_image(prompt, width=1024, height=1024):
  seed = random.randint(1, 999999)
  # Enhanced prompt parameters for centered, uncropped subject focus
  enhanced_prompt = (
      f"{prompt}, centered, full view, professional photo, clean background,"
      " high detail"
  )
  encoded_prompt = urllib.parse.quote(enhanced_prompt)
  return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&seed={seed}&nologo=true"


# --- USER INPUT SECTION ---
st.subheader("Message Input")

# 1. Voice Input
voice_text = speech_to_text(
    language="en",
    start_prompt="🎤 Click to Speak",
    stop_prompt="⏹️ Stop Recording",
    key="speech",
)

# 2. File Upload
uploaded_file = st.file_uploader(
    "📷 Upload an Image or Document", type=["png", "jpg", "jpeg", "txt"]
)

# 3. Chat Text Input
user_prompt = st.chat_input(
    "Ask me anything, type '/image <prompt>' to generate an image, or paste a"
    " YouTube URL..."
)

# Determine final input source
final_prompt = user_prompt or voice_text

# Render past chat messages
for message in st.session_state.messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])

# --- PROCESSING USER REQUEST ---
if final_prompt:
  # Append User Message
  st.chat_message("user").markdown(final_prompt)
  st.session_state.messages.append({"role": "user", "content": final_prompt})

  # IMAGE GENERATION COMMAND
  if final_prompt.startswith("/image"):
    img_prompt = final_prompt.replace("/image", "").strip()
    with st.chat_message("assistant"):
      st.write(f"🎨 Generating image for: *{img_prompt}*")
      img_url = generate_pollinations_image(img_prompt)
      st.image(img_url)
      st.session_state.messages.append(
          {"role": "assistant", "content": f"![Generated Image]({img_url})"}
      )

  # REGULAR AI / TEXT PROCESSING
  else:
    if not api_key:
      st.error(
          "Missing API Key! Please enter an OpenRouter API Key in the sidebar"
          " or save it in Streamlit Secrets."
      )
    else:
      client = OpenAI(
          base_url="https://openrouter.ai/api/v1",
          api_key=api_key,
      )

      # Context augmentation with Developer Identity
      system_context = (
          f"You are an AI assistant created and developed by Garvit Bhatnagar. "
          f"If anyone asks who created, built, or developed you, state"
          f" clearly that you were created by Garvit Bhatnagar. Current"
          f" system date and time is {current_time}."
      )

      if enable_web_search:
        search_data = search_web(final_prompt)
        system_context += f"\nWeb Search Results:\n{search_data}"

      if uploaded_file is not None and uploaded_file.type == "text/plain":
        file_text = uploaded_file.read().decode("utf-8")
        system_context += f"\nUploaded File Content:\n{file_text}"

      messages_payload = [{"role": "system", "content": system_context}] + [
          {"role": m["role"], "content": m["content"]}
          for m in st.session_state.messages
      ]

      with st.chat_message("assistant"):
        try:
          response = client.chat.completions.create(
              model="openrouter/free",
              messages=messages_payload,
          )
          bot_reply = response.choices[0].message.content
          st.markdown(bot_reply)
          st.session_state.messages.append(
              {"role": "assistant", "content": bot_reply}
          )
        except Exception as e:
          st.error(f"Error: {e}")
