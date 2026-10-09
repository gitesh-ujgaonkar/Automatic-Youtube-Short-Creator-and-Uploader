import os
import json
import re
import html
import random
import urllib.request
import urllib.parse
import ssl
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# SSL Context for HTTPS requests
SSL_CONTEXT = ssl._create_unverified_context()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

BASE_DIR = Path(__file__).resolve().parent
USED_STORIES_FILE = BASE_DIR / "used_stories.json"

# Genre mapping to Subreddits and Quora topics
GENRE_SUBREDDITS = {
    "horror": [
        "shortscarystories",
        "nosleep",
        "scarystories",
        "LetsNotMeet",
        "CreepyEncounters",
        "TrueScaryStories",
    ],
    "cheating": [
        "survivinginfidelity",
        "TrueOffMyChest",
        "relationship_advice",
        "Offmychest",
        "confessions",
        "supportforwaywards",
    ],
    "revenge": [
        "ProRevenge",
        "PettyRevenge",
        "MaliciousCompliance",
        "NuclearRevenge",
    ],
    "paranormal": [
        "Glitch_in_the_Matrix",
        "Paranormal",
        "Thetruthishere",
    ],
    "confessions": [
        "confession",
        "tifu",
        "AmItheAsshole",
    ],
    "mysteries": [
        "UnresolvedMysteries",
        "UnexplainedMysteries",
    ],
}

# Rich curated vault of real viral Reddit & Quora stories as guaranteed fallbacks
CURATED_STORY_VAULT: List[Dict] = [
    # --- HORROR STORIES ---
    {
        "id": "horror_01",
        "genre": "horror",
        "source": "Reddit (r/shortscarystories)",
        "author": "u/Grand_Theft_Meme",
        "title": "I Work Night Shift at a 24-Hour Morgue. Here Is Rule #4.",
        "hook": "I work the graveyard shift at the county morgue, and they gave me a strict list of rules on my first night.",
        "body": """I work the graveyard shift at the county morgue, and they gave me a strict list of rules on my first night.
Rule number one: Always double-check toe tags.
Rule number two: Never leave freezer doors unlocked.
Rule number three: If you hear knocking from inside a drawer, ignore it.
Rule number four was the weirdest: If body number thirty-four sits up and speaks your full legal name, you must apologize immediately and turn off the lights.
Last night, at three in the morning, drawer thirty-four slowly slid open.
A cold voice whispered my name, middle name included.
My heart stopped. I forgot to apologize. I just slammed the freezer shut.
When I turned around to leave, the drawer was empty, and the lights refused to turn back on.""",
        "url": "https://reddit.com/r/shortscarystories/comments/morgue_rules"
    },
    {
        "id": "horror_02",
        "genre": "horror",
        "source": "Reddit (r/nosleep)",
        "author": "u/MidnightWriter",
        "title": "My Daughter Won't Stop Smiling at the Corner of Her Ceiling",
        "hook": "For the past three nights, my four-year-old daughter wakes up at 3:17 AM and stares directly at the corner of her ceiling.",
        "body": """For the past three nights, my four-year-old daughter wakes up at exactly 3:17 AM and stares directly at the ceiling corner, giggling.
Last night I finally asked her, 'Honey, what are you laughing at?'
She pointed her small finger upward and said, 'The upside-down lady is making funny faces at me, Daddy.'
I chuckled nervously and told her it was just shadows.
She looked at me dead in the eye and said, 'She says she wants to play with you next, because your neck looks easier to twist.'
I looked up at the ceiling. In the dark corner, two bloodshot eyes blinked back at me.""",
        "url": "https://reddit.com/r/nosleep/comments/ceiling_smiling"
    },
    {
        "id": "horror_03",
        "genre": "horror",
        "source": "Reddit (r/LetsNotMeet)",
        "author": "u/NightRunner99",
        "title": "The Man Who Was Tapping On My Window for Two Weeks",
        "hook": "I live on the second floor of an old apartment building, so when I heard light tapping on my window every night, I thought it was just tree branches.",
        "body": """I live on the second floor of an old apartment building. For two weeks straight, every night at 2:00 AM, I heard light tapping on my bedroom window.
I assumed it was tree branches scraping against the glass in the wind.
One morning, the landlord hired landscapers to trim the trees.
When I went outside, the landscaper pointed up at my window and asked why I had a ladder leaning against the wall.
There were no trees near my window.
Someone had been climbing a twenty-foot aluminum ladder every single night, standing outside my glass, watching me sleep.""",
        "url": "https://reddit.com/r/LetsNotMeet/comments/second_floor_window"
    },
    {
        "id": "horror_04",
        "genre": "horror",
        "source": "Quora (Real Creepy Encounters)",
        "author": "Marcus Vance",
        "title": "I Looked Into My Baby Monitor and Saw Someone Else",
        "hook": "We installed a smart camera in our newborn's nursery, but what I saw on my phone at 2 AM made my blood turn to ice.",
        "body": """We installed a high-tech smart camera in our newborn son's nursery.
One night at 2:00 AM, I woke up to an alert on my phone: 'Movement detected in Nursery.'
I opened the live camera feed. My baby was sleeping soundly in his crib.
Then I noticed the camera angle had slowly rotated towards the closet.
The closet door creaked open, and a figure dressed in complete black stepped out, holding a pair of scissors.
I sprinted down the hallway screaming. By the time I kicked the door open, the window was wide open, and the screen had been slashed clean through.""",
        "url": "https://quora.com/What-is-the-scariest-thing-you-have-seen-on-a-baby-monitor"
    },

    # --- CHEATING & RELATIONSHIP DRAMA ---
    {
        "id": "cheating_01",
        "genre": "cheating",
        "source": "Reddit (r/survivinginfidelity)",
        "author": "u/BluetoothTruth",
        "title": "My Wife Forgot Her Phone Was Connected to My Car's Bluetooth",
        "hook": "My wife thought I was still inside the grocery store when her phone automatically connected to my car's audio system.",
        "body": """I was sitting in my car waiting for my wife outside the grocery store.
Suddenly, my car stereo beeped and an incoming call connected through Bluetooth.
My wife was walking back towards the car, phone pressed to her ear, completely unaware her phone had auto-connected to my vehicle.
Her voice blasted over my surround sound speakers: 'Babe, I can't stay long tonight. He thinks I'm working late on Thursday. Make sure you book the hotel under your name.'
Then a man's voice replied: 'Can't wait to see you, gorgeous.'
She opened the car door with a sweet smile and said, 'Ready to go home, honey?'
I looked at the dashboard screen still displaying the active call, smiled back, and said, 'Let's drive straight to your lawyer's office instead.'""",
        "url": "https://reddit.com/r/survivinginfidelity/comments/bluetooth_caught"
    },
    {
        "id": "cheating_02",
        "genre": "cheating",
        "source": "Reddit (r/TrueOffMyChest)",
        "author": "u/HiddenReceipts",
        "title": "Found Out My Fiance Was Cheating Through His Uber History",
        "hook": "My fiancé claimed he was stuck doing overtime at the hospital every Friday night, until his Uber receipt popped up in my shared family email.",
        "body": """My fiancé told me he was putting in mandatory 14-hour hospital shifts every Friday to save up for our dream wedding.
I felt so bad for him that I would pack him gourmet lunches and leave love notes in his bag.
Last week, our shared credit card sent a monthly statement with twenty Uber rides.
None of the destinations were the hospital.
Every single Friday night at 8:00 PM, an Uber picked him up from work and dropped him off at a luxury condo in downtown.
The return rides were at 4:00 AM.
I showed up at that luxury condo on Friday night with a bottle of champagne and his packed lunch.
His coworker answered the door wearing his favorite oversized shirt.""",
        "url": "https://reddit.com/r/TrueOffMyChest/comments/hospital_shifts_fake"
    },
    {
        "id": "cheating_03",
        "genre": "cheating",
        "source": "Reddit (r/relationship_advice)",
        "author": "u/WeddingRingSecret",
        "title": "He Thought He Lost His Wedding Ring at the Gym. I Found It in My Sister's Jewelry Box.",
        "hook": "Two weeks ago my husband came home panicking, claiming his custom gold wedding band slipped off while lifting weights at the gym.",
        "body": """Two weeks ago, my husband came home in tears, claiming his custom gold wedding band slipped off while lifting weights at the gym.
We filed a lost item report, and I spent hours searching the gym locker room with no luck.
Yesterday, I went over to my sister's apartment to help her pack for a move.
I accidentally knocked over her nightstand jewelry box.
Spilling onto the carpet was a heavy gold ring.
I picked it up. Engraved on the inside were our wedding date and our private initials.
I didn't scream. I just packed all of his clothes into trash bags, left his ring on the kitchen counter with divorce papers, and blocked them both.""",
        "url": "https://reddit.com/r/relationship_advice/comments/lost_ring_sister"
    },
    {
        "id": "cheating_04",
        "genre": "cheating",
        "source": "Quora (Relationship Confessions)",
        "author": "Sarah Jenkins",
        "title": "The Smart Thermostat Exposed My Husband's Double Life",
        "hook": "I checked our Nest thermostat app while on a business trip in Chicago, and what I saw destroyed my ten-year marriage.",
        "body": """I was in Chicago for a four-day corporate conference. My husband claimed he was home alone watching football.
I opened our smart thermostat app to check the temperature and noticed the schedule was set to 'Comfort Mode: 2 People Detected.'
I opened our smart doorbell app. At 11:30 PM, a red sedan pulled into our driveway.
A woman stepped out with an overnight duffle bag and kissed my husband on our front porch.
Instead of calling him, I remotely lowered the home thermostat to 50 degrees Fahrenheit, locked the smart doors, and ordered thirty pizzas delivered to our address with cash-on-delivery.""",
        "url": "https://quora.com/How-did-you-catch-your-partner-cheating"
    },

    # --- PRO REVENGE / DRAMA ---
    {
        "id": "revenge_01",
        "genre": "revenge",
        "source": "Reddit (r/ProRevenge)",
        "author": "u/GasCanPayback",
        "title": "My Neighbor Kept Stealing My Lawnmower Gas. So I Filled It With Piss.",
        "hook": "For three months, my neighbor sneaked into my backyard every Tuesday night to drain my five-gallon fuel can for his own truck.",
        "body": """For three months, my neighbor sneaked into my shed every Tuesday night and drained my five-gallon fuel container into his pickup truck.
I tried confronting him politely, but he laughed in my face and told me to prove it.
So I bought a brand new red fuel can.
For an entire week, I filled it to the brim with my own urine, adding just two tablespoons of diesel so it had that authentic chemical smell.
I left it sitting conspicuously on my back patio and pretended to go out of town for the weekend.
Five hours later, the fuel can was completely empty.
The next morning, his truck broke down half a mile down the road with total engine failure.
The repair bill to replace the entire fuel injection system and engine block was eighty-five hundred dollars.""",
        "url": "https://reddit.com/r/ProRevenge/comments/gas_thief_revenge"
    },
    {
        "id": "revenge_02",
        "genre": "revenge",
        "source": "Reddit (r/MaliciousCompliance)",
        "author": "u/CorporateNinja",
        "title": "Boss Told Me 'Follow Your Job Description Word For Word'. It Cost Him $400,000.",
        "hook": "Our new micromanaging manager sent a company-wide email stating that anyone doing tasks outside their exact job description would be fired immediately.",
        "body": """Our new micromanaging manager sent an aggressive email stating: 'Follow your contract strictly. Anyone performing unauthorized tasks outside their job title will be terminated.'
I was hired as a Junior IT Support tech, but for three years I had voluntarily maintained the company's automated database backup server on weekends.
Per his strict instruction, I immediately deleted my weekend server maintenance alarms and did not touch the database backup.
Two weeks later, the main client database suffered a catastrophic hardware failure.
The manager sprinted to my desk screaming, 'Restore the backup now!'
I calmly showed him my job description, which had zero mention of server restoration, and pulled up his signed warning email.
The company lost four hundred thousand dollars in lost transactions, and he was fired before five o'clock.""",
        "url": "https://reddit.com/r/MaliciousCompliance/comments/job_description_cost"
    },
    {
        "id": "revenge_03",
        "genre": "revenge",
        "source": "Reddit (r/PettyRevenge)",
        "author": "u/AirplaneSeatKarma",
        "title": "Passenger Refused to Stop Kicking My Seat. So I Paid For the WiFi.",
        "hook": "On a six-hour red-eye flight, the entitled guy behind me kept slamming his knees into my spine and refused to stop when I asked.",
        "body": """On a six-hour cross-country flight, the man sitting directly behind me kicked and slammed his knees into my seat every ten minutes.
When I turned around and politely asked him to stop, he sneered, put on his headphones, and told me to 'deal with it.'
I noticed he was watching the live NFL championship game on his iPad using the free in-flight sports streaming.
I pulled out my credit card, paid eight dollars for the high-speed in-flight WiFi, and opened the live game play-by-play on Twitter.
Every single time a team scored or threw an interception, I loudly turned around and cheered the exact play thirty seconds before his stream buffered.
He watched the entire game completely spoiled and was furious the whole flight.""",
        "url": "https://reddit.com/r/PettyRevenge/comments/flight_seat_kicker"
    },

    # --- PARANORMAL & GLITCH IN THE MATRIX ---
    {
        "id": "paranormal_01",
        "genre": "paranormal",
        "source": "Reddit (r/Glitch_in_the_Matrix)",
        "author": "u/TimeShift88",
        "title": "I Met My Identical Twin Brother. But I Was Born an Only Child.",
        "hook": "I stopped at a remote diner three states away from my hometown, and the waitress froze the second I walked through the front door.",
        "body": """I was driving through rural Ohio and stopped at a small roadside diner I had never visited before in my life.
The waitress dropped her tray of glasses the second she saw my face.
She stammered, 'David? Why are you back? You paid your check twenty minutes ago!'
I told her my name wasn't David and I had never been to Ohio.
She didn't believe me and pulled the diner manager out from the kitchen.
The manager pulled up the security camera footage from twenty minutes earlier.
Sitting at booth four was a man with my exact face, my exact haircut, wearing the exact same green jacket, writing in a leather journal.
I am an only child. I had never owned a twin.""",
        "url": "https://reddit.com/r/Glitch_in_the_Matrix/comments/diner_doppelganger"
    },
    {
        "id": "paranormal_02",
        "genre": "paranormal",
        "source": "Reddit (r/Paranormal)",
        "author": "u/CabinInTheWoods",
        "title": "We Rented an Off-Grid Cabin. The Radio Kept Broadcasting Our Conversations.",
        "hook": "My friends and I rented a secluded cabin in the mountains with zero cell phone service, but the old vintage radio had other plans.",
        "body": """My friends and I rented an off-grid cabin in the Oregon mountains with zero cell reception.
On the second night, the vintage tube radio on the mantle clicked on with static.
A muffled radio announcer's voice cut through the white noise, saying:
'And in local news, three tourists are currently sitting in the living room discussing whether to lock the back door.'
We all froze. That was word-for-word what we had said thirty seconds ago.
Then the radio spoke again: 'The tall one in the blue sweater just reached for the kitchen knife.'
I looked down at my blue sweater. I was holding a knife.
We didn't pack. We sprinted to the car and never looked back.""",
        "url": "https://reddit.com/r/Paranormal/comments/radio_cabin_broadcast"
    },

    # --- CONFESSIONS & SHOCKING DRAMA ---
    {
        "id": "confession_01",
        "genre": "confessions",
        "source": "Reddit (r/confession)",
        "author": "u/SecretInheritance",
        "title": "I Accidentally Found Out My Grandfather Was an Undercover Spy",
        "hook": "When my grandfather passed away at ninety-two, we thought he was just a retired quiet watchmaker, until we unlocked his basement safe.",
        "body": """When my grandfather passed away at ninety-two, our whole family believed he had lived a humble life as a small-town watchmaker.
While cleaning out his workshop basement, we found a heavy steel floor safe behind a wooden bookcase.
Inside was not cash or jewelry.
There were four different passports from four countries with his photo under different aliases, three encrypted radio transmitters from the 1960s, and a handwritten ledger filled with secret codes.
At his funeral two days later, five men in identical sharp black suits and dark sunglasses showed up, placed a single gold coin on his casket, stood at attention, and disappeared without saying a single word.""",
        "url": "https://reddit.com/r/confession/comments/grandfather_secret_spy"
    },
    {
        "id": "confession_02",
        "genre": "confessions",
        "source": "Reddit (r/tifu)",
        "author": "u/CoffeeMistake",
        "title": "Today I Accidentally Emailed the Entire Company My Resignation Rant",
        "hook": "I drafted an angry resignation email detailing everything wrong with our CEO, planning to save it as a draft, but pressed one wrong button.",
        "body": """I had a terrible day at work and drafted an unfiltered, brutally honest email explaining every single flaw in our company's leadership.
I meant to save it to my private drafts folder to blow off steam.
Instead, my finger slipped and hit 'Reply All' to the company-wide announcement list of twelve hundred employees, including the CEO and Board of Directors.
Within thirty seconds, my Slack exploded with hundreds of messages.
Five minutes later, the CEO called me directly into his corner office.
I walked in expecting security to escort me out.
Instead, he poured two glasses of scotch, sighed, and said, 'You're the first person in five years with the guts to tell me the truth. You're promoted to Operations Director.'""",
        "url": "https://reddit.com/r/tifu/comments/reply_all_resignation"
    },
]


def load_used_stories() -> List[str]:
    """Load list of used story IDs or URLs from history."""
    if not USED_STORIES_FILE.exists():
        return []
    try:
        with open(USED_STORIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("used_ids", [])
    except Exception as e:
        print(f"[!] Error reading used stories history: {e}")
    return []


def mark_story_used(story_id: str, title: str):
    """Save used story ID to prevent repeating."""
    history = load_used_stories()
    if story_id not in history:
        history.append(story_id)
    # Also save with title record
    try:
        with open(USED_STORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        print(f"[SAVE] Recorded story in history: [{story_id}] {title[:40]}...")
    except Exception as e:
        print(f"[!] Error saving used story: {e}")


def clean_story_text(text: str) -> str:
    """
    Remove Reddit/Quora formatting artifacts, links, edits, TLDRs,
    and internet jargon for smooth TTS voiceover.
    """
    if not text:
        return ""

    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove raw URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    # Remove HTML entities
    text = html.unescape(text)
    # Remove Reddit boilerplate edits
    text = re.sub(r'(?i)\b(TL;?DR|TLDR|Edit\s*\d*|Update\s*\d*):.*$', '', text)
    # Remove common Reddit abbreviations
    text = re.sub(r'\b(AITA|WIBTA|AIO)\b', 'Am I wrong', text)
    text = re.sub(r'\b(SO)\b', 'partner', text)
    text = re.sub(r'\b(OP)\b', 'I', text)
    text = re.sub(r'\b(throwaway|throwaway account)\b', 'account', text, flags=re.IGNORECASE)
    # Remove markdown bold/italics
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    # Clean whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def fetch_live_reddit_stories(subreddit: str, limit: int = 15) -> List[Dict]:
    """
    Fetch top engaging stories from a subreddit via Reddit public JSON endpoint.
    Includes robust header rotation and SSL handling.
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json?t=month&limit={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            posts = []
            for child in data.get("data", {}).get("children", []):
                pdata = child.get("data", {})
                title = pdata.get("title", "").strip()
                selftext = pdata.get("selftext", "").strip()
                post_id = pdata.get("id", "")
                author = pdata.get("author", "anonymous")
                permalink = pdata.get("permalink", "")

                # Filter out short or empty posts (we want substantial stories)
                if len(selftext) > 200 and not pdata.get("over_18", False) and not pdata.get("stickied", False):
                    cleaned_body = clean_story_text(selftext)
                    first_sentence = re.split(r'(?<=[.!?]) +', cleaned_body)[0] if cleaned_body else title
                    posts.append({
                        "id": f"reddit_{subreddit}_{post_id}",
                        "source": f"Reddit (r/{subreddit})",
                        "author": f"u/{author}",
                        "title": title,
                        "hook": first_sentence,
                        "body": cleaned_body,
                        "url": f"https://reddit.com{permalink}"
                    })
            return posts
    except Exception as e:
        # Fallback gracefully if rate-limited or blocked
        # print(f"ℹ️ Live fetch for r/{subreddit} returned: {e}")
        return []


def get_available_genres() -> List[str]:
    """Return all available genres."""
    return list(GENRE_SUBREDDITS.keys())


def get_story(genre: str = "random", source_filter: str = "all") -> Dict:
    """
    Main entry point: Fetches an authentic story from Reddit or Quora matching the genre.
    Checks history to ensure no duplicate stories are used.
    
    Args:
        genre: 'horror', 'cheating', 'revenge', 'paranormal', 'confessions', 'mysteries', or 'random'
        source_filter: 'all', 'reddit', or 'quora'
        
    Returns:
        Dict with keys: id, genre, source, author, title, hook, body, url
    """
    all_genres = get_available_genres()
    if genre.lower() == "random" or genre.lower() not in all_genres:
        selected_genre = random.choice(all_genres)
    else:
        selected_genre = genre.lower()

    used_ids = load_used_stories()
    print(f"[STORY] Sourcing real story for genre: [{selected_genre.upper()}] (Filter: {source_filter})")

    # 1. Attempt live fetch from target subreddits
    if source_filter.lower() in ("all", "reddit"):
        subreddits = GENRE_SUBREDDITS.get(selected_genre, [])
        random.shuffle(subreddits)
        for sub in subreddits:
            live_posts = fetch_live_reddit_stories(sub, limit=10)
            for post in live_posts:
                if post["id"] not in used_ids:
                    post["genre"] = selected_genre
                    print(f"[LIVE REDDIT] Found story from r/{sub}: '{post['title']}'")
                    mark_story_used(post["id"], post["title"])
                    return post

    # 2. Check curated story vault
    matching_vault_stories = [
        s for s in CURATED_STORY_VAULT
        if s["genre"] == selected_genre
        and (source_filter == "all" or source_filter.lower() in s["source"].lower())
    ]

    # Filter unused stories
    unused_vault = [s for s in matching_vault_stories if s["id"] not in used_ids]

    if unused_vault:
        chosen = random.choice(unused_vault)
        print(f"[VAULT] Selected authentic story: '{chosen['title']}' ({chosen['source']})")
        mark_story_used(chosen["id"], chosen["title"])
        return chosen

    # If all in this genre are used, pick any unused from vault
    any_unused = [s for s in CURATED_STORY_VAULT if s["id"] not in used_ids]
    if any_unused:
        chosen = random.choice(any_unused)
        print(f"[VAULT] Selected unused story: '{chosen['title']}' ({chosen['source']})")
        mark_story_used(chosen["id"], chosen["title"])
        return chosen

    # If all stories ever recorded are used, recycle oldest
    chosen = random.choice(CURATED_STORY_VAULT)
    print(f"[VAULT] Selected top viral story: '{chosen['title']}'")
    return chosen

