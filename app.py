import streamlit as st
from openai import OpenAI
from datetime import datetime, timedelta, timezone
from PIL import Image
from duckduckgo_search import DDGS
from streamlit_mic_recorder import speech_to_text
import urllib.parse
import base64

st.set_page_config(page_title="Garvit's AI Assistant", page_icon="🤖", layout="wide")

# --- SIDEBAR: Settings & Secrets ---
st.sidebar.title("⚙️ Control Panel")

# Retrieve API key from Secrets or Sidebar
api_key_input = st.sidebar.text_input("Enter OpenRouter API Key (Optional if set in Secrets)", type="password")

if api_key_input:
    api_key = api_key_input
elif "OPENROUTER_API_KEY" in st.secrets:
    api_key = st.secrets["OPENROUTER_API_KEY"]
else:
    api_key = None

# Display India Standard Time (UTC + 5:30)
ist_timezone = timezone(timedelta(hours=5, minutes=30))
current_time = datetime.now(ist_timezone).strftime("%Y-%m-%d %H:%M:%S")
st.sidebar.write(f"📅 **Current Time (IST):** {current_time}")

# Feature Selection
enable_web_search = st.sidebar.checkbox("🌐 Enable Web Search (DuckDuckGo)")

# Chat History Management
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

st.title("🤖 Garvit's AI Assistant")

# --- HELPER FUNCTIONS ---
def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"Search error: {e}"

def generate_image_url(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

def encode_uploaded_image(file):
    file.seek(0)
    return base64.b64encode(file.read()).decode('utf-8')

def extract_image_prompt(text):
    lowered = text.strip().lower()
    
    if lowered.startswith("/image"):
        return text[6:].strip()
    
    triggers = [
        "generate an image of", "generate image of", 
        "create an image of", "create image of",
        "draw an image of", "draw image of",
        "make an image of", "make image of"
    ]
    for trigger in triggers:
        if trigger in lowered:
            idx = lowered.find(trigger) + len(trigger)
            return text[idx:].strip()
            
    return None

# --- USER INPUT SECTION ---
st.subheader("Message Input")

# 1. Voice Input
st.caption("🎙️ *Note: Ensure browser permissions allow microphone access.*")
voice_text = speech_to_text(language='en', start_prompt="🎤 Click to Speak", stop_prompt="⏹️ Stop Recording", key='speech')

# 2. File Upload
uploaded_file = st.file_uploader("📷 Upload an Image or Document", type=["png", "jpg", "jpeg", "txt"])

if uploaded_file is not None and uploaded_file.type.startswith("image/"):
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image Preview", use_container_width=True)
    except Exception as e:
        st.error(f"Error previewing image: {e}")

# 3. Chat Text Input
user_prompt = st.chat_input("Ask me anything, or type 'create an image of...'")

final_prompt = user_prompt or voice_text

# Render past chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.image(message["url"], caption=message["caption"], use_container_width=True)
            st.markdown(f"[🔗 Open Full Size Image]({message['url']})")
        else:
            st.markdown(message["content"])

# --- PROCESSING USER REQUEST ---
if final_prompt or uploaded_file:
    prompt_text = final_prompt if final_prompt else "Describe and analyze this uploaded image."

    if final_prompt:
        st.chat_message("user").markdown(final_prompt)
        st.session_state.messages.append({"role": "user", "content": final_prompt})

    extracted_prompt = extract_image_prompt(prompt_text)

    # 1. IMAGE GENERATION TRIGGER
    if extracted_prompt is not None and not uploaded_file:
        if not extracted_prompt:
            with st.chat_message("assistant"):
                msg = "🎨 Please provide a descriptive prompt! Example: `create an image of a cricket bat on grass`"
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
        else:
            with st.chat_message("assistant"):
                st.write(f"🎨 Generating image for: *{extracted_prompt}*")
                with st.spinner("Rendering image..."):
                    img_url = generate_image_url(extracted_prompt)
                    st.image(img_url, caption=f"Generated: {extracted_prompt}", use_container_width=True)
                    st.markdown(f"[🔗 Open Full Size Image]({img_url})")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "image",
                        "url": img_url,
                        "caption": f"Generated: {extracted_prompt}"
                    })

    # 2. REGULAR AI / TEXT & VISION PROCESSING
    else:
        if not api_key:
            st.error("Missing API Key! Please enter an OpenRouter API Key in the sidebar or save it in Streamlit Secrets.")
        else:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )

            system_instruction = (
                "YOUR CORE IDENTITY:\n"
                "- You are an AI assistant created and developed exclusively by Garvit Bhatnagar.\n"
                "- If asked who created, developed, or built you, state explicitly: 'I was created and developed by Garvit Bhatnagar.'\n"
                "- NEVER claim to be created by OpenAI, Meta, DeepSeek, Google, or any other corporation.\n"
                f"Current system date and time (IST) is {current_time}."
            )

            if enable_web_search and final_prompt:
                with st.spinner("Searching the web..."):
                    search_data = search_web(final_prompt)
                if "Search error" not in search_data:
                    system_instruction += f"\n\nWeb Search Results:\n{search_data}"

            user_content = []

            # Document File Handling
            if uploaded_file is not None and uploaded_file.type == "text/plain":
                try:
                    uploaded_file.seek(0)
                    file_text = uploaded_file.read().decode("utf-8")
                    system_instruction += f"\n\nUploaded Document Context:\n{file_text}"
                except Exception as e:
                    st.error(f"Error reading text document: {e}")

            # Image File Handling
            is_image_attached = uploaded_file is not None and uploaded_file.type.startswith("image/")
            if is_image_attached:
                try:
                    base64_img = encode_uploaded_image(uploaded_file)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{uploaded_file.type};base64,{base64_img}"
                        }
                    })
                except Exception as e:
                    st.error(f"Error encoding uploaded image: {e}")

            user_content.append({
                "type": "text",
                "text": prompt_text
            })

            messages_payload = [{"role": "system", "content": system_instruction}]
            
            # Format message history
            for m in st.session_state.messages[:-1]:
                if m.get("type") != "image":
                    messages_payload.append({"role": m["role"], "content": m["content"]})

            messages_payload.append({"role": "user", "content": user_content})

            # Route to explicit vision model if image attached, else default free router
            selected_model = "google/gemma-4-31b-it:free" if is_image_attached else "openrouter/free"

            with st.chat_message("assistant"):
                try:
                    response = client.chat.completions.create(
                        model=selected_model,
                        messages=messages_payload,
                    )
                    bot_reply = response.choices[0].message.content
                    st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                except Exception as e:
                    st.error(f"Error processing request: {e}")
