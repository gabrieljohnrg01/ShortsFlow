import requests
import random
import json
import os
import time
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont

def save_image(url, filepath):
    """Saves an image from a URL or base64 string to a file."""
    try:
        if url.startswith("data:image"):
            import base64
            # Extract header and data
            try:
                header, encoded = url.split(",", 1)
                data = base64.b64decode(encoded)
                with open(filepath, "wb") as f:
                    f.write(data)
                return True
            except Exception as e:
                print(f"❌ Error decoding/saving base64 image: {e}")
                return False
        else:
            try:
                # Add a read timeout to prevent hanging on slow downloads
                response = requests.get(url, stream=True, timeout=(10, 30))
                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    from tqdm import tqdm
                    with open(filepath, 'wb') as f, tqdm(
                        desc=f"      ⬇️ Downloading",
                        total=total_size,
                        unit='iB',
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as bar:
                        for chunk in response.iter_content(1024):
                            size = f.write(chunk)
                            bar.update(size)
                    return True
                else:
                     print(f"❌ Error downloading URL {url}: Status {response.status_code}")
                     return False
            except Exception as e:
                print(f"❌ Error downloading URL {url}: {e}")
                return False
    except Exception as e:
        print(f"❌ Unexpected error in save_image/video: {e}")
        return False

def download_from_pexels(keyword, i, output_dir, api_key):
    print(f"🎥 [Pexels] [{i+1}] Searching video for: {keyword}")
    
    if not api_key or api_key == "your-pexels-api-key":
        return "❌ Pexels API key not set in config.py"

    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=15&orientation=portrait"
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"❌ Pexels API returned {response.status_code}"
        
        data = response.json()
        videos = data.get("videos", [])
        
        if not videos:
            return f"❌ No vertical videos found for {keyword}"
            
        # Shuffle to get variety
        random.shuffle(videos)
        
        for video in videos[:5]: # Try up to 5 videos
            video_files = video.get("video_files", [])
            # Find the best vertical quality (e.g. HD 1080x1920)
            hd_files = [f for f in video_files if f.get("quality") == "hd" and f.get("width", 0) <= f.get("height", 0)]
            if not hd_files:
                hd_files = [f for f in video_files if f.get("width", 0) <= f.get("height", 0)] # Any vertical
            
            if not hd_files:
                continue
                
            # Pick a file that is close to 1080x1920 but not excessively large (avoid 4K)
            # Filter out files wider than 1080 to avoid massive 4K downloads which take forever
            reasonable_files = [f for f in hd_files if f.get("width", 0) <= 1080]
            if reasonable_files:
                best_file = max(reasonable_files, key=lambda x: x.get("width", 0) * x.get("height", 0))
            else:
                # If no 1080p files, just take the smallest HD file to save time
                best_file = min(hd_files, key=lambda x: x.get("width", 0) * x.get("height", 0))
                
            video_url = best_file.get("link")
            
            print(f"      Downloading video ({best_file.get('width')}x{best_file.get('height')})... This may take a moment.")
            
            asset_path = os.path.join(output_dir, f"asset_{i}.mp4")
            
            if save_image(video_url, asset_path):
                # Basic validation
                if os.path.getsize(asset_path) > 50000:
                    return f"✅ Asset {i} (Pexels Video) downloaded."
                else:
                    try: os.remove(asset_path)
                    except: pass
                    
        return f"❌ All video download attempts failed for {keyword}"
        
    except Exception as e:
        print(f"⚠️ Error searching Pexels for {keyword}: {e}")
        return f"⚠️ Error searching Pexels for {keyword}: {e}"



def create_placeholder_image(text, filepath):
    """Creates a placeholder image with text if download fails."""
    try:
        width, height = 1080, 1920
        # Dark background with slight noise or gradient would be better, but solid color is safe
        img = Image.new('RGB', (width, height), color=(20, 20, 20)) 
        d = ImageDraw.Draw(img)
        
        # Simple text drawing
        try:
            # Try to load a generic font or use default
            # specific path for Windows usually works, or default
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
            
        # Draw text in center
        msg = "IMAGE NOT FOUND"
        # wrapper
        import textwrap
        lines = textwrap.wrap(text, width=30)
        
        # Draw "IMAGE NOT FOUND"
        d.text((width/2, height/2 - 100), msg, fill=(255, 50, 50), anchor="mm", font=font)
        
        # Draw query lines
        y = height/2
        for line in lines[:5]: # limit lines
            d.text((width/2, y), line, fill=(200, 200, 200), anchor="mm", font=font)
            y += 50
        
        img.save(filepath)
        return True
    except Exception as e:
        print(f"❌ Failed to create placeholder image: {e}")
        # Fallback to really simple file creation if PIL fails
        try:
            with open(filepath, 'wb') as f:
                f.write(b'\x00' * 1024) # Corrupt file better than nothing? No.
            # actually better to copy another asset if available, but for now specific error is better
            return False
        except:
             return False

def download_assets(output_dir):
    print(f"🎬 Reading visual plan...")
    
    # Import config here to get API key
    try:
        from config import PEXELS_API_KEY
    except ImportError:
        PEXELS_API_KEY = None
    
    json_path = os.path.join(output_dir, "visual_plan.json")
    if not os.path.exists(json_path):
        print(f"❌ visual_plan.json not found in {output_dir}! Run script_gen.py first.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    # Load metadata to get the topic, title, and image_search_term
    metadata_path = os.path.join(output_dir, "metadata.json")
    context_str = ""
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                title = metadata.get("title", "")
                topic = metadata.get("topic", "")
                image_search_term = metadata.get("image_search_term", "")
                
                # Priority: image_search_term > title > topic
                if image_search_term:
                    context_str = image_search_term
                elif title:
                    context_str = title
                else:
                    context_str = topic
                
                # Optional: Remove emojis from context to keep query clean (simple regex)
                import re
                # This regex removes characters that are likely emojis or non-standard symbols
                context_str = re.sub(r'[^\w\s,.-]', '', context_str).strip()

        except:
             pass

    print(f"⬇️ Downloading video assets for {len(scenes)} scenes (Pexels)...")
    if context_str:
        print(f"🎯 Using Search Context: '{context_str}'")

    results = []
    for i, scene in enumerate(scenes):
        keyword = scene.get("visual_query", "")
        # For video search, keep query simple
        base_query = f"{context_str} {keyword}" if context_str else keyword
        # Clean query slightly, take first 4-5 important words
        words = base_query.split()
        query = " ".join(words[:5])
        
        asset_path = os.path.join(output_dir, f"asset_{i}.mp4")
        
         # Check if already exists
        if os.path.exists(asset_path) and os.path.getsize(asset_path) > 50000:
             print(f"✅ Asset {i} already exists, skipping.")
             results.append(f"Skipped {i}")
             continue
        
        # Add delay to avoid aggressive rate limiting (Pexels allows 200 req/hour)
        time.sleep(1.0)
        
        result = download_from_pexels(query, i, output_dir, PEXELS_API_KEY)
        
        # Check if success (result starts with ✅)
        if "✅" not in result:
            print(f"⚠️ Primary search failed for asset {i}. Retrying with simplified query...")
            simplified_query = " ".join(keyword.split()[:2])
            print(f"   Retrying: {simplified_query}")
            result_retry = download_from_pexels(simplified_query, i, output_dir, PEXELS_API_KEY)
            
            if "✅" in result_retry:
                result = result_retry
                print(f"✅ Retry successful for asset {i}.")
            else:
                print(f"❌ Retry failed for asset {i}. Creating placeholder image.")
                asset_img_path = os.path.join(output_dir, f"asset_{i}.jpg")
                if create_placeholder_image(keyword, asset_img_path):
                    result = f"✅ Placeholder created for asset {i}"
                else:
                     result = f"❌ Failed to create asset {i}"

        print(result)
        results.append(result)

    print(f"✅ Asset download process completed.")

if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    download_assets(output_dir)
