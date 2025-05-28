import streamlit as st
import requests
import json
import os
from datetime import datetime
import uuid

st.set_page_config(
    page_title="MedReyGen - Medical Respiratory Assistant",
    page_icon="🫁",
    layout="centered"
)

st.title("MedReyGen 🫁")
st.subheader("Asisten Medis untuk Penyakit Pernapasan")
st.markdown("""
Asisten virtual untuk memberikan informasi, saran medis awal, dan panduan 
lanjutan mengenai penyakit pernapasan seperti pneumonia, tuberkulosis (TBC), dan COVID-19.
""")

# Paths untuk menyimpan data lokal
CHAT_HISTORY_DIR = "chat_histories"
CURRENT_SESSION_FILE = "current_session.json"

# Buat folder untuk menyimpan riwayat jika belum ada
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

# Fungsi load & save
def load_json(file_path, default=None):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return default
    return default

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Fungsi untuk membuat ID sesi baru
def generate_session_id():
    return str(uuid.uuid4())[:8]

# Fungsi untuk mendapatkan preview chat
def get_chat_preview(messages):
    if messages:
        first_user_msg = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        return first_user_msg[:50] + "..." if len(first_user_msg) > 50 else first_user_msg
    return "Chat Kosong"

# Fungsi untuk load semua riwayat chat
def load_all_chat_histories():
    histories = {}
    for filename in os.listdir(CHAT_HISTORY_DIR):
        if filename.endswith(".json"):
            session_id = filename.replace(".json", "")
            chat_data = load_json(os.path.join(CHAT_HISTORY_DIR, filename), default={})
            if chat_data:
                histories[session_id] = chat_data
    return histories

# Fungsi untuk menyimpan chat saat ini
def save_current_chat():
    if "current_session_id" in st.session_state and st.session_state.messages:
        chat_data = {
            "messages": st.session_state.messages,
            "current_disease": st.session_state.get("current_disease", None),
            "created_at": st.session_state.get("session_created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "title": get_chat_preview(st.session_state.messages)
        }
        
        session_file = os.path.join(CHAT_HISTORY_DIR, f"{st.session_state.current_session_id}.json")
        save_json(session_file, chat_data)
        
        # Simpan info sesi saat ini
        current_session_data = {
            "current_session_id": st.session_state.current_session_id,
            "last_updated": datetime.now().isoformat()
        }
        save_json(CURRENT_SESSION_FILE, current_session_data)

# Inisialisasi sesi
def initialize_session():
    # Cek apakah ini tab/window baru dengan melihat query params
    query_params = st.query_params
    
    if "new_chat" in query_params or "current_session_id" not in st.session_state:
        # Mulai chat baru
        st.session_state.current_session_id = generate_session_id()
        st.session_state.messages = []
        st.session_state.current_disease = None
        st.session_state.session_created_at = datetime.now().isoformat()
        
        # Hapus parameter new_chat dari URL
        if "new_chat" in query_params:
            st.query_params.clear()
    else:
        # Load sesi yang ada jika belum di-load
        if "messages" not in st.session_state:
            current_session_data = load_json(CURRENT_SESSION_FILE, default={})
            if current_session_data and "current_session_id" in current_session_data:
                session_id = current_session_data["current_session_id"]
                session_file = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
                chat_data = load_json(session_file, default={})
                
                if chat_data:
                    st.session_state.current_session_id = session_id
                    st.session_state.messages = chat_data.get("messages", [])
                    st.session_state.current_disease = chat_data.get("current_disease", None)
                    st.session_state.session_created_at = chat_data.get("created_at", datetime.now().isoformat())
                else:
                    # Jika file tidak ditemukan, buat sesi baru
                    st.session_state.current_session_id = generate_session_id()
                    st.session_state.messages = []
                    st.session_state.current_disease = None
                    st.session_state.session_created_at = datetime.now().isoformat()

# Initialize session
initialize_session()

# Function untuk deteksi penyakit
def detect_disease(text):
    text_lower = text.lower()
    if "pneumonia" in text_lower:
        return "pneumonia"
    elif "tuberkulosis" in text_lower or "tbc" in text_lower or "tb" in text_lower:
        return "tuberkulosis"
    elif "covid" in text_lower or "covid-19" in text_lower or "corona" in text_lower:
        return "covid-19"
    return None

# Sidebar: Riwayat Chat dan Konteks
with st.sidebar:
    st.header("Riwayat Chat")
    
    # Tombol untuk chat baru
    if st.button("💬 Chat Baru", use_container_width=True):
        # Simpan chat saat ini sebelum membuat yang baru
        save_current_chat()
        
        # Reset state untuk chat baru
        st.session_state.current_session_id = generate_session_id()
        st.session_state.messages = []
        st.session_state.current_disease = None
        st.session_state.session_created_at = datetime.now().isoformat()
        st.rerun()
    
    # Load dan tampilkan semua riwayat
    all_histories = load_all_chat_histories()
    
    if all_histories:
        st.markdown("### Riwayat Percakapan")
        for session_id, chat_data in sorted(all_histories.items(), 
                                          key=lambda x: x[1].get("updated_at", ""), 
                                          reverse=True):
            title = chat_data.get("title", f"Chat {session_id}")
            created_at = chat_data.get("created_at", "")
            
            # Format tanggal
            try:
                date_obj = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_str = date_obj.strftime("%d/%m %H:%M")
            except:
                date_str = "Unknown"
            
            # Highlight chat yang sedang aktif
            is_current = session_id == st.session_state.get("current_session_id", "")
            button_style = "🔹 " if is_current else "💬 "
            
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"{button_style}{title}", key=f"load_{session_id}", use_container_width=True):
                    # Simpan chat saat ini
                    save_current_chat()
                    
                    # Load chat yang dipilih
                    st.session_state.current_session_id = session_id
                    st.session_state.messages = chat_data.get("messages", [])
                    st.session_state.current_disease = chat_data.get("current_disease", None)
                    st.session_state.session_created_at = chat_data.get("created_at", datetime.now().isoformat())
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{session_id}", help="Hapus chat"):
                    # Hapus file chat
                    session_file = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
                    if os.path.exists(session_file):
                        os.remove(session_file)
                    
                    # Jika chat yang dihapus adalah chat aktif, buat chat baru
                    if session_id == st.session_state.get("current_session_id", ""):
                        st.session_state.current_session_id = generate_session_id()
                        st.session_state.messages = []
                        st.session_state.current_disease = None
                        st.session_state.session_created_at = datetime.now().isoformat()
                    
                    st.rerun()
            
            st.caption(f"📅 {date_str}")
            st.divider()
    
    # Informasi konteks penyakit
    st.header("Konteks Percakapan")
    if st.session_state.current_disease:
        st.info(f"Penyakit yang sedang dibahas: **{str(st.session_state.current_disease).upper()}**")
    else:
        st.info("Belum ada penyakit spesifik yang dibahas")
    
    # Info sesi saat ini
    st.markdown(f"**ID Sesi:** {st.session_state.get('current_session_id', 'Unknown')[:8]}")

# Tampilkan chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input pengguna
prompt = st.chat_input("Tanyakan sesuatu tentang penyakit pernapasan...")

BACKEND_URL = "http://localhost:5000/generate"

if prompt:
    # Tambahkan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Deteksi penyakit
    detected_disease = detect_disease(prompt)
    if detected_disease:
        st.session_state.current_disease = detected_disease

    # Simpan chat saat ini
    save_current_chat()

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Memikirkan jawaban..."):
            try:
                payload = {
                    "query": prompt,
                    "context": {
                        "current_disease": st.session_state.current_disease
                    }
                }

                response = requests.post(
                    BACKEND_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                response_data = response.json()
                assistant_response = response_data.get("response", "Maaf, terjadi kesalahan.")

                # Update konteks penyakit jika ada
                response_context = response_data.get("context", {})
                if response_context.get("current_disease"):
                    st.session_state.current_disease = response_context["current_disease"]

                # Deteksi dari respons juga
                disease_from_response = detect_disease(assistant_response)
                if disease_from_response:
                    st.session_state.current_disease = disease_from_response

                # Tampilkan dan simpan
                st.markdown(assistant_response)
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
                # Simpan chat yang sudah diupdate
                save_current_chat()

            except Exception as e:
                st.error(f"Error: {str(e)}")

# Auto-save ketika ada perubahan
if st.session_state.messages:
    save_current_chat()

# Instruksi untuk membuka tab baru
st.markdown("---")
st.markdown("💡 **Tips:** Untuk memulai chat baru di tab terpisah, buka `http://localhost:8501?new_chat=true`")