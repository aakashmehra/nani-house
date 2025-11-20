# twister_game.py - Tongue Twister game logic and functions
import os
import re
import tempfile
import random
from datetime import datetime, timedelta
from flask import request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# OpenAI client setup
API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client: {e}")

# Tongue twister pool
TWISTERS = [
    "She sells seashells by the seashore",
    "Peter Piper picked a peck of pickled peppers",
    "How much wood would a woodchuck chuck if a woodchuck could chuck wood",
    "I scream you scream, we all scream for ice cream",
    "Six slippery snails slid slowly seaward",
    "Black background brown background",
    "Unique New York",
    "Red lorry yellow lorry",
    "Fuzzy Wuzzy was a bear"
]

# Active twisters: id -> {text, expires_at}
ACTIVE_TWISTERS = {}

# Helper functions for twister game
def normalize_text(s):
    """Normalize text: lowercase, remove punctuation (including periods and commas), collapse spaces"""
    if not s:
        return ""
    s = str(s).lower()
    # Remove periods and commas specifically first
    s = s.replace('.', ' ').replace(',', ' ')
    # Remove all other punctuation and special characters
    s = re.sub(r"[^\w\s]", " ", s)
    # Collapse multiple spaces into single space
    s = re.sub(r"\s+", " ", s).strip()
    return s

def levenshtein(a, b):
    """Calculate Levenshtein distance between two strings"""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            insert_cost = cur[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (0 if ca == cb else 1)
            cur[j] = min(insert_cost, delete_cost, replace_cost)
        prev = cur
    return prev[-1]

def count_repetitions(target_norm, trans_norm):
    """Count how many times the target phrase appears in the transcript - IMPROVED VERSION"""
    if not target_norm or not trans_norm:
        return 0
    
    t_words = target_norm.split()
    trans_words = trans_norm.split()
    
    if len(t_words) == 0 or len(trans_words) == 0:
        return 0
    
    w = len(t_words)
    
    # Method 1: Simple exact match counting (for perfect repetitions)
    # Split transcript into segments and check each
    count_exact = 0
    i = 0
    while i <= len(trans_words) - w:
        segment = " ".join(trans_words[i:i+w])
        if segment == target_norm:
            count_exact += 1
            i += w  # Skip ahead by phrase length
        else:
            i += 1
    
    if count_exact >= 3:
        return 3
    
    # Method 2: Fuzzy matching with sliding window
    similarity_threshold = 0.7  # 70% similarity threshold
    min_words_needed = max(1, int(w * 0.6))  # Need at least 60% of words
    
    count_fuzzy = 0
    i = 0
    last_match_end = -1
    
    while i < len(trans_words) - min_words_needed + 1:
        best_match = None
        best_sim = 0
        best_len = 0
        
        # Check segments of different lengths (w to w+5 words)
        for seg_len in range(w, min(w + 6, len(trans_words) - i + 1)):
            if i + seg_len > len(trans_words):
                break
            
            segment_words = trans_words[i:i+seg_len]
            segment_text = " ".join(segment_words)
            
            # Calculate similarity using Levenshtein distance
            dist = levenshtein(target_norm, segment_text)
            max_len = max(len(target_norm), len(segment_text))
            if max_len == 0:
                continue
            sim = 1 - (dist / max_len)
            
            # Check word overlap
            target_words_set = set(t_words)
            segment_words_set = set(segment_words)
            word_overlap = len(target_words_set & segment_words_set) / len(target_words_set) if len(target_words_set) > 0 else 0
            
            # Combined similarity (50% levenshtein, 50% word overlap)
            combined_sim = (sim * 0.5) + (word_overlap * 0.5)
            
            if combined_sim > best_sim:
                best_sim = combined_sim
                best_match = i
                best_len = seg_len
        
        # If we found a good match, count it
        if best_sim >= similarity_threshold and best_match is not None:
            # Don't count if it overlaps too much with previous match
            if best_match >= last_match_end or last_match_end == -1:
                count_fuzzy += 1
                last_match_end = best_match + best_len
                i = last_match_end  # Jump ahead
            else:
                i += 1
        else:
            i += 1
    
    # Method 3: Word frequency analysis (for cases where transcript is 3x longer)
    count_frequency = 0
    if len(trans_norm) >= len(target_norm) * 2.0:  # Transcript is at least 2x longer
        # Count how many times each target word appears
        target_word_counts = {word: trans_words.count(word) for word in set(t_words)}
        if target_word_counts:
            # Average occurrences per word
            avg_occurrences = sum(target_word_counts.values()) / len(t_words)
            # Estimate repetitions: if words appear ~3x on average, likely 3 repetitions
            # But be conservative - only count if it's clearly multiple repetitions
            if avg_occurrences >= 2.0:  # Words appear at least 2x on average
                # Estimate based on ratio
                estimated_reps = min(3, int(avg_occurrences))
                count_frequency = max(1, estimated_reps)
    
    # Method 4: Length-based estimation (very lenient fallback)
    count_length = 0
    if len(trans_norm) >= len(target_norm) * 2.5:
        # Transcript is significantly longer - likely multiple repetitions
        length_ratio = len(trans_norm) / len(target_norm) if len(target_norm) > 0 else 0
        if length_ratio >= 2.5:
            # Estimate 3 repetitions if transcript is 2.5-3.5x longer
            if length_ratio <= 3.5:
                count_length = 3
            else:
                # More than 3.5x - might be more, but cap at 3
                count_length = 3
    
    # Return the maximum count from all methods (but cap at 3)
    final_count = max(count_exact, count_fuzzy, count_frequency, count_length)
    
    # Special case: if transcript is very similar overall and longer, assume repetitions
    if final_count < 3:
        overall_dist = levenshtein(target_norm, trans_norm)
        overall_max_len = max(len(target_norm), len(trans_norm))
        if overall_max_len > 0:
            overall_sim = 1 - (overall_dist / overall_max_len)
            length_ratio = len(trans_norm) / len(target_norm) if len(target_norm) > 0 else 0
            
            # If similarity is very high (>= 0.9) and transcript is 2x+ longer, likely multiple repetitions
            if overall_sim >= 0.9 and length_ratio >= 2.0:
                # Estimate based on length ratio
                if length_ratio >= 2.5:
                    final_count = 3
                elif length_ratio >= 2.0:
                    final_count = 2
            # If similarity is good (>= 0.7) and transcript is 2.5x longer, assume 3 repetitions
            elif overall_sim >= 0.7 and length_ratio >= 2.5:
                final_count = 3
    
    return min(final_count, 3)  # Cap at 3 repetitions max

def get_twister_task():
    """Get a random tongue twister"""
    tw = random.choice(TWISTERS)
    tid = str(random.randrange(10**9))
    # Normalize the tongue twister before storing (lowercase, remove periods and commas)
    tw_normalized = normalize_text(tw)
    ACTIVE_TWISTERS[tid] = {
        "text": tw,  # Keep original for display
        "text_normalized": tw_normalized,  # Store normalized version for comparison
        "expires_at": datetime.utcnow() + timedelta(minutes=5)
    }
    return {"id": tid, "twist": tw}

def submit_twister_recording(twist_id, audio_file):
    """Submit and score a tongue twister recording"""
    if not client:
        return {
            'error': 'OpenAI API not configured'
        }, 500
    
    try:
        if not twist_id or twist_id not in ACTIVE_TWISTERS:
            return {"error": "invalid or missing twist_id"}, 400
        
        if not audio_file:
            return {"error": "file required"}, 400
        
        info = ACTIVE_TWISTERS.get(twist_id)
        if datetime.utcnow() > info["expires_at"]:
            return {"error": "twister expired"}, 400
        
        target = info["text"]
        # Use normalized version if available, otherwise normalize on the fly
        target_normalized = info.get("text_normalized") or normalize_text(target)
        
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tf:
            audio_file.save(tf.name)
            tmpname = tf.name
        
        # Transcribe using OpenAI Whisper
        try:
            with open(tmpname, "rb") as af:
                resp = client.audio.transcriptions.create(
                    file=af,
                    model="whisper-1"
                )
            transcript = resp.get("text") if isinstance(resp, dict) else getattr(resp, "text", "")
            transcript = transcript or ""
        except Exception as e:
            transcript = ""
            return {"error": "transcription_failed", "detail": str(e)}, 500
        finally:
            try:
                os.unlink(tmpname)
            except Exception:
                pass
        
        # Normalize transcript (target already normalized when stored)
        n_target = target_normalized
        n_trans = normalize_text(transcript)
        
        # Calculate similarity via Levenshtein distance
        dist = levenshtein(n_target, n_trans)
        maxlen = max(len(n_target), len(n_trans)) if max(len(n_target), len(n_trans)) > 0 else 1
        similarity = 1 - (dist / maxlen)
        similarity = round(max(0.0, min(1.0, similarity)), 3)
        
        # Count repetitions
        reps = count_repetitions(n_target, n_trans)
        
        # Calculate score out of 10 - NEW SCORING LOGIC
        # Priority: 3 repetitions = minimum score 6, then scale by similarity
        score = 0
        
        if reps >= 3:
            # 3 repetitions = minimum score 6, scale up with similarity
            if similarity > 0.9:
                score = 10  # Above 90% → 10
            elif similarity >= 0.9:
                score = 9   # 90% → 9
            elif similarity >= 0.7:
                score = 8   # 70% → 8
            elif similarity >= 0.5:
                score = 7   # 50% → 7
            elif similarity >= 0.3:
                score = 6   # 30% → 6 (minimum for 3 reps)
            else:
                score = 6   # Still give 6 for 3 repetitions even if similarity < 30%
        elif reps >= 2:
            # 2 repetitions - scale by similarity (lower scores)
            if similarity >= 0.9:
                score = 8
            elif similarity >= 0.7:
                score = 7
            elif similarity >= 0.5:
                score = 6
            elif similarity >= 0.3:
                score = 5
            else:
                score = 4
        elif reps >= 1:
            # 1 repetition - scale by similarity (even lower)
            if similarity >= 0.9:
                score = 7
            elif similarity >= 0.7:
                score = 6
            elif similarity >= 0.5:
                score = 5
            elif similarity >= 0.3:
                score = 4
            else:
                score = 3
        else:
            # No repetitions - scale by similarity only (lowest scores)
            if similarity >= 0.9:
                score = 6
            elif similarity >= 0.7:
                score = 5
            elif similarity >= 0.5:
                score = 4
            elif similarity >= 0.3:
                score = 3
            else:
                score = 2
        
        # Verdict
        if similarity >= 0.85 and reps >= 3:
            verdict = "Perfect"
        elif similarity >= 0.65 and reps >= 2:
            verdict = "Good"
        else:
            verdict = "Try Again"
        
        return {
            "target": target,
            "transcript": transcript,
            "normalized_transcript": n_trans,
            "normalized_target": n_target,
            "similarity": similarity,
            "repetitions_detected": reps,
            "score": score,
            "verdict": verdict
        }, 200
        
    except Exception as e:
        print(f"Error in twister game submit: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e)
        }, 500
