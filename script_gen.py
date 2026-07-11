from google import genai
from google.genai import types
from config import GEMINI_KEY
import time
import json
import os
import requests

def generate_script(topic, output_dir):
    client = genai.Client(api_key=GEMINI_KEY)
    
    print(f"📝 Generating script for: {topic}...")
    
    # Load history
    history_file = "generated_history.json"
    past_titles = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                # Get last 20 titles to avoid
                past_titles = [entry.get("title", "") for entry in history_data[-20:]]
        except Exception:
            past_titles = []

    avoid_instruction = ""
    if past_titles:
        avoid_instruction = f"\n    IMPORTANT: You have already written scripts about the following titles. DO NOT repeat these exact stories or angles. Find a NEW, UNIQUE angle or fact:\n    " + "\n    ".join([f"- {t}" for t in past_titles])

    print(f"🔍 Searching Wikipedia for verified facts about: {topic}...")
    scraped_facts = ""
    try:
        # Use Wikipedia API to grab the factual summary
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        response = requests.get(wiki_url, timeout=5)
        if response.status_code == 200:
            scraped_facts = f"- {response.json().get('extract', '')}\n"
        else:
            # Try a broader search if the exact page doesn't exist
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={topic}&limit=1&namespace=0&format=json"
            search_res = requests.get(search_url, timeout=5).json()
            if len(search_res) > 1 and len(search_res[1]) > 0:
                best_match = search_res[1][0]
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{best_match.replace(' ', '_')}"
                scraped_facts = f"- {requests.get(wiki_url, timeout=5).json().get('extract', '')}\n"
    except Exception as e:
        print(f"⚠️ Web scraping failed: {e}. Falling back to internal knowledge.")

    prompt = f"""
    You are a professional Video Director for YouTube Shorts AND a verified historian. 
    Topic: {topic}
    {avoid_instruction}
    
    VERIFIED FACTS TO USE:
    {scraped_facts}
    
    CRITICAL FACT CHECKING RULE: You MUST base your script's core claims heavily on the "VERIFIED FACTS TO USE" above. Do not invent or hallucinate historical/scientific information. If the verified facts are empty, rely purely on strictly accurate established knowledge.
    
    Create a highly engaging, viral 30-second Short.
    
    CRITICAL: The VERY FIRST sentence must be an aggressive, high-energy "Hook" designed to stop a viewer from scrolling immediately (e.g., "STOP scrolling! Did you know...", "This car secret will blow your mind...", "You've been lied to about...").
    
    Output strictly VALID JSON in this format:
    {{
        "title": "Impactful Title (Max 60 chars)",
        "description": "Engaging description with CTA",
        "tags": ["tag1", "tag2"],
        "image_search_term": "The MAIN physical subject (e.g. 'Nissan GT-R R34', 'Eiffel Tower', 'Tiger'). Avoid abstract concepts.",
        "scenes": [
            {{
                "narration": "First sentence of the hook...",
                "visual_query": "Specific, high-quality photograph description (e.g. 'close up of cybernetic eye, highly detailed, 8k')",
                "media_type": "image"
            }},
            {{
                "narration": "Next part of the story...",
                "visual_query": "Visual matching this exact moment",
                "media_type": "image"
            }}
        ]
    }}
    
    Rules:
    1. Total narration length must be STRICTLY between 20 and 30 seconds. Do not exceed 30 seconds.
    2. "visual_query": Be EXTREMELY specific and descriptive. Design for Google Image Search. 
            - Use adjectives like "detailed", "cinematic", "historic photo", "diagram".
            - Avoid generic terms like "footage of". Instead, describe the IMAGE content.
            - **CRITICAL: Ensure the visual description implies a VERTICAL (9:16) composition.** Use terms like "portrait shot", "tall vertical cropping", "vertical wallpaper style".
            - Ensure the visual is finding a REAL entity mentioned in the narration (e.g. if talking about 'Model T', search for 'Ford Model T 1908 black factory').
    3. "media_type": STRICTLY USE "image" ONLY. Do NOT use "video".
    4. Ensure smooth flow between scenes.
    """
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Using Gemini 2.5 Flash for high speed and generous API quotas
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            script_data = json.loads(response.text)
            
            # Reconstruct full script from scenes
            full_script = " ".join([s["narration"] for s in script_data["scenes"]])
            
            # Save script
            script_path = os.path.join(output_dir, "script.txt")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(full_script)
            print(f"✅ Script saved to {script_path}")
            
            # Save visual plan (The entire scenes list)
            visual_plan_path = os.path.join(output_dir, "visual_plan.json")
            with open(visual_plan_path, "w", encoding="utf-8") as f:
                json.dump(script_data["scenes"], f, indent=4)
            print(f"✅ Visual plan saved to {visual_plan_path}")

            # Save Metadata
            metadata = {
                "title": script_data.get("title", f"Short about {topic}"),
                "description": script_data.get("description", "Interesting facts about cars! #shorts"),
                "tags": script_data.get("tags", ["shorts", "cars", "history"]),
                "topic": topic,
                "image_search_term": script_data.get("image_search_term", topic)
            }
            metadata_path = os.path.join(output_dir, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            print(f"✅ Metadata saved to {metadata_path}")
            
            # Append to history
            new_entry = {
                "timestamp": time.time(),
                "topic": topic,
                "title": metadata["title"],
                "script_snippet": full_script[:50]
            }
            
            current_history = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        current_history = json.load(f)
                except:
                    current_history = []
            
            current_history.append(new_entry)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(current_history, f, indent=4)
                
            return full_script
            
        except Exception as e:
            # Check for generic 429 or quota issues in the exception message
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = (2 ** attempt) * 10 
                print(f"⚠️ Quota exceeded. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                print(f"❌ Error generating script: {e}")
                break
            
    print("❌ Failed to generate script after multiple retries.")
    return None

if __name__ == "__main__":
    import sys
    if not os.path.exists("test_output"):
        os.makedirs("test_output")

    if len(sys.argv) > 1:
        generate_script(sys.argv[1], "test_output")
    else:
        generate_script("Nissan GTR R34", "test_output")
