# LoL Kill Calculator Assistant

> ⚠️ **Very early stage project (v0.1 — Alpha)**
> Actively under development. The current implementation works stably with Kha'Zix as the player's champion, with a base database of ~26 enemy champions. The champion database, damage model and OCR pipeline will be significantly expanded in upcoming phases.

A real-time overlay for League of Legends displaying kill confidence — the probability of killing a target — based on the player's live stats, spell ranks and enemy HP, without modifying any game files.

---

## How it works

```
Riot Live Client API  ──►  player stats (AD, AP, HP%, level, items, spell ranks)
                                          │
OCR from top-left target panel  ──►  enemy HP/mana in real time
                                          │
Static database  ──►  enemy base HP / armor / MR per level
                                          │
                              Kill Calculator
                                          │
                         Overlay: GO / RISKY / NO GO  +  confidence %
```

The main loop runs every ~300ms. No game file modification or process memory access required.

---

## System requirements

- **Windows 10/11** (required by Riot Live Client API)
- **Python 3.10+**
- **League of Legends** running (API is only available during an active game)
- **Tesseract OCR** — separate installation required (see below)
- Resolution: OCR coordinates calibrated for **2560x1440**. Other resolutions require recalibration (see Calibration section)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/lol_assistant.git
cd lol-kill-calculator
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` includes:

```
requests>=2.31.0
keyboard>=0.13.5
mss>=9.0.1
opencv-python>=4.9.0
psutil>=5.9.0
numpy>=1.26.0
pytesseract>=0.3.10
Pillow>=10.0.0
```

### 3. Install Tesseract OCR

Download the Windows installer from:
**https://github.com/UB-Mannheim/tesseract/wiki**

Install to the default location:
```
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If you install to a different path, update the path in `modules/target_panel_reader.py`:

```python
pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"
```

### 4. Verify installation

```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

You should see a version number (e.g. `5.3.x`). An error means the Tesseract path is incorrect.

---

## Running

```bash
python main.py
```

Launch **during an active game** — the app automatically detects whether League of Legends is running.

### Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+F1` | Toggle calculator on / off |
| `Ctrl+F2` | Show / hide overlay |
| `Ctrl+F3` | Quit |

### Target lock

The calculator tracks a single enemy champion at a time. On startup it automatically locks onto the first enemy detected in the player list. To switch targets, use `Ctrl+F1` to cycle through available enemies — the current target is shown in the overlay and debug logs as `Target: ChampionName`.

Locking onto a specific target is intentional: it prevents the overlay from flickering between multiple enemies during teamfights and keeps the confidence reading stable.

---

## Reading the output

| Result | Threshold | Meaning |
|--------|-----------|---------|
| 🟢 **GO** | >= 75% | High kill probability — engaging is favourable |
| 🟡 **RISKY** | 50-74% | Situational — consider map state before engaging |
| 🔴 **NO GO** | < 50% | Insufficient damage — avoid the fight |
| ⏸️ **PAUSED** | HP = 0% | Player is dead / respawning |

Confidence is capped at 97% — this reflects irreducible execution uncertainty (ping, reaction time, enemy active items such as Zhonya's or Stopwatch).

---

## Prerequisites for accurate calculation

The kill confidence calculation always runs, but its accuracy depends on two conditions being met:

**1. You must click on the enemy champion in-game.**
Clicking causes the target panel to appear in the top-left corner of the screen. This panel is the only source of real-time enemy HP and stats. Without it, the calculator falls back to assuming the enemy is at full HP and uses estimated base stats — the result is still shown but is significantly less accurate, especially mid- and late-game.

**2. The enemy must be visible (not in fog of war).**
When the enemy goes out of vision, the target panel disappears. The calculator then falls back to the last cached HP reading. The longer the enemy is out of vision, the more stale and unreliable that cached value becomes. This is reflected in the fallback chain: OCR → last cached reading → assume full HP.

---

## OCR — reading enemy HP

To use the enemy's **actual current HP** instead of assuming 100%:

1. Click on the enemy champion in-game (the target panel appears in the top-left corner)
2. Keep the panel visible — the app reads it automatically every ~300ms
3. Logs will show: `panel=on | HP=327/705`

Without clicking: the calculator assumes full HP (worst case — reduces false GO signals).

### Calibrating OCR for a different resolution

If you are playing at a resolution other than 2560x1440:

```bash
python -c "
import mss
from modules.target_panel_reader import calibrate_target_panel
calibrate_target_panel(mss.mss())
"
```

Run this with an enemy clicked so the target panel is visible. Check the console output and the saved `target_panel_calibration.png`. If the OCR reads incorrect values, adjust `_HP_REGION` and `_MP_REGION` coordinates in `modules/target_panel_reader.py`.

---

## Project structure

```
lol-kill-calculator/
│
├── main.py                        # Entry point, main loop, hotkey handling
│
├── modules/
│   ├── live_client.py             # Riot Live Client API — player stats
│   ├── kill_calculator.py         # Kill confidence mathematical model
│   ├── overlay.py                 # Tkinter screen overlay
│   ├── target_panel_reader.py     # OCR — enemy HP/mana from target panel
│   └── screen_reader.py           # Screen capture utilities
│
├── data/
│   ├── champion_stats.py          # Database: base HP, armor, MR per champion
│   ├── champion_combos.py         # Combo sequences and damage models per champion
│   └── item_stats.py              # HP/armor/MR bonuses from items
│
├── requirements.txt
└── README.md
```

---

## Supported champions (Phase I)

### As the player (damage model implemented)

| Champion | Type | Status |
|----------|------|--------|
| Kha'Zix | AD Assassin | ✅ Full model including isolation bonus |

### As the enemy (stat database)

The database covers ~26 champions. All others fall back to default values (580 base HP), which may introduce up to a 20-40% HP error for unlisted champions.

Champions with full stats include: Sona, Jinx, Lux, Caitlyn, Ashe, Ezreal, Leona, Thresh, Blitzcrank, Alistar, Zed, Yasuo, Akali, Katarina, Diana, Talon, LeBlanc, Ahri, Syndra, Orianna, Lissandra, Ziggs, Veigar, Annie, Cassiopeia and others.

> **Not yet in the database:** Xerath (planned for Phase 1.5), most recently released champions. Pull requests welcome!

---

## Known limitations (Phase I)

| Issue | Impact | Plan |
|-------|--------|------|
| Champion database ~26 entries | Up to 40% HP error for the rest | Phase II — DataDragon API |
| Enemy armor/MR — database only, no OCR | Up to 20% eff-HP error | Phase 1.5 — OCR from target panel |
| Damage model — Kha'Zix only | No support for other player champions | Phase 1.5 — Xerath; Phase II — more |
| Runes not included in damage model | Up to 40% undercount on squishes | Phase II |
| HP bar colour detection — disabled | Do not click allied champions | Phase II |
| Enemy defensive items — incomplete | Up to 300 HP error late game | Phase II |
| Fog of war — panel disappears | Falls back to stale cached HP | Cache TTL + decay in Phase II |
| Click required for accurate HP | Full HP assumed without panel | Fundamental — no workaround without API |

---

## Roadmap

### Phase 1.5 (current)
- [ ] Xerath — full damage model (AP mage)
- [ ] OCR for enemy armor and MR from the top-left target panel
- [ ] Ultrawide / 4K resolution support (coordinate calibration per resolution)
- [ ] Alpha testing with a second player on a 4K ultrawide display

### Phase II
- [ ] **Riot DataDragon API integration** — automatic champion and item stat updates after every patch, eliminating manual database maintenance
- [ ] Spell damage reading via tooltip OCR (hover over spell → read base damage value)
- [ ] Player runes in the damage model (Electrocute, Dark Harvest, Arcane Comet)
- [ ] True damage as a separate damage category
- [ ] Cooldown tracking — whether spells are currently available
- [ ] GUI (PyQt6) to replace the terminal — architecture already supports this without rewriting core logic
- [ ] GO/RISKY/NO GO threshold calibration based on historical fight outcome data

---

## Architecture — design decisions

**Why single-threaded?** At a 300ms tick rate multithreading provides no meaningful benefit and significantly increases code complexity. Logic is already decoupled from the presentation layer, making future GUI migration straightforward.

**Why OCR instead of memory reading?** Memory reading (Cheat Engine style) violates Riot's Terms of Service and risks account bans. OCR reads only what is visible on screen — the same information available to any player.

**Why fall back to 1.0 HP when OCR fails?** A pessimistic worst case reduces false GO signals. It is better for the tool to be cautious than to encourage unnecessary aggression.

**Why cap at 97%?** There is never 100% certainty — ping, reaction time, Zhonya's Hourglass, model inaccuracy and other factors always introduce residual risk.

<<<<<<< Updated upstream
Full mathematical documentation of the model : [`docs/lol_methodology_en.docx`](docs/lol_methodology_en.docx)
=======
>>>>>>> Stashed changes

Full mathematical documentation of the model : [`docs/lol_methodology_en.docx`](docs/lol_methodology_en.docx)
---

## Contributing

The project is in early development — any pull request is welcome, especially:

- Champion stat entries in `data/champion_stats.py` — format is straightforward, stats can be sourced from the LoL wiki
- Damage models for new champions in `data/champion_combos.py`
- Testing on resolutions other than 2560x1440

---

## Disclaimer

This project is an educational and research tool. It uses only the official Riot Live Client API (a local endpoint requiring no API key) and screen reading — it does not modify game files or access process memory. Use at your own risk.

League of Legends is the property of Riot Games. This project is not affiliated with or endorsed by Riot Games.
