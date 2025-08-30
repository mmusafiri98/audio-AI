# streamlit_app.py
import streamlit as st
from gradio_client import Client
import json
import os
import uuid
import tempfile

# === CONFIG ===
st.set_page_config(
    page_title="Video Foley AI",
    page_icon="🎬",
    layout="wide"
)

# === PATH PER LE CHAT MULTIPLE ===
CHAT_DIR = "chats"
TEMP_DIR = "temp_videos"
os.makedirs(CHAT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """
You are Video Foley AI.
Your role is to help users generate high-quality audio for their videos
based on video content and text descriptions.
You were created by Pepe Musafiri.
Always answer naturally and helpfully about audio generation.
"""

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
    return sorted(files)

def format_history_for_model(chat_history, limit=5):
    """Formate l'historique pour le modèle avec gestion des vidéos"""
    formatted_history = []
    
    recent_history = chat_history[-limit*2:] if len(chat_history) > limit*2 else chat_history
    
    i = 0
    while i < len(recent_history) - 1:
        if (recent_history[i]["role"] == "user" and 
            recent_history[i + 1]["role"] == "assistant"):
            
            user_content = recent_history[i]["content"]
            ai_content = recent_history[i + 1]["content"]
            
            if isinstance(user_content, str) and isinstance(ai_content, str):
                user_content = user_content.strip()
                ai_content = ai_content.strip()
                
                if (user_content and 
                    user_content != "Vidéo envoyée 🎬" and 
                    ai_content):
                    formatted_history.append([user_content, ai_content])
            
            i += 2
        else:
            i += 1
    
    return formatted_history

# === CSS ===
st.markdown("""
<style>
    body, .stApp { font-family: 'Inter', sans-serif; background: #0f0f23; color: #ffffff; }
    .main-header { text-align: center; font-size: 3rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; 
                   background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .subtitle { text-align: center; font-size: 1.2rem; color: #a0a0a0; margin-bottom: 2rem; }
    .chat-container { max-width: 1000px; margin: auto; padding: 20px; }
    .message-user, .message-ai { display: flex; margin: 15px 0; }
    .message-user { justify-content: flex-end; }
    .message-ai { justify-content: flex-start; }
    .bubble { border-radius: 16px; padding: 15px 20px; max-width: 75%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-size: 0.95rem; }
    .user-bubble { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    .ai-bubble { background: #1a1a2e; border: 1px solid #16213e; color: #ffffff; }
    .video-container { margin: 10px 0; padding: 15px; background: #16213e; border-radius: 12px; border: 1px solid #0f3460; }
    .audio-container { margin: 10px 0; padding: 15px; background: #16213e; border-radius: 12px; border: 1px solid #0f3460; }
    .form-container { background: #16213e; padding: 25px; border-radius: 12px; border: 1px solid #0f3460; margin-top: 20px; }
    .stButton button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; border: none; padding: 10px 25px; font-weight: 600; }
    .stButton button:hover { background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%); }
    .stSelectbox > div > div { background: #1a1a2e; color: white; border: 1px solid #0f3460; }
    .stTextInput > div > div > input { background: #1a1a2e; color: white; border: 1px solid #0f3460; }
    .stFileUploader > div { background: #1a1a2e; border: 1px solid #0f3460; border-radius: 8px; }
    .stApp > footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# === INIT SESSION STATE ===
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history(st.session_state.chat_id)

# === INIT HUNYUAN FOLEY CLIENT ===
if "foley_client" not in st.session_state:
    try:
        with st.spinner("🎬 Connexion au modèle HunyuanVideo-Foley..."):
            st.session_state.foley_client = Client("tencent/HunyuanVideo-Foley")
            st.success("✅ Modèle HunyuanVideo-Foley connecté !")
    except Exception as e:
        st.error(f"❌ Erreur de connexion au modèle: {e}")
        st.session_state.foley_client = None

# === SIDEBAR ===
st.sidebar.title("📂 Gestion des projets")

if st.sidebar.button("➕ Nouveau projet"):
    st.session_state.chat_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    save_chat_history(st.session_state.chat_history, st.session_state.chat_id)
    st.rerun()

available_chats = list_chats()
if available_chats:
    selected_chat = st.sidebar.selectbox(
        "💾 Vos projets sauvegardés :", 
        available_chats, 
        index=available_chats.index(st.session_state.chat_id) if st.session_state.chat_id in available_chats else 0
    )

    if selected_chat and selected_chat != st.session_state.chat_id:
        st.session_state.chat_id = selected_chat
        st.session_state.chat_history = load_chat_history(st.session_state.chat_id)
        st.rerun()

# === INFO SIDEBAR ===
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎵 Comment ça marche ?")
st.sidebar.markdown("""
1. **Upload ta vidéo** 📹
2. **Décris l'audio souhaité** 📝
3. **L'IA génère le son** 🎶
4. **Télécharge le résultat** ⬇️
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Paramètres avancés")
num_samples = st.sidebar.slider("Nombre d'échantillons audio", 1, 6, 3)
audio_length = st.sidebar.slider("Durée audio (sec)", 5, 30, 10)

# === UI HEADER ===
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown('<h1 class="main-header">🎬 Video Foley AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Génération automatique d\'audio pour vos vidéos avec IA</p>', unsafe_allow_html=True)

# === AFFICHAGE CHAT ===
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"""
        <div class="message-user">
            <div class="bubble user-bubble">{message['content']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Affichage vidéo
        if "video" in message and message["video"] is not None:
            if os.path.exists(message["video"]):
                st.markdown('<div class="video-container">', unsafe_allow_html=True)
                st.video(message["video"])
                st.markdown('</div>', unsafe_allow_html=True)
                
    else:
        st.markdown(f"""
        <div class="message-ai">
            <div class="bubble ai-bubble"><b>🎵 Foley AI:</b> {message['content']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Affichage audio généré
        if "audio_files" in message and message["audio_files"]:
            st.markdown('<div class="audio-container">', unsafe_allow_html=True)
            st.markdown("**🎶 Audio généré :**")
            for idx, audio_file in enumerate(message["audio_files"]):
                if os.path.exists(audio_file):
                    st.audio(audio_file, format="audio/wav")
                    st.download_button(
                        f"⬇️ Télécharger Audio {idx+1}",
                        data=open(audio_file, "rb").read(),
                        file_name=f"foley_audio_{idx+1}.wav",
                        mime="audio/wav",
                        key=f"download_{uuid.uuid4()}"
                    )
            st.markdown('</div>', unsafe_allow_html=True)

# === FORMULAIRE PRINCIPAL ===
st.markdown('<div class="form-container">', unsafe_allow_html=True)

with st.form("foley_form", clear_on_submit=True):
    st.markdown("### 🎬 Génération Audio pour Vidéo")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_video = st.file_uploader(
            "📹 Upload votre vidéo", 
            type=["mp4", "avi", "mov", "mkv"],
            help="Formats supportés: MP4, AVI, MOV, MKV"
        )
        
    with col2:
        audio_description = st.text_area(
            "🎵 Description de l'audio souhaité",
            placeholder="Ex: Bruit de pas sur gravier, musique d'ambiance, explosion, etc.",
            height=100
        )
    
    additional_notes = st.text_input(
        "💬 Notes supplémentaires (optionnel)",
        placeholder="Précisions sur le style, l'intensité, l'ambiance..."
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        submit = st.form_submit_button("🚀 Générer l'Audio", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# === TRAITEMENT ===
if submit and st.session_state.foley_client:
    if uploaded_video is not None and audio_description.strip():
        
        # Sauvegarde temporaire de la vidéo
        video_path = os.path.join(TEMP_DIR, f"video_{uuid.uuid4().hex}.mp4")
        with open(video_path, "wb") as f:
            f.write(uploaded_video.read())
        
        # Préparation du message utilisateur
        user_message = f"Audio: {audio_description.strip()}"
        if additional_notes.strip():
            user_message += f" | Notes: {additional_notes.strip()}"
        
        # Formatage de l'historique
        conversation_history = format_history_for_model(st.session_state.chat_history)
        
        try:
            with st.spinner("🎵 Génération de l'audio en cours... (peut prendre 1-3 minutes)"):
                
                # === APPEL AU MODÈLE HUNYUAN FOLEY ===
                result = st.session_state.foley_client.predict(
                    video_input=video_path,
                    text_input=audio_description.strip(),
                    sample_nums=num_samples,
                    api_name="/generate_audio"  # À ajuster selon l'API
                )
                
                # Traitement du résultat
                if result:
                    # Sauvegarde des fichiers audio générés
                    audio_files = []
                    if isinstance(result, list):
                        for idx, audio_data in enumerate(result):
                            audio_file_path = os.path.join(TEMP_DIR, f"audio_{uuid.uuid4().hex}_{idx}.wav")
                            # Sauvegarde selon le format retourné par l'API
                            if isinstance(audio_data, str) and os.path.exists(audio_data):
                                # Si c'est un chemin de fichier
                                import shutil
                                shutil.copy2(audio_data, audio_file_path)
                            audio_files.append(audio_file_path)
                    
                    # Ajout à l'historique
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_message,
                        "video": video_path
                    })
                    
                    ai_response = f"✅ Audio généré avec succès ! {len(audio_files)} échantillon(s) créé(s) basé(s) sur votre description : '{audio_description.strip()}'"
                    
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": ai_response,
                        "audio_files": audio_files
                    })
                    
                    st.success("🎉 Audio généré avec succès !")
                    
                else:
                    st.error("❌ Erreur lors de la génération audio")
                    
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")
            
            # Ajout d'un message d'erreur à l'historique
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_message,
                "video": video_path
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"❌ Désolé, une erreur s'est produite lors de la génération : {str(e)}"
            })
        
        # Sauvegarde de l'historique
        save_chat_history(st.session_state.chat_history, st.session_state.chat_id)
        st.rerun()
        
    elif not uploaded_video:
        st.warning("⚠️ Veuillez upload une vidéo")
    elif not audio_description.strip():
        st.warning("⚠️ Veuillez décrire l'audio souhaité")

# === CHAT TEXTE SIMPLE (sans vidéo) ===
st.markdown("---")
st.markdown("### 💬 Discussion avec Foley AI")

with st.form("text_chat_form", clear_on_submit=True):
    text_message = st.text_input("💬 Posez une question sur la génération audio")
    text_submit = st.form_submit_button("💫 Envoyer")

if text_submit and text_message.strip():
    conversation_history = format_history_for_model(st.session_state.chat_history)
    
    # Réponse simple sans génération audio
    simple_response = f"Merci pour votre question : '{text_message.strip()}'. Pour générer de l'audio, veuillez uploader une vidéo et décrire l'audio souhaité dans le formulaire ci-dessus."
    
    st.session_state.chat_history.append({
        "role": "user",
        "content": text_message.strip(),
        "video": None
    })
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": simple_response
    })
    
    save_chat_history(st.session_state.chat_history, st.session_state.chat_id)
    st.rerun()

# === RESET ===
if st.session_state.chat_history:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🗑️ Vider l'historique", use_container_width=True):
            st.session_state.chat_history = []
            save_chat_history([], st.session_state.chat_id)
            st.rerun()

# === INFO SECTION ===
st.markdown("---")
st.markdown("### 📋 Informations")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    **🎯 Fonctionnalités :**
    - Génération audio à partir de vidéo
    - Descriptions textuelles personnalisées
    - Multiples échantillons audio
    - Historique des projets
    """)

with col2:
    st.markdown("""
    **⚡ Conseils :**
    - Descriptions claires et précises
    - Vidéos courtes pour plus de rapidité
    - Testez différents styles
    - Sauvegardez vos meilleurs résultats
    """)

with col3:
    st.markdown("""
    **🔧 Modèle :**
    - HunyuanVideo-Foley (Tencent)
    - Génération audio haute qualité
    - Synchronisation vidéo-audio
    - IA de pointe pour le cinéma
    """)

st.markdown('</div>', unsafe_allow_html=True)
