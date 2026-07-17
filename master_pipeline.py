import json
import os
import asyncio
import nest_asyncio
import edge_tts
import requests
import urllib.parse
import subprocess
from groq import Groq
from youtube_uploader import upload_short_to_youtube

# Setup
nest_asyncio.apply()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
VOICE_ID = "en-US-ChristopherNeural"

# --- 1. SCRIPT GENERATOR ---
def generate_curiosity_script():
    print("--- 1. Generating Script ---")
    system_prompt = """You are a viral YouTube Shorts scriptwriter (Ink Explainer style).
    TASK: Write a 60-second script based on a random fascinating topic.
    RULES: 140-160 words, start with a 3-second curiosity gap hook, documentary tone.
    Output ONLY in JSON: {"title": "...", "script": "...", "description": "...", "tags": ["tag1", "tag2"]}"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": "Write a random fascinating short script."}],
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
    system_prompt = "Output raw JSON array of scenes. Each has 'start_time', 'end_time', and 'visual_prompt'. Prefix prompt with: 'Flat vector art, vintage parchment paper background, sepia palette. A minimalist silhouette of an explorer...'"
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(segments)}], response_format={"type": "json_object"})
    scenes = json.loads(response.choices[0].message.content)["scenes"]
    
    for i, scene in enumerate(scenes):
        print(f"Fetching scene {i+1}...")
        prompt = urllib.parse.quote(scene["visual_prompt"])
        response = requests.get(f"https://image.pollinations.ai/prompt/{prompt}?width=768&height=1344&nologo=true")
        img_path = f"scene_{i:03d}.png"
        with open(img_path, 'wb') as f: f.write(response.content)
        scene["image_path"] = img_path
    
    with open("storyboard.json", "w") as f: json.dump(scenes, f, indent=4)
    return scenes

# --- 5. VIDEO COMPILER ---
def compile_video(scenes, audio_path="audio.mp3", output_path="final_video.mp4"):
    print("--- 5. Compiling Video ---")
    
    # Debug: Check if images exist
    for scene in scenes:
        if not os.path.exists(scene['image_path']):
            print(f"❌ ERROR: Missing image file: {scene['image_path']}")
            return

    with open("ffmpeg_concat.txt", "w") as f:
        for i, scene in enumerate(scenes):
            img_path = os.path.abspath(scene['image_path'])
            f.write(f"file '{img_path}'\n")
            duration = (scenes[i+1]["start_time"] - scene["start_time"]) if i < len(scenes)-1 else 2.0
            f.write(f"duration {max(0.1, duration):.2f}\n")
        f.write(f"file '{os.path.abspath(scenes[-1]['image_path'])}'\n")
    
    # We use 'which ffmpeg' to find the path in the environment
    try:
        ffmpeg_path = subprocess.check_output(["which", "ffmpeg"]).decode().strip()
        print(f"Using FFmpeg at: {ffmpeg_path}")
        
        cmd = [
            ffmpeg_path, "-y", "-f", "concat", "-safe", "0", 
            "-i", "ffmpeg_concat.txt", "-i", audio_path, 
            "-c:v", "libx264", "-pix_fmt", "yuv420p", 
            "-c:a", "aac", "-shortest", output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Video compiled: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg failed!")
        print("Stdout:", e.stdout)
        print("Stderr:", e.stderr)
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
