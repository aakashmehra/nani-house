# Nani House

### A chaotic adventure combat board game on a 10×10 grid

Built using **Flask (Python)** + **HTML**, **CSS**, **JavaScript**, and **Socket.IO**.

Nani House is a hybrid **movement + combat** board game where players battle across a 10×10 board, rolling dice, fighting enemies, and using abilities.

This version uses **simple colored tiles purely for visuals**.
**Tile color does not affect gameplay.**

---

# Game Overview

* **Players:** 2–6
* **Board:** 10×10 = 100 tiles
* **Goal:**

  * Reach tile **100**, or
  * Be the **last player alive**
* **Actions per turn:** Roll, Attack, Ability, Items
* **No special tile effects** — colors are for board style only.

---

# Board System

### Board Layout

* 100 tiles arranged in a 10×10 snaking grid.
* Tiles are numbered **0 → 99**.
* The board features **colored tiles (Yellow, Green, Blue, Red, Beige)** for visual variation only.
* **No tile-based bonuses or penalties.**
* **Ladders** may be used (optional), allowing players to jump forward.
* **Snakes** may be added (optional), sending players backward.

Tile colors do **not** provide effects.

---

# Dice and Player Actions

Each turn, players choose **one** action:

### 1. Roll

* Roll a standard 6-sided dice.
* Move forward based on roll result.
* If ladders/snakes are enabled, movement will apply them.
* Colored tiles do not change movement.

Optional special dice (if added later):

* Double Roll Dice
* Lucky Roll Dice
* Teleport Dice
* Trap Skip Dice

---

### 2. Attack

* Players may attack if another player is within **range**.
* Range = tile distance between two players.
* Characters define `(min_range, max_range)`.

Damage rules:

* Attack reduces enemy health.
* Shield absorbs damage first (flat absorb value).

---

### 3. Ability

Each character has a **unique ability**.

Abilities may:

* Heal
* Move the player
* Deal enhanced damage
* Place traps
* Teleport
* Apply buffs

Abilities return a dict describing their effect for the backend to apply.

---

### 4. Items

Players may use items from inventory.

Examples:

* Healing items
* Shield boosts
* Extra roll
* Special dice
* Movement tools (escape rope, boosters)

Items are sold in shop or obtained via game modes.

---

# Characters

Characters are built to support tile-based distance combat.

Each character includes:

* Health
* Attack
* Shield (flat absorb)
* Range `(min_distance, max_distance)`
* A special ability

## Character List

| Character | Type       | Ability                                 |
| --------- | ---------- | --------------------------------------- |
| Ditte     | Support    | Heal self or nearby players             |
| Tontar    | Fighter    | Strong power strike                     |
| Makdi     | Trapster   | Place a trap on current tile            |
| Mishu     | Speedster  | Dash forward 2 tiles and damage on path |
| Dholky    | Tank       | Gain temporary shield                   |
| Beaster   | Berserker  | Increase attack for several turns       |
| Prepto    | Teleporter | Teleport to a specified tile            |
| Ishada    | Sniper     | Long-range high-damage shot             |
| Padupie   | Bomber     | Area-of-effect tile bombing             |

---

# Backend Project Structure

```
/nani_house
│
├── app.py
├── game_manager.py
├── board.py
├── socket_events.py
├── models.py
│
├── classes/
│   ├── characters.py
│   ├── dice.py
│   ├── items.py
│
├── templates/
│   ├── index.html
│   ├── game.html
│   ├── shop.html
│   └── lobby.html
│
└── static/
    ├── js/
    │   ├── game.js
    │   ├── board.js
    │   └── shop.js
    ├── css/
    │   ├── style.css
    │   └── board.css
    ├── img/
    ├── sfx/
    └── music/
```

---

# Gameplay Loop

1. Player turn starts
2. Choose one action: Roll, Attack, Ability, or Item
3. If Roll: move forward
4. Apply ladder/snake (if enabled)
5. If attack or ability used: resolve combat/effect
6. End turn → next player

---

# Shop System

Players earn coins by:

* Reaching milestones
* Winning fights
* Surviving rounds
* Rolling rare values
* Completing objectives (optional modes)

Shop may include:

* Special dice
* Health items
* Shield boosters
* Movement items
* Cosmetic skins
* Board themes

---

# Game Modes

### Classic Mode

First player to **tile 100** wins.

### Battle Mode

Players fight until one remains.

### Chaos Mode

Board layout (colors only) is randomized each round.
No bonus/penalty effects.

---

# Technical Notes

* Tile color is **purely visual**.
* Only ladders/snakes modify position, if enabled.
* All characters use tile-based distance for range.
* Shield uses **flat absorb**, not percentage.
* Abilities return a dict for the GameManager to apply.
* Backend supports multiple game rooms via Socket.IO.

---

# Version

**Nani House v1.0**
Board tiles are color-only, no tile effects.
# nani-house
