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

# --- 1. SCRIPT GENERATOR ---
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

def generate_curiosity_script():
    print("--- 1. Generating Script ---")
    history = get_history()
    history_str = ", ".join(history[-50:]) # Send last 50 topics to avoid boredom
    
    system_prompt = f"""You are a viral YouTube Shorts scriptwriter.
    TASK: Write a 60-second documentary script.
    RULES: 140-160 words, curiosity hook.
    IMPORTANT: Do NOT write about these topics, they have been done already: {history_str}
    Output ONLY in JSON: {{"title": "...", "script": "...", "description": "...", "tags": ["tag1", "tag2"]}}"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_prompt}, 
                  {"role": "user", "content": "Write a unique, fascinating short script on a new topic."}],
        temperature=0.9,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 2. AUDIO GENERATOR ---
async def generate_audio(script_text):
    print("--- 2. Generating Audio ---")
    communicate = edge_tts.Communicate(script_text, VOICE_ID)
    await communicate.save("audio.mp3")

# --- 3. TRANSCRIPTION (Groq Whisper) ---
def transcribe_audio(audio_path="audio.mp3"):
    print("--- 3. Transcribing ---")
    with open(audio_path, "rb") as file:
        transcription = client.audio.transcriptions.create(file=(audio_path, file.read()), model="whisper-large-v3", response_format="verbose_json")
    
    segments = [{"start_time": round(s['start'], 2), "end_time": round(s['end'], 2), "text": s['text'].strip()} for s in transcription.segments]
    with open("transcript_timestamps.json", "w") as f: json.dump(segments, f, indent=4)
    return segments

# --- 4. PROMPT & IMAGE GENERATOR (API-based) ---
def generate_storyboard(segments):
    print("--- 4. Generating Visuals ---")
    system_prompt = "Output raw JSON array of scenes. Each has 'start_time', 'end_time', and 'visual_prompt'. Prefix prompt with: 'Flat vector art, vintage parchment paper background, sepia color palette. A minimalist silhouette of an explorer...'"
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
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

def compile_video(scenes, audio_path="audio.mp3", output_path="final_video.mp4"):
    print("--- 5. Compiling Video ---")
    
    # 1. Normalize images: Ensure they are all JPG/PNG and readable
    # We will use ffmpeg to convert them to a uniform format first to fix 'status 187'
    for i, scene in enumerate(scenes):
        normalized_path = f"norm_{i:03d}.png"
        # Force convert to ensure the pixel format is compatible with yuv420p
        # This handles bad image headers that might be causing the crash
        subprocess.run(["ffmpeg", "-y", "-i", scene['image_path'], "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280", normalized_path], check=True)
        scene['image_path'] = normalized_path

    # 2. Generate concat file with the normalized paths
    with open("ffmpeg_concat.txt", "w") as f:
        for i, scene in enumerate(scenes):
            f.write(f"file '{scene['image_path']}'\n")
            duration = (scenes[i+1]["start_time"] - scene["start_time"]) if i < len(scenes)-1 else 2.0
            f.write(f"duration {max(0.1, duration):.2f}\n")
        f.write(f"file '{scenes[-1]['image_path']}'\n")
    
    # 3. Final Compile
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
            "-i", "ffmpeg_concat.txt", "-i", audio_path, 
            "-c:v", "libx264", "-pix_fmt", "yuv420p", 
            "-c:a", "aac", "-shortest", output_path
        ], check=True)
        print(f"✅ Video compiled successfully: {output_path}")
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg compilation failed. Check image formats.")
        raise e


# --- MASTER ---
def run_pipeline():
    data = generate_curiosity_script()
    with open("metadata.json", "w") as f: json.dump(data, f)
    asyncio.run(generate_audio(data["script"]))
    segments = transcribe_audio()
    scenes = generate_storyboard(segments)
    compile_video(scenes)
    upload_short_to_youtube("final_video.mp4", "metadata.json")

if __name__ == "__main__":
    run_pipeline()
