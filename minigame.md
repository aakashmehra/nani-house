# Nani House – Minigame Mechanics (v1.1)

This document describes the **four special minigames** currently included in Nani House.  
Each is tied to an item or board event and adds chaos, skill, and variety to gameplay.

---

# 1. Tongue-Twister Swap Minigame  
**Type:** Audio Skill Challenge  
**Trigger:** Using the **Swap Character** item

## Overview
When a player uses a Swap Character item, they must complete a fast audio challenge to execute the swap.

## Rules
- A tongue twister appears on the screen.  
- Player must **speak the phrase 3 times within 30 seconds**.  
- The voice recording is checked using OpenAI STT and tolerance-based matching.

## Outcome
- **Success:** Character Swap is performed.  
- **Failure:** Swap fails (item consumed or penalty applied).

---

# 2. Nani’s Gate – Drawing Test  
**Type:** Creative Drawing Challenge  
**Trigger:** Landing on a Gate Tile (randomly spawned)

## Overview
A special gate appears on a random tile. Any player landing on it must pass a drawing test to move past the gate.

## Rules
- Player gets a drawing prompt.  
- Draw for **30–60 seconds**.  
- OpenAI scores the drawing **1–10**.

## Outcome
- **Score ≥ 8:** Gate permanently opens for all players.  
- **Score < 8:** Player must retry on their next turn.

---

# 3. Guessing-Lock Curse  
**Type:** Word Puzzle / Turn-Lock Curse  
**Trigger:** Using a **Curse Item** on another player

## Overview
The cursed player is locked and must solve 3 words to regain their turns.

## Rules
- Player must solve **3 hidden words**.  
- **Correct letter:** reveal slots.  
- **Wrong letter:** keyboard disabled for **2 seconds**.  
- While cursed, normal turns are skipped.

## Outcome
- Curse ends only after all 3 words are solved.

---

# 4. Medicine Box Challenge  
**Type:** Logic Guess / Healing Reward  
**Trigger:** Landing on a **Healing Box Tile** or using a **Medicine Box Item**

## Overview
Player sees **5 different medicines** inside a box (icons or names).  
Only **3 of them are correct/healthy** choices.

## Rules
- Player must choose **3 medicines out of the 5**.  
- Each correct medicine grants **+15 HP**.  
- Each wrong medicine gives **0 HP** (or optional small penalty).

### Example:
- 2 correct → +30 HP  
- 3 correct → +45 HP  
- 0 correct → no heal

## Outcome
- Immediate HP increase is applied.  
- Perfect selection can optionally trigger a small bonus (e.g., +5 shield).

## Design Notes
- Quick and fun, no slowdown.  
- Light puzzle that rewards knowledge or luck.  
- Works great on both mobile and desktop.

---

# End of Document  
Nani House – Chaos meets strategy on a 10×10 battlefield.
