# streamlit_app.py
import streamlit as st
from gradio_client import Client
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
    .stApp { font-family: 'Arial', sans-serif; background: #f8f9fa; }
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
    st.markdown("**Paramètres:**")
    num_samples = st.slider("Échantillons audio", 1, 5, 2)

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

# === FORMULAIRE PRINCIPAL ===
st.markdown("### Nouvelle génération")

# Upload de vidéo
st.markdown('<div class="upload-section">', unsafe_allow_html=True)
uploaded_video = st.file_uploader(
    "Sélectionnez votre vidéo",
    type=["mp4", "avi", "mov", "mkv", "webm"],
    help="Formats supportés: MP4, AVI, MOV, MKV, WebM"
)
st.markdown('</div>', unsafe_allow_html=True)

# Description audio
st.markdown('<div class="description-section">', unsafe_allow_html=True)
audio_description = st.text_area(
    "Décrivez l'audio que vous souhaitez générer:",
    value="",
    placeholder="Exemple: ragazzo che suona la chitarra, bruit de pas, musique d'ambiance, explosion...",
    height=120,
    help="Soyez précis dans votre description pour de meilleurs résultats"
)

additional_notes = st.text_input(
    "Notes supplémentaires (optionnel):",
    placeholder="Style, intensité, ambiance particulière..."
)
st.markdown('</div>', unsafe_allow_html=True)

# === SECTION DE DEBUG (temporaire) ===
with st.expander("🔧 Debug Info", expanded=False):
    st.write(f"**Vidéo uploadée:** {uploaded_video is not None}")
    st.write(f"**Description:** '{audio_description}'")
    st.write(f"**Description nettoyée:** '{audio_description.strip() if audio_description else 'VIDE'}'")
    st.write(f"**Longueur description:** {len(audio_description) if audio_description else 0}")
    st.write(f"**Client connecté:** {st.session_state.foley_client is not None}")

# === BOUTON GÉNÉRATION ===
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_button = st.button(
        "🚀 Générer l'Audio", 
        use_container_width=True,
        type="primary"
    )

# === TRAITEMENT ===
if generate_button:
    # Validation claire et détaillée
    if not uploaded_video:
        st.error("❌ Aucune vidéo sélectionnée. Veuillez d'abord uploader une vidéo.")
    elif not audio_description or len(audio_description.strip()) == 0:
        st.error("❌ Description audio vide. Veuillez décrire l'audio souhaité.")
    elif not st.session_state.foley_client:
        st.error("❌ Modèle non connecté. Veuillez rafraîchir la page.")
    else:
        # GÉNÉRATION
        description_clean = audio_description.strip()
        
        try:
            # Sauvegarde vidéo temporaire
            video_path = os.path.join(TEMP_DIR, f"input_video_{uuid.uuid4().hex}.mp4")
            with open(video_path, "wb") as f:
                f.write(uploaded_video.read())
            
            st.info(f"🎵 Génération en cours pour: '{description_clean}'")
            
            with st.spinner("Traitement par l'IA... Cela peut prendre quelques minutes."):
                
                # === APPEL API HUNYUAN FOLEY - MULTI TENTATIVES ===
                api_names_to_try = [
                    "/generate",
                    "/inference", 
                    "/run",
                    "/foley_generate",
                    "/audio_generation"
                ]
                
                result = None
                successful_api = None
                
                for api_name in api_names_to_try:
                    try:
                        st.info(f"Tentative avec API: {api_name}")
                        
                        result = st.session_state.foley_client.predict(
                            video_input=video_path,
                            text_input=description_clean,
                            sample_nums=num_samples,
                            api_name=api_name
                        )
                        
                        if result:
                            successful_api = api_name
                            st.success(f"Succès avec API: {api_name}")
                            break
                            
                    except Exception as api_error:
                        st.warning(f"Échec avec {api_name}: {str(api_error)}")
                        continue
                
                # Traitement du résultat
                if result:
                    st.success("🎉 Audio généré avec succès!")
                    
                    # Sauvegarde des résultats
                    audio_files = []
                    
                    if isinstance(result, list):
                        for idx, audio_data in enumerate(result):
                            audio_file_path = os.path.join(TEMP_DIR, f"generated_audio_{uuid.uuid4().hex}.wav")
                            
                            # Copie du fichier audio
                            if isinstance(audio_data, str) and os.path.exists(audio_data):
                                shutil.copy2(audio_data, audio_file_path)
                                audio_files.append(audio_file_path)
                    
                    elif isinstance(result, str) and os.path.exists(result):
                        audio_file_path = os.path.join(TEMP_DIR, f"generated_audio_{uuid.uuid4().hex}.wav")
                        shutil.copy2(result, audio_file_path)
                        audio_files.append(audio_file_path)
                    
                    # Préparation du message utilisateur
                    user_message = f"Audio: {description_clean}"
                    if additional_notes.strip():
                        user_message += f" | {additional_notes.strip()}"
                    
                    # Ajout à l'historique
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_message,
                        "video": video_path
                    })
                    
                    ai_response = f"Audio généré: {len(audio_files)} fichier(s) pour '{description_clean}'"
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ai_response,
                        "audio_files": audio_files
                    })
                    
                    # Affichage immédiat du résultat
                    st.markdown('<div class="result-section">', unsafe_allow_html=True)
                    st.markdown("### 🎶 Résultat généré")
                    
                    col_video, col_audio = st.columns([1, 1])
                    
                    with col_video:
                        st.markdown("**Vidéo originale:**")
                        st.video(video_path)
                    
                    with col_audio:
                        st.markdown("**Audio généré:**")
                        for idx, audio_file in enumerate(audio_files):
                            if os.path.exists(audio_file):
                                st.audio(audio_file)
                                
                                with open(audio_file, "rb") as f:
                                    st.download_button(
                                        f"⬇️ Télécharger Audio {idx+1}",
                                        data=f.read(),
                                        file_name=f"audio_generated_{idx+1}.wav",
                                        mime="audio/wav",
                                        key=f"download_new_{idx}"
                                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                else:
                    st.error("❌ Aucun résultat retourné par le modèle")
                
        except Exception as e:
            st.markdown('<div class="error-section">', unsafe_allow_html=True)
            st.error(f"❌ Erreur lors de la génération: {str(e)}")
            st.markdown("**Solutions possibles:**")
            st.markdown("- Vérifiez votre connexion internet")
            st.markdown("- Essayez avec une vidéo plus courte")
            st.markdown("- Reformulez votre description")
            st.markdown("- Réessayez dans quelques minutes")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Enregistrer l'erreur dans l'historique
            error_message = f"Erreur: {description_clean}"
            st.session_state.chat_history.append({
                "role": "user",
                "content": error_message,
                "video": video_path if 'video_path' in locals() else None
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"Erreur lors de la génération: {str(e)}"
            })
        
        # Sauvegarde automatique
        save_chat_history(st.session_state.chat_history, st.session_state.chat_id)

# === EXEMPLES D'UTILISATION ===
st.markdown("---")
st.markdown("### 💡 Exemples de descriptions")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **🎵 Musique:**
    - ragazzo che suona la chitarra
    - piano dolce e melodioso
    - batteria energica
    - violino romantico
    """)

with col2:
    st.markdown("""
    **🔊 Effets sonores:**
    - passi sulla ghiaia
    - porta che scricchiola
    - vento tra gli alberi
    - motore di auto
    """)

with col3:
    st.markdown("""
    **🌍 Ambiances:**
    - caffè affollato
    - pioggia leggera
    - onde del mare
    - traffico cittadino
    """)

# === INSTRUCTIONS ===
st.markdown("---")
st.markdown("### 📋 Come usare l'app")

st.markdown("""
1. **Carica la tua vidéo** - Seleziona un file video dal tuo computer
2. **Descrivi l'audio** - Scrivi cosa vuoi sentire (in italiano o inglese)
3. **Clicca Genera** - Aspetta che l'IA elabori la richiesta
4. **Scarica il risultato** - Ottieni i file audio generati

**Nota:** La generazione può richiedere 1-3 minuti a seconda della lunghezza del video.
""")

# === RESET ===
if st.session_state.chat_history:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🗑️ Cancella tutto", use_container_width=True):
            # Pulire anche i file temporanei
            for message in st.session_state.chat_history:
                if message["role"] == "user" and "video" in message and message["video"]:
                    if os.path.exists(message["video"]):
                        try:
                            os.remove(message["video"])
                        except:
                            pass
                elif message["role"] == "assistant" and "audio_files" in message:
                    for audio_file in message["audio_files"]:
                        if os.path.exists(audio_file):
                            try:
                                os.remove(audio_file)
                            except:
                                pass
            
            st.session_state.chat_history = []
            save_chat_history([], st.session_state.chat_id)
            st.rerun()

# === STATUS ===
st.markdown("---")
if st.session_state.foley_client:
    st.success("🟢 Modèle HunyuanVideo-Foley prêt")
else:
    st.error("🔴 Modèle non disponible - vérifiez votre connexion")
