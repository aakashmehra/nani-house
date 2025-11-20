# Minigame routes and logic for Battle Lanes

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import os
import base64
import random
import json
import re
from io import BytesIO
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# OpenAI client setup
API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client: {e}")

# Drawing game prompts
DRAWING_PROMPTS = [
    "Draw a simple robot (one continuous line)",
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

# Import twister game functions from the minigames directory
# Using importlib to load from minigames/twister_game.py
import sys
import importlib.util

twister_module_path = os.path.join(os.path.dirname(__file__), 'minigames', 'twister_game.py')
if os.path.exists(twister_module_path):
    spec = importlib.util.spec_from_file_location("twister_game_module", twister_module_path)
    twister_game_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(twister_game_module)
    
    get_twister_task = twister_game_module.get_twister_task
    submit_twister_recording = twister_game_module.submit_twister_recording
else:
    # Fallback if file doesn't exist
    def get_twister_task():
        return {"error": "twister game module not found"}, 500
    def submit_twister_recording(twist_id, audio_file):
        return {"error": "twister game module not found"}, 500

minigame_bp = Blueprint('minigame', __name__)

# ============================================================================
# MINIGAME ROUTES
# ============================================================================

@minigame_bp.route('/medicine_game')
def medicine_game():
    """Medicine game - choose 3 medicines from 6 options"""
    return render_template('minigames_temp/medicine_game.html')

@minigame_bp.route('/drawing_game')
def drawing_game():
    """Drawing game - draw a picture"""
    return render_template('minigames_temp/drawing_game.html')

@minigame_bp.route('/twister_game')
def twister_game():
    """Twister game - say tongue twisters"""
    return render_template('minigames_temp/twister_game.html')

@minigame_bp.route('/drawing_game/task')
def drawing_game_task():
    """Get a random drawing task"""
    task = random.choice(DRAWING_PROMPTS)
    return jsonify({'task': task})

@minigame_bp.route('/drawing_game/rate', methods=['POST'])
def drawing_game_rate():
    """Rate a drawing using OpenAI"""
    if not client:
        return jsonify({
            'success': False,
            'error': 'OpenAI API not configured'
        }), 500
    
    try:
        data = request.get_json()
        image_data = data.get('image')
        task = data.get('task', '')
        
        if not image_data:
            return jsonify({
                'success': False,
                'error': 'No image provided'
            }), 400
        
        # Extract base64 data from data URL
        try:
            # Remove data URL prefix if present (e.g., "data:image/png;base64,")
            if image_data.startswith('data:'):
                # Find the comma that separates the header from the data
                comma_idx = image_data.find(',')
                if comma_idx != -1:
                    image_data = image_data[comma_idx + 1:]
            
            # Decode base64 image (transparent PNG)
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes)).convert("RGBA")
            
            # Verify image is not empty
            width, height = image.size
            print(f"Original image size: {width}x{height}")
            
            # Create a copy for OpenAI (resize but keep transparent)
            image_for_openai = image.copy()
            
            # Resize image to reduce OpenAI API costs
            # Line drawings don't need high resolution - 512x512 is plenty
            max_size = 512
            if image_for_openai.width > max_size or image_for_openai.height > max_size:
                # Maintain aspect ratio
                image_for_openai.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                print(f"Resized for OpenAI to {image_for_openai.size[0]}x{image_for_openai.size[1]}")
            
            # Save image to drawing_game_canvas folder (in project root) WITH white background
            project_root = os.path.dirname(os.path.abspath(__file__))
            canvas_folder = os.path.join(project_root, 'drawing_game_canvas')
            os.makedirs(canvas_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f'drawing_{timestamp}.png'
            filepath = os.path.join(canvas_folder, filename)
            
            # Save with white background
            white_bg = Image.new('RGB', image.size, (255, 255, 255))
            white_bg.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            white_bg.save(filepath, format='PNG')
            print(f"Image saved with white background to: {filepath}")
            
            # Convert to JPEG for OpenAI (transparent areas become white automatically)
            # But we want to preserve transparency, so convert RGBA to RGB with white background
            openai_bg = Image.new('RGB', image_for_openai.size, (255, 255, 255))
            openai_bg.paste(image_for_openai, mask=image_for_openai.split()[3] if len(image_for_openai.split()) > 3 else None)
            
            buf = BytesIO()
            openai_bg.save(buf, format="JPEG", quality=85, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64}"
            
            print(f"Image for OpenAI: JPEG {image_for_openai.size[0]}x{image_for_openai.size[1]}, base64 length: {len(b64)} bytes ({len(b64)/1024:.2f} KB)")
        except Exception as e:
            print(f"Error processing image: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error processing image: {str(e)}'
            }), 400
        
        # Request rating from OpenAI using Vision API - BALANCED STRICT
        prompt_text = (
            f"You are a fair but strict art judge rating a simple line drawing. Task: '{task}'.\n\n"
            f"FIRST: Identify what object the drawing actually shows.\n\n"
            f"SCORING RULES:\n\n"
            f"WRONG OBJECT (score 1-4):\n"
            f"- If the drawing shows a DIFFERENT object than requested = 1-4\n"
            f"- Examples: ball/circle for 'apple' = 1-2, elephant for 'ice cream' = 1-2\n"
            f"- Completely wrong object = 1-2, vaguely wrong = 3-4\n\n"
            f"CORRECT OBJECT - GOOD QUALITY (score 7-10):\n"
            f"- 9-10: Clearly recognizable as the CORRECT object, well-drawn, matches task perfectly\n"
            f"- 8: Clearly the CORRECT object, recognizable, well-executed, minor imperfections\n"
            f"- 7: CORRECT object, recognizable, decent quality, some roughness acceptable\n\n"
            f"CORRECT OBJECT - POOR QUALITY (score 4-6):\n"
            f"- 6: CORRECT object but incomplete, rough, or missing key features\n"
            f"- 5: CORRECT object but very rough, barely recognizable, incomplete\n"
            f"- 4: CORRECT object but extremely poor quality or very incomplete\n\n"
            f"UNRECOGNIZABLE/INCOMPLETE (score 1-3):\n"
            f"- Just a line, scribble, or random marks = 1-2\n"
            f"- Cannot tell what it is = 1-3\n\n"
            f"KEY PRINCIPLES:\n"
            f"- CORRECT object + Good quality = 7-10 (reward good drawings!)\n"
            f"- CORRECT object + Poor quality = 4-6\n"
            f"- WRONG object = 1-4 (penalize wrong matches)\n"
            f"- Be FAIR: If it's the right object and recognizable, give 7-9\n"
            f"- Only give 10 for exceptional quality\n"
            f"- Don't be too harsh on correct objects - if recognizable, start at 7+\n\n"
            f"Return ONLY valid JSON: {{\"rating\": <1-10>}}"
        )
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ],
            max_tokens=150,
            temperature=0.2
        )
        
        # Extract rating from response
        text = resp.choices[0].message.content if resp.choices else ""
        print(f"OpenAI response: {text}")
        
        # Try to parse JSON
        rating = None
        m = re.search(r"\{[^{}]*\"rating\"[^{}]*:[^{}]*\d+[^{}]*\}", text, re.S)
        if m:
            try:
                parsed = json.loads(m.group(0))
                rating = int(parsed.get("rating", 0))
                rating = max(1, min(10, rating))
                print(f"Parsed rating from JSON: {rating}")
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                pass
        
        # Fallback: try to find a number 1-10 in text
        if rating is None:
            digits = re.findall(r"\b(10|[1-9])\b", text)
            if digits:
                rating = int(digits[0])
                print(f"Extracted rating from text: {rating}")
        
        if rating is None:
            print("Could not extract rating from response")
            return jsonify({
                'success': False,
                'error': f'Could not extract rating from response: {text[:200]}'
            }), 500
        
        print(f"Final rating: {rating}/10")
        
        return jsonify({
            'success': True,
            'rating': rating
        })
        
    except Exception as e:
        print(f"Error rating drawing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@minigame_bp.route('/twister_game/task')
def twister_game_task():
    """Get a random tongue twister"""
    result = get_twister_task()
    return jsonify(result)

@minigame_bp.route('/twister_game/submit', methods=['POST'])
def twister_game_submit():
    """Submit and score a tongue twister recording"""
    twist_id = request.form.get("twist_id")
    record = request.files.get("file")
    result, status_code = submit_twister_recording(twist_id, record)
    return jsonify(result), status_code

