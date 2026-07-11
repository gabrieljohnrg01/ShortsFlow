from moviepy import *
import moviepy.video.fx as vfx
import os
import re
import random
import math
import sys
import json

def parse_srt(srt_file):
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    subs = []
    # Split content into blocks based on double newlines
    blocks = re.split(r'\n\s*\n', content.strip())
    
    def time_to_seconds(t_str):
        # format: HH:MM:SS,mmm
        match = re.match(r'(\d+):(\d+):(\d+),(\d+)', t_str)
        if not match: return 0.0
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000.0

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2: # At least index and time line
            # The first line is the index, second is time, rest is text
            time_line = lines[1]
            text_lines = lines[2:]
            
            times = time_line.strip().split(' --> ')
            if len(times) == 2:
                start_str, end_str = times
                start = time_to_seconds(start_str)
                end = time_to_seconds(end_str)
                text = "\n".join(text_lines).strip()
                subs.append((start, end, text))
    return subs

def get_scene_durations(scenes, subtitles):
    durations = []
    current_sub_idx = 0
    total_subs = len(subtitles)
    
    for i, scene in enumerate(scenes):
        narration = scene.get('narration', '')
        # Simple tokenization by space to estimate word count
        scene_words = narration.split()
        word_count = len(scene_words)
        
        if current_sub_idx >= total_subs:
            durations.append(2.0)
            continue
            
        # Target end index in subtitles
        end_sub_idx = min(current_sub_idx + word_count, total_subs) - 1
        
        # Ensure we at least advance by 1 if there's text
        if word_count > 0 and end_sub_idx < current_sub_idx:
             end_sub_idx = current_sub_idx
        
        start_time = subtitles[current_sub_idx][0]
        end_time = subtitles[end_sub_idx][1]
        
        duration = end_time - start_time
        if i < len(scenes) - 1 and end_sub_idx + 1 < total_subs:
             next_start = subtitles[end_sub_idx + 1][0]
             duration = next_start - start_time
             
        if duration < 1.0: duration = 1.0
            
        durations.append(duration)
        current_sub_idx = end_sub_idx + 1
        
    return durations

def apply_ken_burns(clip, width=1080, height=1920):
    """
    Applies a slow Pan/Zoom effect to an image clip.
    1. Resize image to be slightly larger than target (zoom_ratio).
    2. Define start and end positions for the crop window.
    3. Animate the position (Pan).
    """
    
    duration = clip.duration
    target_aspect = width / height
    
    # 1. Resize to cover the frame with some room to pan
    # We want the image to be, say, 1.2x the required size in one dimension to allow movement.
    
    zoom_ratio = 1.3
    
    # Determine if the image is portrait or landscape/square
    img_w, img_h = clip.w, clip.h
    img_aspect = img_w / img_h
    
    if img_aspect > target_aspect:
        # Image is wider (relative to target). 
        # Match height to target * zoom, and width will be wider than needed.
        new_h = int(height * zoom_ratio)
        new_w = int(img_w * (new_h / img_h))
    else:
        # Image is taller/narrower.
        # Match width to target * zoom, and height will be taller than needed.
        new_w = int(width * zoom_ratio)
        new_h = int(img_h * (new_w / img_w))
        
    clip_resized = clip.resized(width=new_w, height=new_h)
    
    # 2. Random Start/End Crop Positions
    # Available Pan/Scroll range
    max_x = max(0, new_w - width)
    max_y = max(0, new_h - height)
    
    # Define corners/edges/centers
    positions = [
        ('left', 'top'), ('center', 'top'), ('right', 'top'),
        ('left', 'center'), ('center', 'center'), ('right', 'center'),
        ('left', 'bottom'), ('center', 'bottom'), ('right', 'bottom')
    ]
    
    start_pos_name = random.choice(positions)
    # Pick end position different from start to ensure movement
    possible_ends = [p for p in positions if p != start_pos_name]
    end_pos_name = random.choice(possible_ends)
    
    def get_coords(name, max_x, max_y):
        x, y = 0, 0
        if name[0] == 'left': x = 0
        elif name[0] == 'center': x = max_x / 2
        elif name[0] == 'right': x = max_x
        
        if name[1] == 'top': y = 0
        elif name[1] == 'center': y = max_y / 2
        elif name[1] == 'bottom': y = max_y
        return int(x), int(y)

    x1, y1 = get_coords(start_pos_name, max_x, max_y)
    x2, y2 = get_coords(end_pos_name, max_x, max_y)
    
    # 3. Animate Crop
    # scroll function: returns (x, y) for top-left of crop at time t
    # 3. Animate Crop using a custom filter (fl) because v2.0 'cropped' might not accept functions for x1/y1 directly in all contexts
    # or the error suggests it's trying to add a function to an int.
    
    # We will use a custom transformer. 
    # Logic: The image is already resized to be larger (clip_resized).
    # We want to extract a 1080x1920 frame from it at shifting coordinates.
    
    def crop_filter(get_frame, t):
        # Calculate current top-left coordinates
        progress = t / clip.duration
        current_x = int(x1 + (x2 - x1) * progress)
        current_y = int(y1 + (y2 - y1) * progress)
        
        # Get the full frame
        frame = get_frame(t)
        
        # Crop: frame[y:y+h, x:x+w]
        # Ensure we don't go out of bounds
        cy1 = max(0, current_y)
        cy2 = min(frame.shape[0], current_y + height)
        cx1 = max(0, current_x)
        cx2 = min(frame.shape[1], current_x + width)
        
        return frame[cy1:cy2, cx1:cx2]

    # Apply the filter
    # In MoviePy 2.1.2, use .transform() instead of .fl() if .fl() is missing
    # .transform(func, apply_to=...) works similar to fl
    final_clip = clip_resized.transform(crop_filter, apply_to=['mask'])
    
    # Ensure the size is correct (in case of slight off-by-one errors in rounding)
    final_clip = final_clip.with_effects([vfx.Resize(new_size=(width, height))])
                                      
    return final_clip

def render_final_video(output_dir):
    print("🎬 Rendering Final Edit with Ken Burns...")
    
    try:
        audio_path = os.path.join(output_dir, "audio.mp3")
        subs_path = os.path.join(output_dir, "subtitles.srt")
        
        if not os.path.exists(audio_path) or not os.path.exists(subs_path):
             print(f"❌ Audio or Subtitles missing in {output_dir}!")
             return
        
        # Determine Audio Duration
        # We need to temporarily load audio to know total duration? 
        # Actually AudioFileClip is fast.
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        
        # Add Background Music
        bg_music_path = os.path.join("sound", "bg_music.mp3")
        if os.path.exists(bg_music_path):
            print(f"🎵 Adding background music from {bg_music_path}...")
            bg_music = AudioFileClip(bg_music_path)
            if bg_music.duration > audio.duration:
                bg_music = bg_music.subclipped(0, audio.duration)
            # Volume
            bg_music = bg_music.with_volume_scaled(0.05)
            # Composite
            audio_clips = [audio, bg_music]
        else:
            audio_clips = [audio]

        # Load SFX
        pop_path = "sound/pop.wav"
        whoosh_path = "sound/whoosh.wav"
        has_pop = os.path.exists(pop_path)
        has_whoosh = os.path.exists(whoosh_path)

        # Load Scenes
        visual_plan_path = os.path.join(output_dir, "visual_plan.json")
        scenes = []
        if os.path.exists(visual_plan_path):
             with open(visual_plan_path, 'r', encoding='utf-8') as f:
                 scenes = json.load(f)
                 
        subtitles = parse_srt(subs_path)
        
        if scenes and subtitles:
            print("🎬 Using Director Mode: Syncing visuals to narration scripts...")
            scene_durations = get_scene_durations(scenes, subtitles)
        else:
            scene_durations = []

        asset_files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) 
                              if f.startswith("asset_") and (f.endswith(".jpg") or f.endswith(".png") or f.endswith(".jpeg") or f.endswith(".mp4"))], 
                              key=lambda x: int(re.search(r'asset_(\d+)', x).group(1)))
        
        if not asset_files:
            print(f"❌ No assets found in {output_dir}!")
            return
            
        clips = []
        
        # Helper function for pop effect
        def pop_effect(clip):
            # Scale from 0.8 to 1.1 then back to 1.0
            def resize_func(t):
                if t < 0.05:
                    return 0.8 + 6 * t # t=0 -> 0.8, t=0.05 -> 1.1
                elif t < 0.1:
                    return 1.1 - 2 * (t - 0.05) # t=0.05 -> 1.1, t=0.1 -> 1.0
                return 1.0
            # Moviepy vfx.resize takes a function
            return clip.fx(vfx.resize, resize_func)
        
        for i, asset_path in enumerate(asset_files):
            # Duration
            if i < len(scene_durations):
                clip_duration = scene_durations[i]
            else:
                remaining_duration = total_duration - sum(scene_durations)
                remaining_assets = len(asset_files) - len(scene_durations)
                clip_duration = max(1.0, remaining_duration / max(1, remaining_assets))
            
            print(f"  - Asset {i}: {clip_duration:.2f}s")

            if asset_path.endswith('.mp4'):
                # Handle Video Asset
                vid_clip = VideoFileClip(asset_path)
                # Ensure it has no audio
                vid_clip = vid_clip.without_audio()
                # Loop if video is shorter than needed duration
                if vid_clip.duration < clip_duration:
                     vid_clip = vid_clip.with_effects([vfx.Loop(duration=clip_duration)])
                else:
                     vid_clip = vid_clip.subclipped(0, clip_duration)
                     
                # Apply Ken Burns to video clips as well for constant momentum
                vid_clip = apply_ken_burns(vid_clip, width=1080, height=1920)
                clips.append(vid_clip)
            else:
                # Handle Image Asset (Fallback)
                img_clip = ImageClip(asset_path).with_duration(clip_duration)
                kb_clip = apply_ken_burns(img_clip, width=1080, height=1920)
                clips.append(kb_clip)
        
        # Concatenate
        base_video = concatenate_videoclips(clips, method="compose")
        
        # Add flash transitions and whoosh SFX
        flashes = []
        current_time = 0.0
        for i, dur in enumerate(scene_durations):
            current_time += dur
            if i < len(scene_durations) - 1:
                # Add white flash at transition
                flash = ColorClip(size=(1080, 1920), color=(255, 255, 255)).with_duration(0.15)
                flash = flash.with_opacity(0.8).with_start(current_time)
                flashes.append(flash)
                
                if has_whoosh:
                    # Create a new instance to avoid shared file reader state corruption
                    w_sfx = AudioFileClip(whoosh_path).with_volume_scaled(0.4).with_start(current_time)
                    audio_clips.append(w_sfx)
        
        # Check if video is shorter than audio, extend last frame? or trim audio?
        # Usually we sync audio to video or vice versa. 
        # If video is shorter (due to rounding), we should probably loop last frame or fade out audio.
        # But we calculated durations based on audio, so it should be close.
        
        if base_video.duration < audio.duration:
             # Extend last clip? Or just let audio cutoff
             pass
             
        # Set Audio
        final_audio = CompositeAudioClip(audio_clips)
        base_video = base_video.with_audio(final_audio)
        
        # Truncate to audio duration
        base_video = base_video.with_duration(audio.duration)

        print("📝 Generating Subtitle Overlays (Hormozi Style)...")
        text_clips = []
        STOP_WORDS = {"THE", "AND", "IS", "TO", "IN", "OF", "A", "IT", "THAT", "FOR", "ON", "WITH", "AS", "AT", "BY", "OR", "IF"}
        COLORS = ['yellow', '#00FF00', '#FF3333', '#00FFFF'] # High energy colors
        color_idx = 0
        
        for start, end, text in subtitles:
            word = text.upper().strip()
            
            if word not in STOP_WORDS and len(word) > 2:
                text_color = COLORS[color_idx % len(COLORS)]
                color_idx += 1
            else:
                text_color = 'white'
            
            display_text = word
            
            # Subtitle styling with large stroke to ensure it pops
            txt_clip = (TextClip(text=display_text, font_size=95, color=text_color, font='C:/Windows/Fonts/impact.ttf', 
                                 stroke_color='black', stroke_width=8, method='caption', size=(900, 300))
                        .with_position(('center', 1000)) # slightly higher
                        .with_start(start)
                        .with_end(end))
            
            if has_pop and text_color != 'white':
                # Create a new instance to avoid shared file reader state corruption
                p_sfx = AudioFileClip(pop_path).with_volume_scaled(0.6).with_start(start)
                audio_clips.append(p_sfx)
            
            # Apply pop effect and slight rotational shake
            try:
                # Shake rotation randomly
                shake = random.choice([-3, -2, 2, 3])
                txt_clip = txt_clip.rotated(shake)
                # MoviePy 2.x vfx resize
                txt_clip = txt_clip.resized(lambda t: 1 + 0.15 * math.sin(t * 15) if t < 0.2 else 1)
            except:
                pass
                
            text_clips.append(txt_clip)
            
        final_audio = CompositeAudioClip(audio_clips)
        base_video = base_video.with_audio(final_audio)
            
        final_video = CompositeVideoClip([base_video] + flashes + text_clips)
        
        final_video_path = os.path.join(output_dir, "final_short.mp4")
        # Ensure fast rendering
        final_video.write_videofile(final_video_path, fps=30, codec="libx264", audio_codec="aac", threads=8, preset='ultrafast')
        print(f"🚀 SUCCESS! Video saved as '{final_video_path}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        render_final_video(sys.argv[1])
    else:
        # Try to find latest asset folder
        assets_dir = "assets"
        if os.path.exists(assets_dir):
            subdirs = [os.path.join(assets_dir, d) for d in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, d))]
            if subdirs:
                latest_dir = max(subdirs, key=os.path.getmtime)
                print(f"⚠️ No output directory specified. Using latest: {latest_dir}")
                render_final_video(latest_dir)
            else:
                print("Usage: python editor.py <output_dir>")
        else:
            print("Usage: python editor.py <output_dir>")
