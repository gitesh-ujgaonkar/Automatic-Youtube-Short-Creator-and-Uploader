import json
import os
import asyncio
import nest_asyncio
import edge_tts
import requests
import urllib.parse
import subprocess
import time
from groq import Groq
from youtube_uploader import upload_short_to_youtube


# Setup
nest_asyncio.apply()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
VOICE_ID = "en-US-ChristopherNeural"

#--- Find Model
def get_best_available_model(client):
    try:
        print("🔍 Scanning for best available Groq model...")
        available_models = client.models.list()
        active_model_ids = [m.id for m in available_models.data]
        
        preferred_models = [
            "openai/gpt-oss-120b",  # Top choice
            "qwen/qwen3.6-27b",     # Great secondary option
            "llama3-70b-8192",      # Reliable older model
            "mixtral-8x7b-32768"    # Fast fallback
        ]
        
        for model in preferred_models:
            if model in active_model_ids:
                print(f"✅ Auto-selected AI Model: {model}")
                return model
                
        fallback_model = active_model_ids[0]
        print(f"⚠️ Preferred models missing. Auto-falling back to: {fallback_model}")
        return fallback_model
        
    except Exception as e:
        print(f"⚠️ Could not fetch model list. Defaulting to safe fallback. Error: {e}")
        return "openai/gpt-oss-120b"

best_model = get_best_available_model(client)

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
        if new_clean == past_clean or new_clean in past_clean or past_clean in new_clean:
            return True
    return False

import sys

# Attempt multi-path import of story_fetcher
try:
    from story_fetcher import get_story, get_available_genres
except ImportError:
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "Auto_youtuber"))
        from story_fetcher import get_story, get_available_genres
    except ImportError:
        # Self-contained fallback story library in case story_fetcher.py is not in working directory
        _FALLBACK_VAULT = [
            {
                "id": "horror_01",
                "genre": "horror",
                "source": "Reddit (r/shortscarystories)",
                "author": "u/Grand_Theft_Meme",
                "title": "I Work Night Shift at a 24-Hour Morgue. Here Is Rule #4.",
                "hook": "I work the graveyard shift at the county morgue, and they gave me a strict list of rules on my first night.",
                "body": "I work the graveyard shift at the county morgue, and they gave me a strict list of rules on my first night. Rule number one: Always double-check toe tags. Rule number two: Never leave freezer doors unlocked. Rule number three: If you hear knocking from inside a drawer, ignore it. Rule number four was the weirdest: If body number thirty-four sits up and speaks your full legal name, you must apologize immediately and turn off the lights. Last night, at three in the morning, drawer thirty-four slowly slid open. A cold voice whispered my full name. My heart stopped. I forgot to apologize. I just slammed the freezer shut. When I turned around to leave, the drawer was empty, and the lights refused to turn back on.",
                "url": "https://reddit.com/r/shortscarystories"
            },
            {
                "id": "cheating_01",
                "genre": "cheating",
                "source": "Reddit (r/survivinginfidelity)",
                "author": "u/BluetoothTruth",
                "title": "My Wife Forgot Her Phone Was Connected to My Car's Bluetooth",
                "hook": "My wife thought I was still inside the grocery store when her phone automatically connected to my car's audio system.",
                "body": "I was sitting in my car waiting for my wife outside the grocery store. Suddenly, my car stereo beeped and an incoming call connected through Bluetooth. My wife was walking back towards the car, phone pressed to her ear, completely unaware her phone had auto-connected to my vehicle. Her voice blasted over my speakers: 'Babe, I can't stay long tonight. He thinks I'm working late on Thursday. Make sure you book the hotel under your name.' Then a man's voice replied: 'Can't wait to see you, gorgeous.' She opened the car door with a sweet smile and said, 'Ready to go home, honey?' I looked at the dashboard screen still displaying the active call, smiled back, and said, 'Let's drive straight to your lawyer's office instead.'",
                "url": "https://reddit.com/r/survivinginfidelity"
            },
            {
                "id": "revenge_01",
                "genre": "revenge",
                "source": "Reddit (r/ProRevenge)",
                "author": "u/GasCanPayback",
                "title": "My Neighbor Kept Stealing My Lawnmower Gas. So I Filled It With Piss.",
                "hook": "For three months, my neighbor sneaked into my backyard every Tuesday night to drain my five-gallon fuel can for his own truck.",
                "body": "For three months, my neighbor sneaked into my shed every Tuesday night and drained my five-gallon fuel container into his pickup truck. I tried confronting him politely, but he laughed in my face and told me to prove it. So I bought a brand new red fuel can. For an entire week, I filled it to the brim with my own urine, adding just two tablespoons of diesel so it had that authentic chemical smell. I left it sitting conspicuously on my back patio and pretended to go out of town for the weekend. Five hours later, the fuel can was completely empty. The next morning, his truck broke down half a mile down the road with total engine failure. The repair bill to replace the entire fuel injection system and engine block was eighty-five hundred dollars.",
                "url": "https://reddit.com/r/ProRevenge"
            },
            {
                "id": "cheating_02",
                "genre": "cheating",
                "source": "Reddit (r/relationship_advice)",
                "author": "u/WeddingRingSecret",
                "title": "He Thought He Lost His Wedding Ring at the Gym. I Found It in My Sister's Jewelry Box.",
                "hook": "Two weeks ago my husband came home panicking, claiming his custom gold wedding band slipped off while lifting weights at the gym.",
                "body": "Two weeks ago, my husband came home in tears, claiming his custom gold wedding band slipped off while lifting weights at the gym. We filed a lost item report, and I spent hours searching the gym locker room with no luck. Yesterday, I went over to my sister's apartment to help her pack for a move. I accidentally knocked over her nightstand jewelry box. Spilling onto the carpet was a heavy gold ring. I picked it up. Engraved on the inside were our wedding date and our private initials. I didn't scream. I just packed all of his clothes into trash bags, left his ring on the kitchen counter with divorce papers, and blocked them both.",
                "url": "https://reddit.com/r/relationship_advice"
            },
            {
                "id": "paranormal_01",
                "genre": "paranormal",
                "source": "Reddit (r/Paranormal)",
                "author": "u/CabinInTheWoods",
                "title": "We Rented an Off-Grid Cabin. The Radio Kept Broadcasting Our Conversations.",
                "hook": "My friends and I rented a secluded cabin in the mountains with zero cell phone service, but the old vintage radio had other plans.",
                "body": "My friends and I rented an off-grid cabin in the Oregon mountains with zero cell reception. On the second night, the vintage tube radio on the mantle clicked on with static. A muffled radio announcer's voice cut through the white noise, saying: 'And in local news, three tourists are currently sitting in the living room discussing whether to lock the back door.' We all froze. That was word-for-word what we had said thirty seconds ago. Then the radio spoke again: 'The tall one in the blue sweater just reached for the kitchen knife.' I looked down at my blue sweater. I was holding a knife. We didn't pack. We sprinted to the car and never looked back.",
                "url": "https://reddit.com/r/Paranormal"
            }
        ]

        def get_available_genres():
            return ["horror", "cheating", "revenge", "paranormal", "confessions", "mysteries"]

        def get_story(genre="random", source_filter="all"):
            import random
            if genre == "random":
                return random.choice(_FALLBACK_VAULT)
            matches = [s for s in _FALLBACK_VAULT if s["genre"] == genre]
            return random.choice(matches) if matches else random.choice(_FALLBACK_VAULT)

# --- 1. SCRIPT GENERATOR (REDDIT & QUORA STORY ADAPTER) ---
def generate_curiosity_script(genre="random"):
    print(f"\n--- 1. Sourcing Story from Reddit & Quora (Genre: {genre}) ---")
    
    # 1. Fetch authentic story
    story = get_story(genre=genre)
    print(f"[STORY] Sourced Story: '{story['title']}' ({story['source']})")
    
    genre_tag = story.get("genre", "story").replace(" ", "")
    
    system_prompt = f"""You are an elite YouTube Shorts script adapter.
Adapt the following REAL story from {story['source']} into a viral, high-retention 45-50 second voiceover narration.

AUTHENTIC STORY DETAILS:
Title: {story['title']}
Hook: {story['hook']}
Full Story: {story['body']}

RULES:
1. Preserve 100% of the true story plot, twist, and drama. Do NOT make up unrelated facts.
2. The "script" MUST contain ONLY the exact words the narrator speaks out loud. No stage directions, no narrator labels, no visual prompts.
3. Aim for approx 80-100 punchy spoken words.
4. Output in JSON format exactly: {{"title": "...", "script": "...", "description": "...", "tags": ["tag1", "tag2"]}}"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Adapt this real {genre_tag} story for voiceover narration now."}
    ]
    
    try:
        print(f"⏳ Calling Groq LLM to adapt Reddit/Quora story into script...")
        response = client.chat.completions.create(
            model=best_model,
            messages=messages,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        if not data.get("title"):
            data["title"] = story["title"]
        if not data.get("description"):
            data["description"] = f"Story from {story['source']}. #shorts #redditstories #{genre_tag}"
        print(f"✅ Adapted script: '{data['title']}'")
        print(f"📝 Script preview: {data['script'][:100]}...")
        return data
    except Exception as e:
        print(f"⚠️ Groq call failed ({e}). Using direct authentic story fallback...")
        # Clean sentences fallback
        import re
        sentences = re.split(r'(?<=[.!?]) +', story['body'].strip())
        script_text = " ".join(sentences[:5]) if sentences else story['body'][:400]
        return {
            "title": story["title"],
            "script": script_text,
            "description": f"{story['title']}\n\nSourced from {story['source']} by {story['author']}.\n\n#shorts #redditstories #{genre_tag}",
            "tags": ["reddit stories", "storytime", genre_tag, "viral", "shorts"]
        }



# --- 2. AUDIO GENERATOR ---
async def generate_audio(script_text):
    print("\n--- 2. Generating Voiceover Audio ---")
    print(f"🎙️ Using Edge TTS Voice: {VOICE_ID}")
    communicate = edge_tts.Communicate(script_text, VOICE_ID)
    await communicate.save("audio.mp3")
    print("✅ Audio saved as audio.mp3")

# --- 3. TRANSCRIPTION & SUBTITLES ---
def transcribe_audio(audio_path, client):
    print("\n--- 3. Transcribing Audio & Generating Subtitles ---")
    print("🤖 Sending audio to Groq Whisper API for timestamp mapping...")
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo", 
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"] 
        )
    print(f"✅ Transcription complete! Extracted {len(transcript.words)} words and {len(transcript.segments)} sentences.")
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
    print(f"✍️ Formatting {len(chunks)} subtitle chunks into ASS file...")
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
            start_time = format_ass_time(chunk[0]['start'])
            end_time = format_ass_time(chunk[-1]['end'])
            text = " ".join([w['word'].strip() for w in chunk])
            f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
    print("✅ Subtitles saved as subtitles.ass")

# --- 4. PROMPT & IMAGE GENERATOR (API-based) ---
def generate_storyboard(segments):
    print("\n--- 4. Generating Visuals (Storyboard & Images) ---")
    current_model = get_best_available_model(client)
    
    print("🧠 Asking LLM to assign visual prompts to sentence segments...")
    system_prompt = (
        "Output raw JSON array or object containing 'scenes'. "
        "Each scene object must contain 'start_time', 'end_time', and 'visual_prompt'. "
        "Prefix prompt with: 'Flat vector art, vintage parchment paper background, sepia color palette. "
        "A minimalist silhouette of an explorer...'"
    )
    
    response = client.chat.completions.create(
        model=current_model, 
        messages=[
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": json.dumps(segments)}
        ], 
        response_format={"type": "json_object"}
    )
    
    raw_content = response.choices[0].message.content.strip()
    
    if raw_content.startswith("```"):
        raw_content = raw_content.strip("`")
        if raw_content.startswith("json"):
            raw_content = raw_content[4:].strip()

    parsed = json.loads(raw_content)

    if isinstance(parsed, list):
        scenes = parsed
    elif isinstance(parsed, dict) and "scenes" in parsed:
        scenes = parsed["scenes"]
    elif isinstance(parsed, dict):
        scenes = next((v for v in parsed.values() if isinstance(v, list)), [])
    else:
        scenes = []

    print(f"🎬 Total scenes planned: {len(scenes)}")

    for i, scene in enumerate(scenes):
        prompt = urllib.parse.quote(scene.get("visual_prompt", ""))
        img_path = f"scene_{i:03d}.png"
        
        success = False
        for attempt in range(3):
            try:
                print(f"   🖼️ Fetching Image {i+1}/{len(scenes)} (Attempt {attempt+1})...")
                url = f"https://image.pollinations.ai/prompt/{prompt}?width=768&height=1344&nologo=true&seed={i+attempt}"
                img_response = requests.get(url, timeout=60)
                
                if img_response.status_code == 200 and len(img_response.content) > 1000:
                    with open(img_path, 'wb') as f:
                        f.write(img_response.content)
                    scene["image_path"] = img_path
                    success = True
                    break
                else:
                    print(f"   ⚠️ Attempt {attempt+1} failed (Status: {img_response.status_code})")
            except Exception as e:
                print(f"   ⚠️ Attempt {attempt+1} error: {e}")
            
            time.sleep(5)
        
        if not success:
            print(f"   ❌ Critical Failure: Could not generate scene {i+1}, using fallback transparent pixel.")
            with open(img_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
            scene["image_path"] = img_path

    with open("storyboard.json", "w") as f:
        json.dump(scenes, f, indent=4)
        
    print("✅ All visual scenes generated successfully!")
    return scenes

# --- 5. COMPILE VIDEO ---
def compile_video(scenes, audio_path="audio.mp3", ass_path="subtitles.ass", output_path="final_video.mp4"):
    print("\n--- 5. Compiling Final Video ---")
    
    print("📏 Normalizing image resolutions for Short format (720x1280)...")
    for i, scene in enumerate(scenes):
        norm = f"norm_{i:03d}.png"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-i", scene['image_path'], 
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280", 
            norm
        ], check=True)
        scene['image_path'] = norm
    
    print("📝 Generating FFmpeg concatenation playlist...")
    with open("ffmpeg_concat.txt", "w") as f:
        for i, scene in enumerate(scenes):
            f.write(f"file '{scene['image_path']}'\n")
            dur = (scenes[i+1]["start_time"] - scene["start_time"]) if i < len(scenes) - 1 else 2.0
            f.write(f"duration {max(0.1, dur):.2f}\n")
        f.write(f"file '{scenes[-1]['image_path']}'\n")

    print("🎞️ Rendering video, burning in subtitles, and mixing audio (This may take a minute)...")
    subprocess.run([
        "ffmpeg", "-y", "-v", "warning",
        "-f", "concat", "-safe", "0", "-i", "ffmpeg_concat.txt",
        "-i", audio_path,
        "-vf", f"fps=30,ass={ass_path}", 
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ], check=True)
    print(f"✅ Video compiled successfully as '{output_path}'!")

# --- 6. MAIN PIPELINE ---
def run_pipeline():
    print("🚀 STARTING AUTOMATED SHORTS PIPELINE")
    
    data = generate_curiosity_script()
    save_topic(data["title"])
    with open("metadata.json", "w") as f: json.dump(data, f)
    
    # 1. Generate Voice
    asyncio.run(generate_audio(data["script"]))
    
    # 2. Get both words AND sentence-level segments
    words, segments = transcribe_audio("audio.mp3", client)
    
    # 3. Create 3-word dynamic subtitles
    chunks = chunk_words(words)
    create_ass_subtitles(chunks)
    
    # 4. Generate Storyboard using sentence-level segments
    scenes = generate_storyboard(segments)
    
    # 5. Compile Video
    compile_video(scenes)
    
    # 6. Upload
    print("\n--- 6. Uploading to YouTube ---")
    upload_short_to_youtube("final_video.mp4", "metadata.json")
    print("✅ Upload triggered!")
    
    # Push updates
    print("\n--- 7. Pushing History to GitHub ---")
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=False)
    subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=False)
    subprocess.run(["git", "add", "history.json"], check=False)
    subprocess.run(["git", "commit", "-m", f"Update history: {data['title']}"], check=False)
    subprocess.run(["git", "push"], check=False)
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY! 🎉")

if __name__ == "__main__":
    run_pipeline()
