import os
import wave
import struct
import numpy as np

def generate_pop(filepath):
    """Generates a quick, punchy 'pop' sound (frequency drop)."""
    sample_rate = 44100
    duration = 0.08  # 80 ms
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Frequency drops rapidly from 800Hz to 200Hz
    freqs = np.linspace(800, 200, len(t))
    # Generate the wave
    wave_data = np.sin(2 * np.pi * freqs * t)
    
    # Envelope to make it pop: sharp attack, quick decay
    envelope = np.exp(-t * 50)
    audio = wave_data * envelope
    
    # Normalize and convert to 16-bit PCM
    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)
    
    with wave.open(filepath, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for sample in audio:
            f.writeframes(struct.pack('h', sample))
    print(f"Generated {filepath}")

def generate_whoosh(filepath):
    """Generates a 'whoosh' sound (filtered white noise with envelope)."""
    sample_rate = 44100
    duration = 0.3  # 300 ms
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # White noise
    noise = np.random.normal(0, 1, len(t))
    
    # Envelope: rises quickly, falls smoothly
    envelope = np.sin(np.pi * (t / duration)) ** 2
    audio = noise * envelope
    
    # Apply a simple low-pass filter effect by smoothing
    window_size = 50
    audio = np.convolve(audio, np.ones(window_size)/window_size, mode='same')
    
    # Normalize and convert to 16-bit PCM
    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)
    
    with wave.open(filepath, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for sample in audio:
            f.writeframes(struct.pack('h', sample))
    print(f"Generated {filepath}")

if __name__ == "__main__":
    os.makedirs("sound", exist_ok=True)
    generate_pop("sound/pop.wav")
    generate_whoosh("sound/whoosh.wav")
