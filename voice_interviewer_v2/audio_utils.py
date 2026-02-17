import numpy as np
import wave
import io


def wav_bytes_to_array(wav_bytes):
    """Convert wav bytes to numpy array"""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)
        return audio, wf.getframerate()


def calculate_rms(audio_array):
    """RMS energy for volume"""
    if len(audio_array) == 0:
        return 0
    return np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))


def silence_detected(wav_bytes, silence_seconds=4, threshold=500):
    """
    Detect if last N seconds are silent.
    threshold: lower means more sensitive
    """
    audio, rate = wav_bytes_to_array(wav_bytes)

    chunk_size = int(rate * silence_seconds)
    if len(audio) < chunk_size:
        return False

    last_chunk = audio[-chunk_size:]
    rms = calculate_rms(last_chunk)

    return rms < threshold, rms
