
import os
import json
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube"] 
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def get_authenticated_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"❌ Error: {CLIENT_SECRETS_FILE} not found.")
                print("👉 Please follow the setup guide in youtube_setup.md to create this file.")
                return None
                
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def upload_video(output_dir):
    youtube = get_authenticated_service()
    if not youtube:
        return

    # Paths
    video_path = os.path.join(output_dir, "final_short.mp4")
    metadata_path = os.path.join(output_dir, "metadata.json")

    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return

    # Load Metadata
    title = "New YouTube Short"
    description = "Uploaded by automation."
    tags = ["shorts"]
    
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            title = data.get("title", title)
            description = data.get("description", description)
            tags = data.get("tags", tags)

    # Truncate title if needed (Max 100 actually, prompt asked for 60)
    if len(title) > 95:
        title = title[:95] + "..."

    print(f"🚀 Uploading to YouTube...")
    print(f"   Title: {title}")
    print(f"   Tags: {tags}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22" # People & Blogs default
        },
        "status": {
            "privacyStatus": "public", 
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"   Uploading... {int(status.progress() * 100)}%")
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                print(f"⚠️ Network error {e.resp.status}, retrying...")
                import time
                time.sleep(5)
                continue
            else:
                raise
        except (OSError, ConnectionError) as e: 
             # Catch ConnectionResetError (subclass of OSError)
             print(f"⚠️ Connection error: {e}. Retrying chunk...")
             import time
             time.sleep(5)
             continue

    print(f"✅ Upload Complete!")
    video_id = response.get('id')
    print(f"   Video ID: {video_id}")
    print(f"   Link: https://youtube.com/shorts/{video_id}")
    
    # Monitor Processing Status
    print("⏳ Waiting for YouTube to process the video...")
    while True:
        try:
            request = youtube.videos().list(
                part="processingDetails",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                print("   Processing status unavailable.")
                break
                
            details = response['items'][0].get('processingDetails', {})
            status = details.get('processingStatus')
            
            if status == 'succeeded':
                print("✅ Processing Complete! Video is live.")
                break
            elif status == 'failed':
                print(f"❌ Processing Failed: {details.get('processingFailureReason')}")
                break
            elif status == 'terminated':
                print("❌ Processing Terminated.")
                break
            else:
                # 'processing' or 'queued'
                parts_processed = details.get('partsProcessed', 0)
                parts_total = details.get('partsTotal', 0)
                if parts_total > 0:
                     print(f"   Processing: {status} ({parts_processed}/{parts_total} parts)")
                else:
                     print(f"   Processing: {status}...")
                
            import time
            time.sleep(10) # Poll every 10 seconds
            
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [401, 403]:
                print(f"❌ Auth Error {e.resp.status}: {e}")
                print("   The script might need re-authentication or updated scopes.")
                break
            print(f"⚠️ HTTP Error {e.resp.status}: {e}. Retrying...")
            import time
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Error checking status: {e}. Retrying...")
            import time
            time.sleep(10)

if __name__ == "__main__":
    # Test on latest folder
    assets_dir = "assets"
    folders = [os.path.join(assets_dir, d) for d in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, d))]
    if folders:
        latest = max(folders, key=os.path.getmtime)
        upload_video(latest)
