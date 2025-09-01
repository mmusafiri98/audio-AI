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
    page_title="Vimeo Audio AI",
    page_icon="🎬",
    layout="wide"
)

# === DIRECTORIES ===
CHAT_DIR = "chats"
TEMP_DIR = "temp_files"
GALLERY_DIR = "gallery"
os.makedirs(CHAT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(GALLERY_DIR, exist_ok=True)  # ✅ Dossier permanent pour les vidéos générées

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

# Sauvegarde permanente des vidéos générées
def save_to_gallery(video_path):
    if video_path and os.path.exists(video_path):
        gallery_path = os.path.join(GALLERY_DIR, os.path.basename(video_path))
        shutil.copy2(video_path, gallery_path)
        return gallery_path
    return None

# === CSS INTERFACE CLAIRE ===
st.markdown("""
<style>
    .stApp { font-family: 'Arial', sans-serif; background: #f8f9fa; }
    .main-header { text-align: center; font-size: 2.5rem; font-weight: 700; color: #2c3e50; margin-bottom: 1rem; padding: 20px 0; }
    .subtitle { text-align: center; font-size: 1.1rem; color: #7f8c8d; margin-bottom: 2rem; }
    .upload-section { background: white; padding: 30px; border-radius: 12px; border: 2px dashed #3498db; margin: 20px 0; text-align: center; }
    .description-section { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin: 20px 0; }
    .generate-btn { background: linear-gradient(135deg, #3498db, #2980b9); color: white; border: none; padding: 15px 40px; border-radius: 8px; font-size: 1.1rem; font-weight: 600; cursor: pointer; margin: 20px 0; }
    .result-section { background: #ecf0f1; padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #27ae60; }
    .error-section { background: #fadbd8; padding: 20px; border-radius: 8px; border-left: 4px solid #e74c3c; margin: 20px 0; }
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

# === HEADER ===
st.markdown('<h1 class="main-header">🎬 Vimeo Audio AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Générez de l\'audio pour vos vidéos avec l\'IA</p>', unsafe_allow_html=True)

# === FORMULAIRE PRINCIPAL ===
st.markdown("### Nouvelle génération")

uploaded_video = st.file_uploader("Sélectionnez votre vidéo", type=["mp4", "avi", "mov", "mkv", "webm"])
audio_description = st.text_area("Décrivez l'audio que vous souhaitez générer:", value="", height=120)
additional_notes = st.text_input("Notes supplémentaires (optionnel):")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_button = st.button("🚀 Générer l'Audio", use_container_width=True)

# === TRAITEMENT ===
if generate_button:
    if not uploaded_video:
        st.error("❌ Aucune vidéo sélectionnée.")
    elif not audio_description.strip():
        st.error("❌ Description audio vide.")
    elif not st.session_state.foley_client:
        st.error("❌ Modèle non connecté.")
    else:
        video_path = os.path.join(TEMP_DIR, f"input_video_{uuid.uuid4().hex}.mp4")
        with open(video_path, "wb") as f:
            f.write(uploaded_video.read())

        st.info(f"🎵 Génération en cours pour: '{audio_description.strip()}'")

        try:
            result = st.session_state.foley_client.predict(
                video_file={"video": handle_file(video_path)},
                text_prompt=audio_description.strip(),
                guidance_scale=4.5,
                inference_steps=50,
                sample_nums=1,
                api_name="/process_inference"
            )

            if result:
                generated_video_path = None
                if isinstance(result, tuple) and len(result) > 0:
                    first_element = result[0]
                    if isinstance(first_element, dict) and 'video' in first_element:
                        original_video_path = first_element['video']
                        if os.path.exists(original_video_path):
                            generated_video_path = os.path.join(TEMP_DIR, f"video_with_audio_{uuid.uuid4().hex}.mp4")
                            shutil.copy2(original_video_path, generated_video_path)

                            # ✅ Sauvegarde dans la galerie permanente
                            gallery_video_path = save_to_gallery(generated_video_path)

                            st.success("🎉 Vidéo avec audio générée et sauvegardée dans la galerie!")
                            st.video(gallery_video_path)

                            with open(gallery_video_path, "rb") as f:
                                st.download_button(
                                    "⬇️ Télécharger Vidéo avec Audio",
                                    data=f.read(),
                                    file_name="video_with_foley_audio.mp4",
                                    mime="video/mp4"
                                )

        except Exception as e:
            st.error(f"❌ Erreur lors de la génération: {str(e)}")

# === GALERIE DES VIDÉOS SAUVEGARDÉES ===
st.markdown("---")
st.markdown("### 📂 Galerie des vidéos générées")

saved_videos = [f for f in os.listdir(GALLERY_DIR) if f.endswith(".mp4")]
if saved_videos:
    for vid in sorted(saved_videos, reverse=True):
        vid_path = os.path.join(GALLERY_DIR, vid)
        st.video(vid_path)
        with open(vid_path, "rb") as f:
            st.download_button(
                f"⬇️ Télécharger {vid}",
                data=f.read(),
                file_name=vid,
                mime="video/mp4",
                key=f"dl_{vid}"
            )
else:
    st.info("Aucune vidéo sauvegardée pour le moment.")

# === STATUS ===
st.markdown("---")
if st.session_state.foley_client:
    st.success("🟢 Modèle HunyuanVideo-Foley prêt")
else:
    st.error("🔴 Modèle non disponible - vérifiez votre connexion")

