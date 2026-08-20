import json
import os
import asyncio
import nest_asyncio
import edge_tts
import requests
import urllib.parse
import subprocess
import random
import time
from groq import Groq
from youtube_uploader import upload_short_to_youtube


# Setup
nest_asyncio.apply()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
VOICE_ID = "en-US-ChristopherNeural"
best_model = get_best_available_model(client)
#--- Find Model
def get_best_available_model(client):
    try:
        # Fetch the live list of all active models from Groq
        available_models = client.models.list()
        
        # Extract just the ID strings 
        active_model_ids = [m.id for m in available_models.data]
        
        # Your prioritized list of models (best/most capable at the top)
        preferred_models = [
            "openai/gpt-oss-120b",  # Top choice
            "qwen/qwen3.6-27b",     # Great secondary option
            "llama3-70b-8192",      # Reliable older model
            "mixtral-8x7b-32768"    # Fast fallback
        ]
        
        # Loop through your list and pick the first one that is currently active
        for model in preferred_models:
            if model in active_model_ids:
                print(f"✅ Auto-selected AI Model: {model}")
                return model
                
        # If all preferred models are deprecated, just grab whatever the first active chat model is
        fallback_model = active_model_ids[0]
        print(f"⚠️ Preferred models missing. Auto-falling back to: {fallback_model}")
        return fallback_model
        
    except Exception as e:
        # Absolute failsafe in case of a network glitch fetching the list
        print(f"⚠️ Could not fetch model list. Defaulting to safe fallback. Error: {e}")
        return "openai/gpt-oss-120b"

# --- 0. HISTORY MANAGEMENT ---
def get_history():
    if os.path.exists("history.json"):
        with open("history.json", "r") as f:
            return json.load(f)
    return []

def save_topic(title):
    history = get_history()
    history.append(title)
    with open("history.json", "w") as f:
        json.dump(history, f, indent=4)

def is_too_similar(new_title, history):
    new_clean = new_title.lower().strip()
    for past_title in history:
        past_clean = past_title.lower().strip()
        # Checks for exact match or significant keyword overlap
        if new_clean == past_clean or new_clean in past_clean or past_clean in new_clean:
            return True
    return False

# --- 1. SCRIPT GENERATOR ---
def generate_curiosity_script():
    print("--- 1. Generating Script ---")
    history = get_history()
    history_str = ", ".join(history[-50:])
    
    system_prompt = f"""You are a viral YouTube Shorts scriptwriter. 
    IMPORTANT: Do NOT write about these topics, they have been done: {history_str}
    Output ONLY in JSON: {{"title": "...", "script": "...", "description": "...", "tags": ["tag1", "tag2"]}}"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Write a unique, fascinating short script on a new topic."}
    ]
    
    for attempt in range(5):
        response = client.chat.completions.create(
            model=best_model,
            messages=messages,
            temperature=0.9,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        
        if is_too_similar(data.get("title", ""), history):
            print(f"⚠️ Duplicate detected: {data['title']}. Retrying...")
            messages.append({"role": "assistant", "content": json.dumps(data)})
            messages.append({"role": "user", "content": "We already did this. Please provide a completely different topic."})
        else:
            print(f"✅ Unique topic approved: {data['title']}")
            return data
    return data
# --- 2. AUDIO GENERATOR ---
async def generate_audio(script_text):
    print("--- 2. Generating Audio ---")
    communicate = edge_tts.Communicate(script_text, VOICE_ID)
    await communicate.save("audio.mp3")

# --- 3. TRANSCRIPTION (Groq Whisper) ---
def transcribe_audio(audio_path, client):
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo", 
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"] 
        )
    # Return BOTH word-level and segment-level data
    return transcript.words, transcript.segments

def chunk_words(words, chunk_size=3):
    chunks, current = [], []
    for w in words:
        current.append(w)
        ends_sentence = w["word"].strip().endswith((".", "!", "?"))
        if len(current) == chunk_size or ends_sentence:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks

def format_ass_time(seconds):
    """Converts seconds to ASS time format H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int(round((seconds - int(seconds)) * 100))
    if centisecs == 100:
        secs += 1
        centisecs = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def create_ass_subtitles(chunks, output_filename="subtitles.ass"):
    # WrapStyle: 2 prevents auto line-wrapping
    # Fontsize: 58 (tuned for 720px width)
    # Outline: 3, Shadow: 0
    ass_header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,58,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,5,10,10,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for chunk in chunks:
            # Syncs exactly to the first word's start and the last word's end in the chunk
            start_time = format_ass_time(chunk[0]['start'])
            end_time = format_ass_time(chunk[-1]['end'])
            
            # Combine the words, removing leading/trailing spaces
            text = " ".join([w['word'].strip() for w in chunk])
            
            # Alignment 5 places it exactly center screen. 
            # (Change alignment to 2 for bottom-center if preferred)
            f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")

# --- 4. PROMPT & IMAGE GENERATOR (API-based) ---
def generate_storyboard(segments):
    print("--- 4. Generating Visuals ---")
    system_prompt = "Output raw JSON array of scenes. Each has 'start_time', 'end_time', and 'visual_prompt'. Prefix prompt with: 'Flat vector art, vintage parchment paper background, sepia color palette. A minimalist silhouette of an explorer...'"
    
    response = client.chat.completions.create(
        model=best_model, 
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(segments)}], 
        response_format={"type": "json_object"}
    )
    scenes = json.loads(response.choices[0].message.content)["scenes"]
    
    for i, scene in enumerate(scenes):
        prompt = urllib.parse.quote(scene["visual_prompt"])
        img_path = f"scene_{i:03d}.png"
        
        # --- Retry Logic ---
        success = False
        for attempt in range(3):
            try:
                print(f"Fetching scene {i+1} (Attempt {attempt+1})...")
                url = f"https://image.pollinations.ai/prompt/{prompt}?width=768&height=1344&nologo=true&seed={i+attempt}"
                response = requests.get(url, timeout=60) # Increased timeout to 60s
                
                if response.status_code == 200 and len(response.content) > 1000:
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    scene["image_path"] = img_path
                    success = True
                    break
                else:
                    print(f"Attempt {attempt+1} failed (Status: {response.status_code})")
            except Exception as e:
                print(f"Attempt {attempt+1} error: {e}")
            time.sleep(5) # Wait 5 seconds before retrying
        
        if not success:
            print(f"❌ Critical Failure: Could not generate scene {i+1}")
            # Fallback: create a blank 1x1 pixel image so FFmpeg doesn't crash
            with open(img_path, 'wb') as f: f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
            scene["image_path"] = img_path

    with open("storyboard.json", "w") as f: json.dump(scenes, f, indent=4)
    return scenes

# --- 4. COMPILE & SUBTITLE ---
# Create SRT File
def create_srt(segments, srt_path="subtitles.srt"):
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start = f"{int(seg['start_time']//3600):02}:{int((seg['start_time']%3600)//60):02}:{int(seg['start_time']%60):02},{int((seg['start_time']%1*1000)):03}"
            end = f"{int(seg['end_time']//3600):02}:{int((seg['end_time']%3600)//60):02}:{int(seg['end_time']%60):02},{int((seg['end_time']%1*1000)):03}"
            f.write(f"{i+1}\n{start} --> {end}\n{seg['text']}\n\n")
            
# def apply_overlays(input_video, output_video, hook_text, sub_text):
#     print("--- 4. Applying Subtitles/Hooks ---")
#     font = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    
#     # Split the hook into two lines for manual centering
#     words = hook_text.upper().split()
#     mid = len(words) // 2
#     line1 = " ".join(words[:mid])
#     line2 = " ".join(words[mid:])
    
#     # Using individual drawtext filters for compatibility with older FFmpeg versions
#     filter_complex = (
#         f"drawtext=fontfile='{font}':text='{line1}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=100:shadowx=2:shadowy=2,"
#         f"drawtext=fontfile='{font}':text='{line2}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=160:shadowx=2:shadowy=2,"
#         f"drawtext=fontfile='{font}':text='{sub_text.upper()}':fontcolor=yellow:fontsize=60:x=(w-text_w)/2:y=h-200:shadowx=2:shadowy=2"
#     )
#     subprocess.run(["ffmpeg", "-y", "-i", input_video, "-vf", filter_complex, "-c:a", "copy", output_video], check=True)

import subprocess

def compile_video(scenes, audio_path="audio.mp3", ass_path="subtitles.ass", output_path="final_video.mp4"):
    # 1. Normalize images to 720x1280 (Vertical Short aspect ratio)
    for i, scene in enumerate(scenes):
        norm = f"norm_{i:03d}.png"
        subprocess.run([
            "ffmpeg", "-y", 
            "-i", scene['image_path'], 
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280", 
            norm
        ], check=True)
        scene['image_path'] = norm
    
    # 2. Generate the FFmpeg concat playlist with timings
    with open("ffmpeg_concat.txt", "w") as f:
        for i, scene in enumerate(scenes):
            f.write(f"file '{scene['image_path']}'\n")
            dur = (scenes[i+1]["start_time"] - scene["start_time"]) if i < len(scenes) - 1 else 2.0
            f.write(f"duration {max(0.1, dur):.2f}\n")
        # Duplicating the last image line is required by FFmpeg concat filter
        f.write(f"file '{scenes[-1]['image_path']}'\n")

    # 3. Run FFmpeg: Concatenate visual scenes, mix audio, and burn in the ASS subtitles
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", "ffmpeg_concat.txt",
        "-i", audio_path,
        # Render ONLY the single dynamic 3-word ASS track (no hook, no overlapping SRT)
        "-vf", f"fps=30,ass={ass_path}", 
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ], check=True)


def run_pipeline():
    data = generate_curiosity_script()
    save_topic(data["title"])
    with open("metadata.json", "w") as f: json.dump(data, f)
    
    # 1. Generate Voice
    asyncio.run(generate_audio(data["script"]))
    
    # 2. Get both words AND sentence-level segments
    words, segments = transcribe_audio("audio.mp3", client)
    
    # 3. Create 3-word dynamic subtitles (Fast Pacing)
    chunks = chunk_words(words)
    create_ass_subtitles(chunks)
    
    # 4. Generate Storyboard using sentence-level segments (Normal Image Pacing)
    scenes = generate_storyboard(segments)
    
    # 5. Compile Video
    compile_video(scenes)
    
    # 6. Upload
    upload_short_to_youtube("final_video.mp4", "metadata.json")
    
    # Push updates
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"])
    subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"])
    subprocess.run(["git", "add", "history.json"])
    subprocess.run(["git", "commit", "-m", f"Update history: {data['title']}"])
    subprocess.run(["git", "push"])


if __name__ == "__main__":
    run_pipeline()
