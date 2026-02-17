import io
import numpy as np
from pydub import AudioSegment


def audio_bytes_to_array(audio_bytes):
    """
    Convert audio bytes (webm/wav/ogg) to numpy array
    """
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    return samples, audio.frame_rate


def calculate_rms(samples):
    if len(samples) == 0:
        return 0.0
    return np.sqrt(np.mean(samples ** 2))


def silence_detected(audio_bytes, silence_seconds=4, threshold=500):
    """
    Detect silence in last N seconds of audio
    """
    try:
        samples, rate = audio_bytes_to_array(audio_bytes)

        chunk_size = int(rate * silence_seconds)
        if len(samples) < chunk_size:
            return False, 0

        last_chunk = samples[-chunk_size:]
        rms = calculate_rms(last_chunk)

        return rms < threshold, rms

    except Exception as e:
        # If anything fails, DO NOT break interview
        print("Silence detection failed:", e)
        return False, 0
