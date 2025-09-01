# streamlit_app.py
import streamlit as st
from gradio_client import Client, handle_file
import json
import os
import uuid
import tempfile
import shutil

# === CONFIG ===
st.set_page_config(
    page_title="Video Audio AI",
    page_icon="🎬",
    layout="wide"
)

# === DIRECTORIES ===
CHAT_DIR = "chats"
TEMP_DIR = "temp_files"
os.makedirs(CHAT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# === UTILS ===
def save_chat_history(history, chat_id):
    file_path = os.path.join(CHAT_DIR, f"{chat_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_chat_history(chat_id):
    file_path = os.path.join(CHAT_DIR, f"{chat_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def list_chats():
    files = [f.replace(".json", "") for f in os.listdir(CHAT_DIR) if f.endswith(".json")]
    return sorted(files, reverse=True)

# === CSS INTERFACE CLAIRE ===
st.markdown("""
<style>
.stApp {
    font-family: 'Arial', sans-serif;
    background: #f8f9fa;
}
.main-header {
    text-align: center;
    font-size: 2.5rem;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 1rem;
    padding: 20px 0;
}
.subtitle {
    text-align: center;
    font-size: 1.1rem;
    color: #7f8c8d;
    margin-bottom: 2rem;
}
.upload-section {
    background: white;
    padding: 30px;
    border-radius: 12px;
    border: 2px dashed #3498db;
    margin: 20px 0;
    text-align: center;
}
.description-section {
    background: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin: 20px 0;
}
.generate-btn {
    background: linear-gradient(135deg, #3498db, #2980b9);
    color: white;
    border: none;
    padding: 15px 40px;
    border-radius: 8px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    margin: 20px 0;
}
.result-section {
    background: #ecf0f1;
    padding: 25px;
    border-radius: 12px;
    margin: 20px 0;
    border-left: 4px solid #27ae60;
}
.error-section {
    background: #fadbd8;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #e74c3c;
    margin: 20px 0;
}
.stButton > button {
    background: linear-gradient(135deg, #3498db, #2980b9);
    color: white;
    border: none;
    padding: 12px 30px;
    border-radius: 8px;
    font-weight: 600;
}
.stTextArea textarea {
    border: 2px solid #bdc3c7;
    border-radius: 8px;
    padding: 15px;
    font-size: 1rem;
}
</style>
""", unsafe_allow_html=True)

# === INIT SESSION STATE ===
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history(st.session_state.chat_id)

# === INIT CLIENT ===
if "foley_client" not in st.session_state:
    st.session_state.foley_client = None
try:
    with st.spinner("Connexion au modèle HunyuanVideo-Foley..."):
        st.session_state.foley_client = Client("tencent/HunyuanVideo-Foley")
        st.success("Modèle connecté avec succès!")
except Exception as e:
    st.error(f"Erreur de connexion: {str(e)}")

# === SIDEBAR ===
with st.sidebar:
    st.title("Projets")
    if st.button("Nouveau Projet", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        save_chat_history(st.session_state.chat_history, st.session_state.chat_id)
        st.rerun()

    available_chats = list_chats()
    if available_chats:
        selected_chat = st.selectbox(
            "Projets sauvegardés:",
            available_chats,
            index=available_chats.index(st.session_state.chat_id) if st.session_state.chat_id in available_chats else 0
        )
        if selected_chat != st.session_state.chat_id:
            st.session_state.chat_id = selected_chat
            st.session_state.chat_history = load_chat_history(st.session_state.chat_id)
            st.rerun()

    st.markdown("---")
    st.markdown("**Paramètres Avancés:**")
    num_samples = st.slider("Échantillons audio", 1, 5, 1)
    guidance_scale = st.slider("Guidance Scale", 1.0, 10.0, 4.5, 0.5)
    inference_steps = st.slider("Étapes d'inférence", 10, 100, 50, 5)

# === HEADER ===
st.markdown('<h1 class="main-header">🎬 Video Audio AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Générez de l\'audio pour vos vidéos avec l\'IA</p>', unsafe_allow_html=True)

# === HISTORIQUE ===
if st.session_state.chat_history:
    st.markdown("### Historique des générations")
    for i, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            with st.expander(f"Projet {len(st.session_state.chat_history)//2 - i//2}", expanded=False):
                st.write(f"**Description:** {message['content']}")
                if "video" in message and message["video"] and os.path.exists(message["video"]):
                    st.video(message["video"])
                # Chercher la réponse AI correspondante
                if i + 1 < len(st.session_state.chat_history):
                    ai_response = st.session_state.chat_history[i + 1]
                    if ai_response["role"] == "assistant":
                        st.write(f"**Résultat:** {ai_response['content']}")
                        if "generated_video" in ai_response and ai_response["generated_video"] and os.path.exists(ai_response["generated_video"]):
                            st.markdown("**Vidéo avec audio:**")
                            st.video(ai_response["generated_video"])
                            with open(ai_response["generated_video"], "rb") as f:
                                st.download_button(
                                    "Télécharger Vidéo avec Audio",
                                    data=f.read(),
                                    file_name=f"video_with_audio_{i}.mp4",
                                    mime="video/mp4",
                                    key=f"dl_video_{i}"
                                )
                        if "audio_files" in ai_response and ai_response["audio_files"]:
                            for idx, audio_file in enumerate(ai_response["audio_files"]):
                                if os.path.exists(audio_file):
                                    st.audio(audio_file)
                                    with open(audio_file, "rb") as f:
                                        st.download_button(
                                            f"Télécharger Audio {idx+1}",
                                            data=f.read(),
                                            file_name=f"foley_audio_{idx+1}.wav",
                                            mime="audio/wav",
                                            key=f"dl_{i}_{idx}"
                                        )

