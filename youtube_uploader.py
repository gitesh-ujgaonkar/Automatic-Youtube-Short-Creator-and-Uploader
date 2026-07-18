import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate_youtube():
    # GitHub Action will inject token.json as a file
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def upload_short_to_youtube(video_path="final_video.mp4", metadata_path="metadata.json"):
    # ... (Keep your existing file checks and metadata load) ...

    # CLEANUP LOGIC:
    # 1. Remove '#' from all tags (YouTube tags don't use '#')
    # 2. Remove empty strings
    # 3. Ensure no single tag exceeds 100 characters
    cleaned_tags = []
    for tag in metadata.get("tags", []):
        tag = str(tag).replace("#", "").strip()
        if tag and len(tag) < 100:
            cleaned_tags.append(tag)

    # 4. Enforce the 500-character total limit for the WHOLE list
    final_tags = []
    current_length = 0
    for tag in cleaned_tags:
        # +1 accounts for the comma
        if current_length + len(tag) + 1 <= 495:
            final_tags.append(tag)
            current_length += len(tag) + 1
        else:
            break

    # 5. Build Request
    request_body = {
        "snippet": {
            "title": title,
            "description": formatted_description,
            "tags": final_tags, # Use the cleaned, limited list
            "categoryId": "27"
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False
        }
    }
    

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    print(f"✅ Upload Successful! ID: {response['id']}")
