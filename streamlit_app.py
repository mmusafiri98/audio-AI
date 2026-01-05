import streamlit as st
import tempfile
import os
from pathlib import Path
from gradio_client import Client, handle_file
import moviepy.editor as mp
from datetime import timedelta

# =========================
# CONFIGURAZIONE PAGINA
# =========================
st.set_page_config(
    page_title="Music Video Lyrics Generator",
    page_icon="🎵",
    layout="wide"
)

# =========================
# SESSION STATE
# =========================
if 'processed_video' not in st.session_state:
    st.session_state.processed_video = None

if 'lyrics_data' not in st.session_state:
    st.session_state.lyrics_data = None

if 'output_format' not in st.session_state:
    st.session_state.output_format = "mp4"

# =========================
# FUNZIONI
# =========================
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
    """Timing approssimativo parole"""
    words = lyrics_text.split()
    if not words:
        return []

    time_per_word = audio_duration / len(words)
    timings = []
    current_time = 0.0

    for word in words:
        timings.append({
            "word": word.strip(),
            "start": current_time,
            "end": current_time + time_per_word
        })
        current_time += time_per_word

    return timings


def create_subtitle_clip(text, start, end, video_size):
    """Crea sottotitolo stile Suno"""
    from moviepy.video.VideoClip import TextClip

    try:
        clip = TextClip(
            text,
            fontsize=70,
            color="white",
            font="Arial-Bold",
            stroke_color="black",
            stroke_width=3,
            method="caption",
            size=(int(video_size[0] * 0.8), None),
            align="center"
        )
    except:
        clip = TextClip(
            text,
            fontsize=70,
            color="white",
            stroke_color="black",
            stroke_width=3,
            method="caption",
            size=(int(video_size[0] * 0.8), None),
            align="center"
        )

    return (
        clip
        .set_position(("center", int(video_size[1] * 0.85)))
        .set_start(start)
        .set_duration(end - start)
    )


def add_lyrics_to_video(video_path, word_timings, output_path, words_per_line):
    """Genera video finale con lyrics"""
    video = mp.VideoFileClip(video_path)
    subtitle_clips = []
    current_line = []

    for i, word in enumerate(word_timings):
        current_line.append(word)

        if len(current_line) == words_per_line or i == len(word_timings) - 1:
            text = " ".join(w["word"] for w in current_line)
            start = current_line[0]["start"]
            end = current_line[-1]["end"]

            subtitle_clips.append(
                create_subtitle_clip(text, start, end, video.size)
            )
            current_line = []

    final_video = mp.CompositeVideoClip([video] + subtitle_clips)

    ext = Path(output_path).suffix.lower()

    if ext == ".webm":
        codec = "libvpx-vp9"
        audio_codec = "libopus"
    else:
        codec = "libx264"
        audio_codec = "aac"

    final_video.write_videofile(
        output_path,
        codec=codec,
        audio_codec=audio_codec,
        fps=video.fps,
        logger=None
    )

    video.close()
    final_video.close()
    return output_path


def create_srt_file(word_timings, output_path, words_per_line):
    """Genera file SRT"""
    with open(output_path, "w", encoding="utf-8") as f:
        index = 1
        line = []

        for i, word in enumerate(word_timings):
            line.append(word)

            if len(line) == words_per_line or i == len(word_timings) - 1:
                text = " ".join(w["word"] for w in line)
                start = timedelta(seconds=line[0]["start"])
                end = timedelta(seconds=line[-1]["end"])

                start_str = str(start).split(".")[0] + ",000"
                end_str = str(end).split(".")[0] + ",000"

                f.write(f"{index}\n{start_str} --> {end_str}\n{text}\n\n")
                index += 1
                line = []

# =========================
# UI
# =========================
st.title("🎵 Music Video Lyrics Generator")
st.markdown("### Video musicali con lyrics sincronizzati (MP4 / WebM VLC)")

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("⚙️ Configurazioni")

    words_per_line = st.slider("Parole per riga", 2, 8, 4)

    st.session_state.output_format = st.selectbox(
        "Formato output",
        ["mp4", "webm"],
        help="WEBM consigliato per VLC"
    )

    st.info("💡 Audio chiaro = risultati migliori")

# =========================
# LAYOUT
# =========================
col1, col2 = st.columns(2)

# ---------- UPLOAD ----------
with col1:
    st.header("📤 Upload Video")

    uploaded_file = st.file_uploader(
        "Carica video",
        type=["mp4", "mov", "avi", "mkv", "webm"]
    )

    if uploaded_file:
        suffix = Path(uploaded_file.name).suffix
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_input.write(uploaded_file.read())
        temp_input.close()

        st.video(temp_input.name)

        if st.button("🎬 Genera Video con Lyrics", type="primary", use_container_width=True):
            progress = st.progress(0)

            audio_path, video_clip = extract_audio_from_video(temp_input.name)
            progress.progress(25)

            lyrics = get_lyrics_from_audio(audio_path)
            if not lyrics:
                st.stop()

            st.session_state.lyrics_data = lyrics
            progress.progress(50)

            timings = get_word_timestamps_from_lyrics(lyrics, video_clip.duration)
            progress.progress(75)

            output_suffix = f".{st.session_state.output_format}"
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=output_suffix).name

            final_video = add_lyrics_to_video(
                temp_input.name,
                timings,
                output_path,
                words_per_line
            )

            st.session_state.processed_video = final_video
            progress.progress(100)
            st.success("✅ Video completato!")
            st.balloons()

            try:
                os.unlink(audio_path)
            except:
                pass

# ---------- OUTPUT ----------
with col2:
    st.header("🎥 Risultato")

    if st.session_state.processed_video:
        st.video(st.session_state.processed_video)

        with open(st.session_state.processed_video, "rb") as f:
            st.download_button(
                "📥 Scarica Video",
                f,
                file_name=f"video_with_lyrics.{st.session_state.output_format}",
                mime=f"video/{st.session_state.output_format}",
                use_container_width=True
            )

        srt_path = tempfile.NamedTemporaryFile(delete=False, suffix=".srt").name
        create_srt_file(timings, srt_path, words_per_line)

        with open(srt_path, "rb") as f:
            st.download_button(
                "📝 Scarica SRT",
                f,
                file_name="subtitles.srt",
                mime="text/plain",
                use_container_width=True
            )

    if st.session_state.lyrics_data:
        with st.expander("📝 Lyrics Generati", expanded=True):
            st.text_area(
                "Testo",
                st.session_state.lyrics_data,
                height=300,
                disabled=True
            )

# =========================
# FOOTER
# =========================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:gray;font-size:12px'>"
    "🎵 Powered by Gradio + MoviePy • MP4 / WebM VLC Ready"
    "</div>",
    unsafe_allow_html=True
)
