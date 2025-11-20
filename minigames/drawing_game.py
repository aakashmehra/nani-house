# drawing_game_terminal.py
import os
import base64
import random
import json
import re
from io import BytesIO
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # reads .env in current folder

# --------- config / client ----------
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment or .env")
client = OpenAI(api_key=API_KEY)

# --------- prompts ----------
PROMPTS = [
    "Draw a simple robot",
    "Draw a pencil",
    "Draw a cartoon cat head",
    "Draw a paper airplane",
    "Draw a balloon with stripes",
    "Draw an ice cream cone",
    "Draw a small tree with a round top",
    "Draw a smiling sun",
    "Draw a cloud with rain",
    "Draw a crescent moon",
    "Draw a small house",
    "Draw a simple car",
    "Draw a boat on water",
    "Draw a fish",
    "Draw a star",
    "Draw a heart",
    "Draw a simple flower",
    "Draw a mushroom",
    "Draw a cup",
    "Draw a slice of pizza",
    "Draw a donut",
    "Draw a simple bird",
    "Draw a butterfly",
    "Draw a leaf",
    "Draw a tree stump",
    "Draw a ghost",
    "Draw a simple dog head",
    "Draw a simple cat sitting",
    "Draw a teddy bear face",
    "Draw a rocket",
    "Draw a planet with a ring",
    "Draw a cactus",
    "Draw a simple chair",
    "Draw a backpack",
    "Draw a gift box",
    "Draw a clock",
    "Draw a key",
    "Draw a simple umbrella",
    "Draw a balloon animal",
    "Draw a cookie",
    "Draw a snowman",
    "Draw a mitten",
    "Draw a rainbow",
    "Draw a simple bunny head",
    "Draw a snail",
    "Draw a simple camera",
    "Draw a diamond shape",
    "Draw a lollipop",
    "Draw a starfish",
    "Draw an apple",
    "Draw a simple kite",
    "Draw a candy cane",
    "Draw a bear"
]

def random_prompt():
    return random.choice(PROMPTS)

# --------- helpers ----------
def image_to_data_url(path):
    img = Image.open(path).convert("RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def request_openai_rating(data_url, task):
    prompt_text = (
    f"Rate this simple line drawing (single pen stroke) strictly based on how well it matches "
    f"this task: '{task}'.\n"
    f"Do NOT be extremely strict.\n\n"
    f"Scoring rules:\n"
    f"- 8–10: GOOD match. Clearly the correct object.\n"
    f" If it is a different object (e.g., elephant vs ice cream), it MUST NOT be in this range.\n"
    f"- 7 : If it is a match, incomplete, or not a strong match, it MUST be this.\n"
    f"- 1–7: Does NOT resemble the task, wrong object, or unrecognizable.\n\n"
    f"If the drawing does NOT look like the described object, rating MUST be 1–4.\n"
    f"If it looks like a completely different object, rating MUST be 1.\n\n"
    f"Return ONLY JSON like: {{\"rating\": <1-10> }}\n\n"
    f"Image:\n{data_url}"
)

    resp = client.responses.create(
        model="gpt-4o-mini",
        input=prompt_text,
        max_output_tokens=150,
        temperature=0.2
    )

    # extract text safely
    text = ""
    if hasattr(resp, "output"):
        for block in resp.output:
            if hasattr(block, "content"):
                for sub in block.content:
                    if isinstance(sub, dict) and sub.get("type") == "output_text":
                        text += sub.get("text", "")
    if not text:
        text = str(resp)

    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            parsed = json.loads(m.group(0))
            rating = int(parsed.get("rating", 0))
            rating = max(1, min(10, rating))
            return rating, feedback, text
        except Exception:
            pass
    # fallback: try to find a number 1-10 in text
    digits = re.findall(r"\b(10|[1-9])\b", text)
    rating = int(digits[0]) if digits else None
    return rating, text, text

# --------- main ----------
if __name__ == "__main__":
    task = random_prompt()
    print("\nYour task:")
    print(" →", task)
    print("\nEnter your image path (screenshot of drawing). Quotes will be stripped:")
    img_path = input("> ").strip().strip('"').strip("'")

    # make path absolute if it's relative to home shorthand
    if img_path.startswith('~'):
        img_path = os.path.expanduser(img_path)
    
    if not os.path.exists(img_path):
        print(f"Error: File not found: {img_path}")
        exit(1)
    
    print("\nProcessing image...")
    data_url = image_to_data_url(img_path)
    
    print("Sending to OpenAI for rating...")
    rating, feedback, raw = request_openai_rating(data_url, task)
    
    print("\n" + "="*50)
    if rating is not None:
        print(f"Rating: {rating}/10")
        if feedback and feedback != raw:
            print(f"Feedback: {feedback}")
    else:
        print("Could not extract rating from response.")
        print(f"Raw response: {raw[:200]}...")
    print("="*50)
