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

    # SEO Template Logic
    title = f"{metadata['title']} | Know Lien Exp 🤯 #Shorts"
    desc = f"{metadata['description']}\n\n🧠 Subscribe for daily animated documentaries, mind-blowing facts, and deep dives!\n\n#LearnOnYouTube #ScienceFacts #AnimatedDocumentary #Shorts"
    
    # Tag Compiler (Smart 500-char limit)
    master_tags = ["shorts", "youtube shorts", "ink explainer", "animated facts", "science facts", "history facts", "mystery explained", "documentary short", "learn something new", "mind blowing facts", "fun facts", "daily facts", "trivia", "educational animation", "kurzgesagt style", "infographic video", "space facts", "biology facts", "psychology facts", "weird history", "unsolved mysteries", "how things work", "why things happen", "interesting facts", "crazy facts", "science explained", "history explained", "animation story", "digital art", "vector animation", "fascinating facts", "brain facts", "human body facts", "universe mysteries", "deep dive", "fast facts", "quick facts", "smart shorts", "learning animation", "educational shorts", "science animation", "history animation", "trivia shorts", "viral facts", "top 10 facts", "did you know", "today i learned", "fact of the day", "brain teaser", "knowledge"]
    
    final_tags = []
    current_length = 0
    for tag in (metadata['tags'] + master_tags):
        clean = tag.replace("#", "").strip()
        if current_length + len(clean) + 1 < 495:
            final_tags.append(clean)
            current_length += len(clean) + 1
    
    youtube = authenticate_youtube()
    request_body = {
        "snippet": {"title": title, "description": desc, "tags": final_tags, "categoryId": "27"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    print(f"✅ Upload Successful! ID: {response['id']}")
