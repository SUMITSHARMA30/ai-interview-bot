import tempfile
import streamlit as st

# fallback engine
from gtts import gTTS

# ElevenLabs (optional)
try:
    from elevenlabs.client import ElevenLabs
    ELEVEN_AVAILABLE = True
except:
    ELEVEN_AVAILABLE = False


VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel


def text_to_speech(text):
    # ---------------- TRY ELEVENLABS ----------------
    if ELEVEN_AVAILABLE:
        try:
            client = ElevenLabs(api_key=st.secrets["ELEVENLABS_API_KEY"])

            audio_stream = client.text_to_speech.convert(
                voice_id=VOICE_ID,
                model_id="eleven_multilingual_v2",
                text=text
            )

            audio_bytes = b"".join(audio_stream)

            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_audio.write(audio_bytes)
            temp_audio.close()

            return temp_audio.name

        except Exception as e:
            print("ElevenLabs failed, switching to gTTS:", e)

    # ---------------- FALLBACK GTTS ----------------
    tts = gTTS(text=text, lang="en")

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_audio.name)

    return temp_audio.name
