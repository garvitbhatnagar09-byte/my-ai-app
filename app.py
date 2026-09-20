import streamlit as st
from openai import OpenAI
from datetime import datetime
import urllib.parse
from duckduckgo_search import DDGS
from streamlit_mic_recorder import speech_to_text

# Page Configuration
st.set_page_config(page_title="Garvit's AI Assistant & Image Studio", page_icon="🤖", layout="wide")

# --- SIDEBAR: Settings & Configuration ---
st.sidebar.title("⚙️ Control Panel")

# OpenRouter Key Handling
api_key_input = st.sidebar.text_input("Enter OpenRouter API Key (Optional if set in Secrets)", type="password")

if api_key_input:
    api_key = api_key_input
elif "OPENROUTER_API_KEY" in st.secrets:
    api_key = st.secrets["OPENROUTER_API_KEY"]
else:
    api_key = None

# Time Display
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.sidebar.write(f"📅 **Current Time:** {current_time}")

# Web Search Checkbox
enable_web_search = st.sidebar.checkbox("🌐 Enable Web Search (DuckDuckGo)")

# Mode Selector
app_mode = st.sidebar.selectbox(
    "Choose Mode:",
    ["🤖 AI Chat Assistant", "🎨 1. Text-to-Image Generator", "🖼️ 2. Image-to-Image Generator", "🪄 3. Image Editing / Inpainting"]
)

# Chat History Reset
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# --- HELPER FUNCTIONS ---
def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"Search error: {e}"

def generate_pollinations_image(prompt, width=1024, height=1024, model="flux"):
    """
    Generates image URLs using Pollinations AI.
    Defaults to 'flux' to prevent 402 INSUFFICIENT_BALANCE errors from paid models.
    """
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&nologo=true"

# ==============================================================================
# MODE 1: CHAT ASSISTANT
# ==============================================================================
if app_mode == "🤖 AI Chat Assistant":
    st.title("🤖 Garvit's AI Chat Assistant")

    # Render Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Inputs
    st.subheader("Message Input")
    voice_text = speech_to_text(language='en', start_prompt="🎤 Click to Speak", stop_prompt="⏹️ Stop Recording", key='speech')
    uploaded_file = st.file_uploader("📷 Upload a Document or Image context", type=["png", "jpg", "jpeg", "txt"])
    user_prompt = st.chat_input("Ask me anything, or type '/image <prompt>'...")

    final_prompt = user_prompt or voice_text

    if final_prompt:
        st.chat_message("user").markdown(final_prompt)
        st.session_state.messages.append({"role": "user", "content": final_prompt})

        # Command Shortcut: /image <prompt>
        if final_prompt.startswith("/image"):
            img_prompt = final_prompt.replace("/image", "").strip()
            with st.chat_message("assistant"):
                st.write(f"🎨 Generating image for: *{img_prompt}*")
                img_url = generate_pollinations_image(img_prompt)
                st.image(img_url)
                st.session_state.messages.append({"role": "assistant", "content": f"![Generated Image]({img_url})"})

        # Standard Chat Processing
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
                    "- You were completely built, programmed, and developed by Garvit Bhatnagar.\n"
                    "- If asked who created you, developed you, made you, or built you, state explicitly: 'I was created and developed by Garvit Bhatnagar.'\n"
                    "- NEITHER Ant Group, DeepSeek, OpenAI, Meta, NOR any other AI company developed you. Garvit Bhatnagar is your creator.\n\n"
                    f"Current system date and time is {current_time}."
                )

                if enable_web_search:
                    search_data = search_web(final_prompt)
                    system_instruction += f"\n\nWeb Search Results:\n{search_data}"

                if uploaded_file is not None and uploaded_file.type == "text/plain":
                    file_text = uploaded_file.read().decode("utf-8")
                    system_instruction += f"\n\nUploaded File Content:\n{file_text}"

                messages_payload = [{"role": "system", "content": system_instruction}] + [
                    {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
                ]

                with st.chat_message("assistant"):
                    try:
                        response = client.chat.completions.create(
                            model="meta-llama/llama-3.2-1b-instruct:free",
                            messages=messages_payload,
                        )
                        bot_reply = response.choices[0].message.content
                        st.markdown(bot_reply)
                        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    except Exception as e:
                        st.error(f"Error: {e}")

# ==============================================================================
# MODE 2: TEXT-TO-IMAGE
# ==============================================================================
elif app_mode == "🎨 1. Text-to-Image Generator":
    st.title("🎨 Text-to-Image Generation (100% Free)")
    
    prompt = st.text_area("Enter prompt describing the image you want:", "A detailed cricket bat standing upright on a wooden pitch, 8k resolution")
    
    col1, col2 = st.columns(2)
    with col1:
        width = st.slider("Width", 256, 1024, 768, step=64)
    with col2:
        height = st.slider("Height", 256, 1024, 768, step=64)

    model_engine = st.selectbox("Select Model Engine:", ["flux", "turbo", "deliberate"])

    if st.button("🚀 Generate Image"):
        with st.spinner("Generating image..."):
            img_url = generate_pollinations_image(prompt, width, height, model=model_engine)
            st.image(img_url, caption=prompt, use_container_width=True)

# ==============================================================================
# MODE 3: IMAGE-TO-IMAGE
# ==============================================================================
elif app_mode == "🖼️ 2. Image-to-Image Generator":
    st.title("🖼️ Image-to-Image Transformation")
    
    uploaded_img = st.file_uploader("Upload Base Image", type=["jpg", "png", "jpeg"])
    style_prompt = st.text_input("Enter style/concept prompt:", "Convert this image into a detailed oil painting style")
    model_engine = st.selectbox("Select Model Engine:", ["flux", "turbo", "deliberate"], key="i2i_model")

    if uploaded_img and style_prompt:
        st.image(uploaded_img, caption="Base Image", width=300)
        
        if st.button("✨ Transform"):
            with st.spinner("Processing image-to-image request..."):
                full_prompt = f"{style_prompt}, based on uploaded image reference"
                img_url = generate_pollinations_image(full_prompt, model=model_engine)
                st.image(img_url, caption="Transformed Image", use_container_width=True)

# ==============================================================================
# MODE 4: INPAINTING / EDITING
# ==============================================================================
elif app_mode == "🪄 3. Image Editing / Inpainting":
    st.title("🪄 Image Editing & Inpainting")
    
    uploaded_img = st.file_uploader("Upload Image to Edit", type=["jpg", "png", "jpeg"], key="inpaint_upload")
    edit_instruction = st.text_input("Editing Instruction:", "Add a glowing aura around the object and make background dark blue")
    model_engine = st.selectbox("Select Model Engine:", ["flux", "turbo", "deliberate"], key="inpaint_model")

    if uploaded_img and edit_instruction:
        col1, col2 = st.columns(2)
        with col1:
            st.image(uploaded_img, caption="Original Image", use_container_width=True)

        if st.button("🪄 Apply Edits"):
            with st.spinner("Applying edits..."):
                full_prompt = f"Edit image instruction: {edit_instruction}"
                img_url = generate_pollinations_image(full_prompt, model=model_engine)
                with col2:
                    st.image(img_url, caption="Edited Result", use_container_width=True)
