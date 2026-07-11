import asyncio
import edge_tts
import os
import whisper_timestamped
import warnings
warnings.filterwarnings("ignore") # Suppress Whisper warnings

# Add ffmpeg to PATH for this session
import imageio_ffmpeg
import shutil

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(ffmpeg_exe)
ffmpeg_std_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")

if os.path.exists(ffmpeg_dir):
    # Check if standard ffmpeg.exe exists, if not, copy the versioned one
    if not os.path.exists(ffmpeg_std_exe):
        try:
            print(f"⚠️ 'ffmpeg.exe' not found. Copying {os.path.basename(ffmpeg_exe)} to 'ffmpeg.exe'...")
            shutil.copy(ffmpeg_exe, ffmpeg_std_exe)
            print("✅ Copied successfully.")
        except Exception as e:
            print(f"❌ Failed to copy ffmpeg: {e}")

    os.environ["PATH"] += os.pathsep + ffmpeg_dir

def align_audio_with_whisper(audio_path):
    print(f"🤖 Aligning audio with Whisper Timestamped...")
    
    try:
        audio = whisper_timestamped.load_audio(audio_path)
        model = whisper_timestamped.load_model("tiny", device="cpu")
        
        result = whisper_timestamped.transcribe(model, audio, language="en")
        
        srt_parts = []
        counter = 1
        
        for segment in result['segments']:
            for word in segment['words']:
                start = word['start']
                end = word['end']
                text = word['text']
                
                # Format timestamps
                def fmt(t):
                    h = int(t // 3600)
                    m = int((t % 3600) // 60)
                    s = int(t % 60)
                    ms = int((t - int(t)) * 1000)
                    return f"{h:02}:{m:02}:{s:02},{ms:03}"
                
                srt_parts.append(f"{counter}\n{fmt(start)} --> {fmt(end)}\n{text}\n")
                counter += 1
                
        return "\n".join(srt_parts)
            
    except Exception as e:
        print(f"❌ Whisper alignment error: {e}")
        return None

async def generate_voice(output_dir):
    print("🎙️ Generating Voiceover...")
    
    # Import config here
    try:
        from config import RESEMBLE_API_KEY, RESEMBLE_PROJECT_UUID, RESEMBLE_VOICE_UUID
    except ImportError:
        RESEMBLE_API_KEY = None
    
    # Read the script
    script_path = os.path.join(output_dir, "script.txt")
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    # Generate Audio
    audio_path = os.path.join(output_dir, "audio.mp3")
    
    # Try Resemble API if keys are provided
    if RESEMBLE_API_KEY and RESEMBLE_API_KEY != "your-resemble-api-key":
        print("🎙️ Using Resemble AI for Voiceover...")
        try:
            from resemble import Resemble
            Resemble.api_key(RESEMBLE_API_KEY)
            
            # Remove markdown formatting for voiceover if any
            clean_text = text.replace('*', '').replace('_', '')
            
            response = Resemble.v2.clips.create_direct(
                project_uuid=RESEMBLE_PROJECT_UUID,
                voice_uuid=RESEMBLE_VOICE_UUID,
                data=clean_text,
                title='Shorts Voiceover',
                output_format='mp3',
                sample_rate=44100
            )
            
            if response['success']:
                import requests
                audio_url = response['item']['audio_src']
                audio_data = requests.get(audio_url)
                with open(audio_path, 'wb') as f:
                    f.write(audio_data.content)
                print(f"✅ Resemble Audio saved to {audio_path}")
            else:
                 print(f"❌ Resemble API Error: {response}")
                 raise Exception("Resemble API Failed")
        except Exception as e:
            print(f"⚠️ Resemble AI generation failed: {e}. Falling back to edge-tts.")
            voice = "en-US-ChristopherNeural"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(audio_path)
            print(f"✅ Edge-TTS Audio saved to {audio_path}")
    else:
        # Fallback to Edge-TTS
        print("🎙️ Using Edge-TTS (Free) for Voiceover...")
        voice = "en-US-ChristopherNeural"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_path)
        print(f"✅ Audio saved to {audio_path}")

    subs_path = os.path.join(output_dir, "subtitles.srt")
    
    # Use Whisper for alignment (Primary)
    srt_content = align_audio_with_whisper(audio_path)
    
    if not srt_content:
        print("⚠️ Whisper alignment failed. Falling back to linear estimation...")
        # Fallback: Estimate timestamps based on audio duration
        try:
             from moviepy import AudioFileClip
             if os.path.exists(audio_path):
                 audioclip = AudioFileClip(audio_path)
                 duration = audioclip.duration
                 audioclip.close()
                 
                 words = text.split()
                 word_duration = duration / len(words)
                 
                 srt_parts = []
                 for i, word in enumerate(words):
                     start = i * word_duration
                     end = (i + 1) * word_duration
                     def fmt(t):
                         h = int(t // 3600)
                         m = int((t % 3600) // 60)
                         s = int(t % 60)
                         ms = int((t - int(t)) * 1000)
                         return f"{h:02}:{m:02}:{s:02},{ms:03}"
                     srt_parts.append(f"{i+1}\n{fmt(start)} --> {fmt(end)}\n{word}\n")
                 srt_content = "\n".join(srt_parts)
        except Exception as e:
            print(f"❌ Fallback failed: {e}")

    with open(subs_path, "w", encoding="utf-8") as file:
        file.write(srt_content if srt_content else "")
        
    print(f"✅ Subtitles saved to {subs_path}")

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    asyncio.run(generate_voice(output_dir))