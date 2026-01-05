import streamlit as st
import tempfile
import os
from pathlib import Path
from gradio_client import Client, handle_file
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
import requests
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

def get_word_timestamps_from_lyrics(lyrics_text, audio_duration):
    """
    Crea timing approssimativo delle parole basato sulla durata totale
    (Versione semplificata senza Whisper)
    """
    with st.spinner("Analisi timing delle parole..."):
        words = lyrics_text.split()
        
        if len(words) == 0:
            return []
        
        # Calcola tempo medio per parola
        time_per_word = audio_duration / len(words)
        
        word_timings = []
        current_time = 0
        
        for word in words:
            word_timings.append({
                'word': word.strip(),
                'start': current_time,
                'end': current_time + time_per_word
            })
            current_time += time_per_word
        
        return word_timings

def create_subtitle_clip(txt, start, end, video_size):
    """Crea un clip di sottotitolo con stile Suno AI"""
    from moviepy.video.VideoClip import TextClip
    
    try:
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
        ).set_position(('center', video_size[1] * 0.85)).set_start(start).set_duration(end - start)
    except:
        # Fallback senza font specifico
        return TextClip(
            txt,
            fontsize=70,
            color='white',
            stroke_color='black',
            stroke_width=3,
            method='caption',
            size=(video_size[0] * 0.8, None),
            align='center'
        ).set_position(('center', video_size[1] * 0.85)).set_start(start).set_duration(end - start)

def add_lyrics_to_video(video_path, word_timings, output_path, words_per_line=4):
    """Aggiunge i lyrics sincronizzati al video"""
    with st.spinner("Creazione video con lyrics..."):
        video = mp.VideoFileClip(video_path)
        
        # Crea clips di testo per ogni parola
        subtitle_clips = []
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
            fps=video.fps,
            logger=None
        )
        
        video.close()
        final_video.close()
        
        return output_path

def create_srt_file(word_timings, output_path, words_per_line=4):
    """Crea un file SRT per i sottotitoli"""
    with open(output_path, 'w', encoding='utf-8') as f:
        current_line = []
        subtitle_index = 1
        
        for i, word_data in enumerate(word_timings):
            current_line.append(word_data)
            
            if len(current_line) == words_per_line or i == len(word_timings) - 1:
                text = ' '.join([w['word'] for w in current_line])
                start_time = timedelta(seconds=current_line[0]['start'])
                end_time = timedelta(seconds=current_line[-1]['end'])
                
                # Formato SRT
                start_str = str(start_time).split('.')[0] + ',000'
                end_str = str(end_time).split('.')[0] + ',000'
                
                f.write(f"{subtitle_index}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{text}\n\n")
                
                subtitle_index += 1
                current_line = []

# UI Principale
st.title("🎵 Music Video Lyrics Generator")
st.markdown("### Genera video musicali con lyrics sincronizzati come Suno AI")

# Sidebar configurazione
with st.sidebar:
    st.header("⚙️ Configurazioni")
    
    words_per_line = st.slider(
        "Parole per riga",
        min_value=2,
        max_value=8,
        value=4
    )
    
    st.markdown("---")
    st.markdown("### 📖 Come funziona")
    st.markdown("""
    1. Carica un video
    2. L'AI estrae i lyrics
    3. Sincronizza parole con timing
    4. Genera video finale
    """)
    
    st.markdown("---")
    st.info("💡 **Tip:** Per risultati migliori, usa video con audio chiaro e pulito")

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
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Estrai audio
                status_text.text("⏳ Estrazione audio dal video...")
                progress_bar.progress(20)
                audio_path, video_clip = extract_audio_from_video(temp_input.name)
                audio_duration = video_clip.duration
                st.success("✅ Audio estratto")
                
                # Step 2: Ottieni lyrics
                status_text.text("⏳ Generazione lyrics dall'audio...")
                progress_bar.progress(40)
                lyrics_result = get_lyrics_from_audio(audio_path)
                
                if lyrics_result:
                    st.success("✅ Lyrics generati")
                    st.session_state.lyrics_data = lyrics_result
                    
                    # Step 3: Crea timing parole
                    status_text.text("⏳ Analisi timing delle parole...")
                    progress_bar.progress(60)
                    word_timings = get_word_timestamps_from_lyrics(lyrics_result, audio_duration)
                    st.success(f"✅ Timing analizzato ({len(word_timings)} parole)")
                    
                    # Step 4: Crea video finale
                    status_text.text("⏳ Creazione video con lyrics...")
                    progress_bar.progress(80)
                    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    final_video = add_lyrics_to_video(
                        temp_input.name,
                        word_timings,
                        output_path,
                        words_per_line
                    )
                    
                    st.session_state.processed_video = output_path
                    progress_bar.progress(100)
                    status_text.text("✅ Completato!")
                    st.success("✅ Video generato con successo!")
                    st.balloons()
                else:
                    st.error("❌ Impossibile generare lyrics dall'audio")
                
                # Cleanup
                try:
                    os.unlink(audio_path)
                except:
                    pass
                
            except Exception as e:
                st.error(f"❌ Errore durante il processo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

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
            if st.session_state.lyrics_data:
                # Genera SRT
                srt_path = tempfile.NamedTemporaryFile(delete=False, suffix=".srt").name
                
                # Ricarica word timings per SRT
                try:
                    audio_path_temp, video_temp = extract_audio_from_video(st.session_state.processed_video)
                    word_timings_temp = get_word_timestamps_from_lyrics(
                        st.session_state.lyrics_data, 
                        video_temp.duration
                    )
                    create_srt_file(word_timings_temp, srt_path, words_per_line)
                    
                    with open(srt_path, 'rb') as f:
                        st.download_button(
                            label="📝 Scarica SRT",
                            data=f,
                            file_name="subtitles.srt",
                            mime="text/plain",
                            use_container_width=True
                        )
                except:
                    pass
    
    else:
        st.info("👈 Carica un video e clicca 'Genera' per iniziare")
    
    # Mostra lyrics se disponibili
    if st.session_state.lyrics_data:
        with st.expander("📝 Lyrics Generati", expanded=True):
            st.text_area(
                "Testo della canzone",
                value=st.session_state.lyrics_data,
                height=300,
                disabled=True
            )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>🎵 Powered by Gradio AI + MoviePy</p>
        <p style='font-size: 12px; color: gray;'>Versione Lite - Timing approssimativo</p>
    </div>
    """,
    unsafe_allow_html=True
)
