import os
import tempfile
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"   # Rachel voice (best)


def text_to_speech(text):
    audio_bytes = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text
    )

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_audio.write(audio_bytes)
    temp_audio.close()

    return temp_audio.name
