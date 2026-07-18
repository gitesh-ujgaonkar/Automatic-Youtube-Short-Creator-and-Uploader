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
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # 1. Define your safe, hardcoded tag list here
    # This ignores whatever Groq sent in the JSON for 'tags'
    safe_tags = [
    "shorts", "youtube shorts", "animated facts", "science facts", 
    "history facts", "mystery explained", "documentary short", 
    "fun facts", "daily facts", "trivia", "kurzgesagt style", 
    "space facts", "psychology facts", "weird history", 
    "crazy facts", "science explained", "history explained", 
    "digital art", "fascinating facts", "brain facts", 
    "universe mysteries", "deep dive", "fast facts", "quick facts", 
    "smart shorts", "educational shorts", "trivia shorts", 
    "viral facts", "top 10 facts", "fact of the day", 
    "brain teaser", "knowledge"
]

    print(f"DEBUG: Attempting to upload with tags: {safe_tags}")

    youtube = authenticate_youtube()
    
    # 2. Build Request with strict safe_tags
    request_body = {
        "snippet": {
            "title": f"{metadata['title']} | Know Lien Exp 🤯 #Shorts",
            "description": f"{metadata['description']}\n\n🧠 Subscribe for daily animated documentaries!",
            "tags": safe_tags, # Using our local safe list
            "categoryId": "27"
        },
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    print(f"✅ Upload Successful! ID: {response['id']}")
