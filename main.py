import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
    
import asyncio
from config import TOPIC
import script_gen
import voice_gen
import video_fetch
import editor
import uploader
import os
from datetime import datetime

import shutil

def cleanup_assets():
    assets_dir = "assets"
    if not os.path.exists(assets_dir): return
    
    # Get subdirectories with full paths
    subdirs = [os.path.join(assets_dir, d) for d in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, d))]
    
    if len(subdirs) >= 10:
        print(f"🧹 Cleanup Triggered: Found {len(subdirs)} folders. Keeping last 5...")
        
        # Sort by creation time (oldest first)
        subdirs.sort(key=os.path.getctime)
        
        # Delete all except the last 5
        folders_to_delete = subdirs[:-5]
        
        for d in folders_to_delete:
            try:
                shutil.rmtree(d)
                print(f"   Deleted {d}")
            except Exception as e:
                print(f"   Failed to delete {d}: {e}")

def main(topic=None):
    # Create Timestamped Folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_dir = os.path.join("assets", timestamp)
    
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        
    print(f"📂 Created project folder: {base_dir}")

    active_topic = topic if topic else TOPIC
    print(f"🎯 Using topic: {active_topic}")
    
    # Step 1: Script
    script_gen.generate_script(active_topic, base_dir)
    
    # Step 2 & 3: Voice & Video (Concurrent)
    async def generate_assets_concurrently():
        # Run voice generation (Async) and Video Fetch (Sync -> Thread) concurrently
        await asyncio.gather(
            voice_gen.generate_voice(base_dir),
            asyncio.to_thread(video_fetch.download_assets, base_dir)
        )

    asyncio.run(generate_assets_concurrently())
    
    # Step 4: Edit
    editor.render_final_video(base_dir)
    
    # Step 5: Upload
    print("📺 Starting YouTube Upload...")
    uploader.upload_video(base_dir)
    
    # Step 6: Cleanup
    cleanup_assets()

if __name__ == "__main__":
    main()
