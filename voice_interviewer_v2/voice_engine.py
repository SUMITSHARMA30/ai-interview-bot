import asyncio
import tempfile
import edge_tts


VOICE = "en-US-GuyNeural"   # Human male interviewer voice
# VOICE = "en-US-JennyNeural"  # Human female voice


async def _speak_async(text, output_file):
    communicate = edge_tts.Communicate(text=text, voice=VOICE)
    await communicate.save(output_file)


def text_to_speech(text):
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_audio.close()

    asyncio.run(_speak_async(text, temp_audio.name))
    return temp_audio.name
