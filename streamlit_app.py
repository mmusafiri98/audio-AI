import streamlit as st
import tempfile
import os
from pathlib import Path
from gradio_client import Client, handle_file
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
import whisper
import json
from datetime import timedelta

# Configurazione pagina
st.set_page_config(
    page_title="Music Video Lyrics Generator",
    page_icon="🎵",
    layout="wide"
)

# Inizializza sessione
if 'processed_video' not in st.session_state:
    st.session_state.processed_video = None
if 'lyrics_data' not in st.session_state:
    st.session_state.lyrics_data = None

# Funzioni core
@st.cache_resource
def load_whisper_model():
    """Carica il modello Whisper per il timing delle parole"""
    return whisper.load_model("base")

def extract_audio_from_video(video_path):
    """Estrae l'audio dal video"""
    with st.spinner("Estrazione audio dal video..."):
        video = mp.VideoFileClip(video_path)
        audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        video.audio.write_audiofile(audio_path, logger=None)
        return audio_path, video

def get_lyrics_from_audio(audio_path):
    """Ottiene i lyrics usando Gradio API"""
    with st.spinner("Generazione lyrics dall'audio..."):
        try:
            client = Client("fffiloni/Music-To-Lyrics")
            result = client.predict(
                audio_input=handle_file(audio_path),
                api_name="/infer"
            )
            return result
        except Exception as e:
            st.error(f"Errore nell'estrazione lyrics: {str(e)}")
            return None

def get_word_timestamps(audio_path):
    """Ottiene il timing preciso di ogni parola usando Whisper"""
    with st.spinner("Analisi timing delle parole..."):
        model = load_whisper_model()
        result = model.transcribe(
            audio_path, 
            word_timestamps=True,
            language="it"  # Cambia se necessario
        )
        
        word_timings = []
        for segment in result['segments']:
            if 'words' in segment:
                for word in segment['words']:
                    word_timings.append({
                        'word': word['word'].strip(),
                        'start': word['start'],
                        'end': word['end']
                    })
        
        return word_timings

def create_subtitle_clip(txt, start, end, video_size):
    """Crea un clip di sottotitolo con stile Suno AI"""
    from moviepy.video.VideoClip import TextClip
    
    return TextClip(
        txt,
        fontsize=70,
        color='white',
        font='Arial-Bold',
        stroke_color='black',
        stroke_width=3,
        method='caption',
        size=(video_size[0] * 0.8, None),
        align='center'
    ).set_position(('center', 'bottom')).set_start(start).set_duration(end - start)

def add_lyrics_to_video(video_path, word_timings, output_path):
    """Aggiunge i lyrics sincronizzati al video"""
    with st.spinner("Creazione video con lyrics..."):
        video = mp.VideoFileClip(video_path)
        
        # Crea clips di testo per ogni parola
        subtitle_clips = []
        
        # Raggruppa parole in frasi (max 3-4 parole per riga come Suno)
        words_per_line = 4
        current_line = []
        
        for i, word_data in enumerate(word_timings):
            current_line.append(word_data)
            
            # Quando raggiungiamo il numero di parole o fine frase
            if len(current_line) == words_per_line or i == len(word_timings) - 1:
                # Combina le parole
                text = ' '.join([w['word'] for w in current_line])
                start_time = current_line[0]['start']
                end_time = current_line[-1]['end']
                
                # Crea subtitle clip
                subtitle_clip = create_subtitle_clip(
                    text,
                    start_time,
                    end_time,
                    video.size
                )
                subtitle_clips.append(subtitle_clip)
                current_line = []
        
        # Combina video con sottotitoli
        final_video = mp.CompositeVideoClip([video] + subtitle_clips)
        
        # Esporta
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=tempfile.NamedTemporaryFile(delete=False, suffix=".m4a").name,
            remove_temp=True,
            logger=None
        )
        
        video.close()
        final_video.close()
        
        return output_path

def create_srt_file(word_timings, output_path):
    """Crea un file SRT per i sottotitoli"""
    with open(output_path, 'w', encoding='utf-8') as f:
        words_per_line = 4
        current_line = []
        subtitle_index = 1
        
        for i, word_data in enumerate(word_timings):
            current_line.append(word_data)
            
            if len(current_line) == words_per_line or i == len(word_timings) - 1:
                text = ' '.join([w['word'] for w in current_line])
                start_time = timedelta(seconds=current_line[0]['start'])
                end_time = timedelta(seconds=current_line[-1]['end'])
                
                # Formato SRT
                f.write(f"{subtitle_index}\n")
                f.write(f"{str(start_time).replace('.', ',')} --> {str(end_time).replace('.', ',')}\n")
                f.write(f"{text}\n\n")
                
                subtitle_index += 1
                current_line = []

# UI Principale
st.title("🎵 Music Video Lyrics Generator")
st.markdown("### Genera video musicali con lyrics sincronizzati come Suno AI")

# Sidebar configurazione
with st.sidebar:
    st.header("⚙️ Configurazioni")
    
    language = st.selectbox(
        "Lingua dell'audio",
        ["it", "en", "fr", "es", "de"],
        index=0
    )
    
    words_per_line = st.slider(
        "Parole per riga",
        min_value=2,
        max_value=6,
        value=4
    )
    
    font_size = st.slider(
        "Dimensione testo",
        min_value=40,
        max_value=100,
        value=70
    )
    
    st.markdown("---")
    st.markdown("### 📖 Come funziona")
    st.markdown("""
    1. Carica un video
    2. L'AI estrae i lyrics
    3. Sincronizza parole con timing
    4. Genera video finale
    """)

# Layout principale
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload Video")
    
    uploaded_file = st.file_uploader(
        "Carica il tuo video musicale",
        type=['mp4', 'mov', 'avi', 'mkv'],
        help="Formati supportati: MP4, MOV, AVI, MKV"
    )
    
    if uploaded_file:
        # Salva file temporaneo
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_input.write(uploaded_file.read())
        temp_input.close()
        
        st.video(temp_input.name)
        
        # Pulsante processo
        if st.button("🎬 Genera Video con Lyrics", type="primary", use_container_width=True):
            try:
                # Step 1: Estrai audio
                audio_path, video_clip = extract_audio_from_video(temp_input.name)
                st.success("✅ Audio estratto")
                
                # Step 2: Ottieni lyrics
                lyrics_result = get_lyrics_from_audio(audio_path)
                if lyrics_result:
                    st.success("✅ Lyrics generati")
                    st.session_state.lyrics_data = lyrics_result
                
                # Step 3: Ottieni timing parole
                word_timings = get_word_timestamps(audio_path)
                st.success(f"✅ Timing analizzato ({len(word_timings)} parole)")
                
                # Step 4: Crea video finale
                output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                final_video = add_lyrics_to_video(
                    temp_input.name,
                    word_timings,
                    output_path
                )
                
                st.session_state.processed_video = output_path
                st.success("✅ Video generato con successo!")
                
                # Cleanup
                os.unlink(audio_path)
                
            except Exception as e:
                st.error(f"❌ Errore durante il processo: {str(e)}")
                st.exception(e)

with col2:
    st.header("🎥 Risultato")
    
    if st.session_state.processed_video:
        st.video(st.session_state.processed_video)
        
        # Download buttons
        col_a, col_b = st.columns(2)
        
        with col_a:
            with open(st.session_state.processed_video, 'rb') as f:
                st.download_button(
                    label="📥 Scarica Video",
                    data=f,
                    file_name="video_with_lyrics.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
        
        with col_b:
            # Genera e scarica SRT
            if st.button("📝 Scarica Sottotitoli (SRT)", use_container_width=True):
                srt_path = tempfile.NamedTemporaryFile(delete=False, suffix=".srt").name
                # Ricarica word timings per SRT
                audio_path, _ = extract_audio_from_video(st.session_state.processed_video)
                word_timings = get_word_timestamps(audio_path)
                create_srt_file(word_timings, srt_path)
                
                with open(srt_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download SRT",
                        data=f,
                        file_name="subtitles.srt",
                        mime="text/plain",
                        use_container_width=True
                    )
    
    else:
        st.info("👈 Carica un video per iniziare")
    
    # Mostra lyrics se disponibili
    if st.session_state.lyrics_data:
        with st.expander("📝 Lyrics Generati"):
            st.text_area(
                "Testo della canzone",
                value=st.session_state.lyrics_data,
                height=300
            )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Powered by Whisper AI + MoviePy + Gradio</p>
    </div>
    """,
    unsafe_allow_html=True
)
