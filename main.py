import streamlit as st
import sqlite3
import datetime
import pandas as pd
import os
import requests
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Load environment variables
load_dotenv()

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="Nao Medical: Dr-Patient Bridge", layout="wide", page_icon="🏥")

# 1. Initialize Session State
if "role" not in st.session_state:
    st.session_state.role = "Doctor"
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# --- DATABASE MANAGEMENT ---
def init_db():
    # Using v3 to ensure clean schema with room_id
    conn = sqlite3.connect('medical_chat_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT,
            role TEXT,
            original_text TEXT,
            translated_text TEXT,
            target_lang TEXT,
            has_audio BOOLEAN,
            audio_bytes BLOB,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# --- HUGGING FACE API INTEGRATION ---
# Qwen 2.5 7B is highly capable and currently stable on the free tier
REPO_ID = "Qwen/Qwen2.5-7B-Instruct"

def get_llm_response(messages, api_key):
    """
    Robust handler for HF API with error catching for 402/Quotas.
    """
    # 1. Try Standard Client (Best for speed)
    try:
        client = InferenceClient(model=REPO_ID, token=api_key)
        response = client.chat_completion(
            messages=messages, 
            max_tokens=500, 
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        # 2. Raw HTTP Fallback (Often fixes routing/library issues)
        try:
            api_url = f"https://api-inference.huggingface.co/models/{REPO_ID}/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": REPO_ID,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.3
            }
            response = requests.post(api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 402:
                return "Error: Free Tier Limit Reached (402). Try a new HF Token."
            else:
                return f"API Error {response.status_code}: {response.text}"
                
        except Exception as inner_e:
            return f"Critical Error: {str(inner_e)}"

def translate_text(text, source_role, target_lang, api_key):
    # FIX: Don't translate the system audio placeholder
    if text == "[Audio Message Attached]":
        return text

    # PROMPT FIX: "Natural, spoken language" prevents weird literal translations
    system_instruction = f"""
    You are a professional medical interpreter. Translate the {source_role}'s input into {target_lang}. 
    Use natural, spoken language that a normal person would use. 
    Avoid poetic, formal, or financial vocabulary (e.g., do not use 'giravat' for upset stomach).
    Output ONLY the translation.
    """
    
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": text}
    ]
    return get_llm_response(messages, api_key)

def generate_summary(history_text, api_key):
    system_instruction = "Summarize the following Doctor-Patient conversation. Format output with headers: 1. Symptoms, 2. Diagnoses, 3. Medications, 4. Follow-up Actions."
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": history_text}
    ]
    return get_llm_response(messages, api_key)

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("🏥 Nao Med Bridge")
    
    # Secure Key Handling
    env_key = os.getenv("HF_API_KEY")
    key_source = ".env"
    if not env_key:
        try:
            if "HF_API_KEY" in st.secrets:
                env_key = st.secrets["HF_API_KEY"]
                key_source = "Secrets"
        except:
            pass

    if env_key:
        hf_api_key = env_key
        st.success(f"✅ Key loaded from {key_source}")
    else:
        hf_api_key = st.text_input("Hugging Face API Key", type="password")
    
    st.caption(f"Model: {REPO_ID}")
    st.divider()

    # Room ID (Privacy Fix)
    st.subheader("Session Info")
    room_id = st.text_input("Room ID / Patient Name", value="Room-1", help="Change this to switch conversations")
    
    # Role & Language
    st.subheader("User Role")
    role = st.radio("I am the:", ["Doctor", "Patient"], key="role_radio")
    st.session_state.role = role
    
    target_lang = st.selectbox("Translate Output To:", ["English", "Spanish", "French", "Hindi", "Mandarin"])
    
    st.divider()
    
    # Search Feature
    st.subheader("🔍 Search Logs")
    search_query = st.text_input("Search keywords...")
    
    st.divider()
    
    if st.button("Generate Medical Summary"):
        if not hf_api_key:
            st.error("Please provide an API Key first.")
        else:
            # Filter by Room ID
            df = pd.read_sql_query("SELECT role, original_text FROM messages WHERE room_id = ?", conn, params=(room_id,))
            if not df.empty:
                full_text = "\n".join([f"{row['role']}: {row['original_text']}" for index, row in df.iterrows()])
                with st.spinner("Analyzing..."):
                    summary = generate_summary(full_text, hf_api_key)
                    st.markdown(summary)
            else:
                st.warning("No history in this room.")

# --- MAIN CHAT INTERFACE ---
st.header(f"Conversation: {room_id} ({st.session_state.role})")

# 1. Fetch History (Filtered by Room)
base_query = "SELECT * FROM messages WHERE room_id = ?"
params = [room_id]

if search_query:
    # We fetch everything first, but we could filter in SQL too. 
    # Logic below handles highlighting in Python for better UI control.
    pass

df_msgs = pd.read_sql_query(base_query + " ORDER BY timestamp ASC", conn, params=params)

# 2. Display Loop with Highlighting
for index, row in df_msgs.iterrows():
    # Filter visually if search is active
    if search_query:
        if search_query.lower() not in row['original_text'].lower() and search_query.lower() not in row['translated_text'].lower():
            continue

    avatar = "🧑‍⚕️" if row['role'] == "Doctor" else "🤕"
    with st.chat_message(row['role'], avatar=avatar):
        
        display_text = row['original_text']
        display_trans = row['translated_text']
        
        # Highlight Logic (Regex)
        if search_query:
            pattern = re.compile(re.escape(search_query), re.IGNORECASE)
            display_text = pattern.sub(lambda m: f":orange[**{m.group(0)}**]", display_text)
            display_trans = pattern.sub(lambda m: f":orange[**{m.group(0)}**]", display_trans)

        st.markdown(f"**{row['role']}:** {display_text}")
        st.info(f"**Translated ({row['target_lang']}):** {display_trans}")
        
        if row['has_audio'] and row['audio_bytes']:
            st.audio(row['audio_bytes'], format='audio/wav')
        
        st.caption(f"{row['timestamp']}")

# --- INPUT AREA ---
st.divider()
col1, col2 = st.columns([4, 1])

with col1:
    user_input = st.chat_input("Type your message here...")

with col2:
    audio_value = st.audio_input("Record Voice")

# --- LOGIC HANDLER ---
if user_input or audio_value:
    if not hf_api_key:
        st.error("⚠️ Please configure API Token.")
        st.stop()

    current_text = ""
    audio_data = None
    has_audio_flag = False
    should_save = False

    # 1. Handle Audio with Deduplication Loop Fix
    if audio_value:
        current_audio_bytes = audio_value.getvalue()
        
        # Check if we already processed this specific audio snippet
        if st.session_state.last_processed_audio != current_audio_bytes:
            audio_data = current_audio_bytes
            has_audio_flag = True
            st.session_state.last_processed_audio = current_audio_bytes  # Mark processed
            should_save = True
            
            if not user_input:
                current_text = "[Audio Message Attached]"
        else:
            should_save = False

    # 2. Handle Text
    if user_input:
        current_text = user_input
        should_save = True

    # 3. Execute Save & Translate
    if should_save and current_text:
        with st.spinner("Translating..."):
            translated = translate_text(current_text, st.session_state.role, target_lang, hf_api_key)
            
            c = conn.cursor()
            c.execute('''
                INSERT INTO messages (room_id, role, original_text, translated_text, target_lang, has_audio, audio_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, st.session_state.role, current_text, translated, target_lang, has_audio_flag, audio_data))
            conn.commit()
            
            st.rerun()