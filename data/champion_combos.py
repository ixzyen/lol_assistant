"""
Combo damage definitions for the kill calculator.
Each entry defines the burst/full combo damage components.

damage_components: list of damage sources in the combo.
  - 'base':  flat base damage of the ability at given rank
  - 'ad_ratio': multiplier of total AD
  - 'ap_ratio': multiplier of AP (usually 0 for AD junglers)
  - 'type':  'physical' | 'magic' | 'true'
  - 'label': human-readable ability name

spell_order: suggested hotkey sequence shown in overlay.
"""

CHAMPION_COMBOS = {
    "khazix": {
        "combo_label": "E → Q (isolated) → W → AA",
        "spell_order":  "E > Q > W > AA",
        "damage_components": [
            # Q - Taste Their Fear (isolated bonus)
            {"label": "Q isolated",  "base": [70, 95, 120, 145, 170],
             "ad_ratio": 1.15, "type": "physical", "rank_index": "q"},
            # W - Void Spike
            {"label": "W spike",     "base": [85, 115, 145, 175, 205],
             "ad_ratio": 1.0,  "type": "physical", "rank_index": "w"},
            # E - Leap
            {"label": "E leap",      "base": [65, 100, 135, 170, 205],
             "ad_ratio": 0.2,  "type": "physical", "rank_index": "e"},
            # AA
            {"label": "AA",          "base": [0],
             "ad_ratio": 1.0,  "type": "physical", "rank_index": None},
        ],
    },

    "jarvaniv": {
        "combo_label": "E+Q → W → AA → R",
        "spell_order":  "E+Q > W > AA > R (to trap)",
        "damage_components": [
            # Q - Dragon Strike
            {"label": "Q knockup",   "base": [80, 130, 180, 230, 280],
             "ad_ratio": 1.4, "type": "physical", "rank_index": "q"},
            # E flag (no damage by itself - used for setup)
            # W - Golden Aegis (no direct damage)
            # R - Cataclysm
            {"label": "R Cataclysm", "base": [150, 250, 350],
             "ad_ratio": 1.5, "type": "physical", "rank_index": "r"},
            # AA
            {"label": "AA",          "base": [0],
             "ad_ratio": 1.0,  "type": "physical", "rank_index": None},
        ],
    },

    "briar": {
        "combo_label": "Q → W (frenzy) → E → W recast",
        "spell_order":  "Q > W > E (charged) > W recast",
        "damage_components": [
            # Q - Head Rush (stun + armor shred)
            {"label": "Q stun",      "base": [60, 85, 110, 135, 160],
             "ad_ratio": 0.8,  "type": "physical", "rank_index": "q"},
            # W - Blood Frenzy autos (3 autos approximated)
            {"label": "W autos x3",  "base": [0],
             "ad_ratio": 3.0,  "type": "physical", "rank_index": None},
            # E - Chilling Scream (max charge)
            {"label": "E max charge","base": [140, 215, 290, 365, 440],
             "ad_ratio": 2.4,  "type": "magic",    "rank_index": "e"},
        ],
    },

    "warwick": {
        "combo_label": "Q → R (suppress) → autos",
        "spell_order":  "R > Q > autos",
        "damage_components": [
            # Q - Jaws of the Beast
            {"label": "Q bite",      "base": [0],
             "ad_ratio": 0,   "hp_ratio": 0.06, "type": "magic", "rank_index": "q"},
            # R - Infinite Duress (3 hits)
            {"label": "R suppress",  "base": [175, 350, 525],
             "ad_ratio": 2.5,  "type": "magic", "rank_index": "r"},
            # Autos x3
            {"label": "autos x3",    "base": [0],
             "ad_ratio": 3.0,  "type": "physical", "rank_index": None},
        ],
    },

    "nocturne": {
        "combo_label": "R → AA → Q → E (fear) → AA",
        "spell_order":  "R > AA > Q > E > AA",
        "damage_components": [
            # Q - Duskbringer trail autos + Q hit
            {"label": "Q",           "base": [65, 110, 155, 200, 245],
             "ad_ratio": 0.85, "type": "physical", "rank_index": "q"},
            # Passive - Umbra Blades (every 10s, roughly 1 proc per combo)
            {"label": "Passive proc","base": [0],
             "ad_ratio": 1.2,  "type": "physical", "rank_index": None},
            # Autos x2
            {"label": "AAs x2",      "base": [0],
             "ad_ratio": 2.0,  "type": "physical", "rank_index": None},
        ],
    },

    "masteryi": {
        "combo_label": "Q (4 strikes) → autos → E (true dmg)",
        "spell_order":  "Q > E > autos",
        "damage_components": [
            # Q - Alpha Strike (4 hits, one target)
            {"label": "Q Alpha x4",  "base": [25, 60, 95, 130, 165],
             "ad_ratio": 4 * 0.9, "type": "physical", "rank_index": "q"},
            # E - Wuju Style true damage autos (3)
            {"label": "E true dmg x3", "base": [0],
             "ad_ratio": 3 * 0.1, "type": "true",    "rank_index": None},
            # Autos x3 (Highlander haste)
            {"label": "AAs x3",      "base": [0],
             "ad_ratio": 3.0,  "type": "physical", "rank_index": None},
        ],
    },

    "vi": {
        "combo_label": "Q → AA → W procs → R → AA",
        "spell_order":  "Q > AA > R > AA",
        "damage_components": [
            # Q - Vault Breaker (max charge)
            {"label": "Q max charge","base": [55, 80, 105, 130, 155],
             "ad_ratio": 1.7,  "type": "physical", "rank_index": "q"},
            # R - Assault and Battery
            {"label": "R",           "base": [150, 325, 500],
             "ad_ratio": 1.4,  "type": "physical", "rank_index": "r"},
            # AAs x2 with W proc
            {"label": "AAs+W x2",    "base": [0],
             "ad_ratio": 2.0,  "type": "physical", "rank_index": None},
        ],
    },

    # Default fallback for unknown champions
    "_default": {
        "combo_label": "Full combo",
        "spell_order":  "Spell1 > Spell2 > AA",
        "damage_components": [
            {"label": "Estimated combo", "base": [300],
             "ad_ratio": 2.5, "type": "physical", "rank_index": None},
        ],
    },
}


def get_combo(champion_name: str) -> dict:
    key = (champion_name.lower()
           .replace("'", "")
           .replace(" ", "")
           .replace(".", ""))
    return CHAMPION_COMBOS.get(key, CHAMPION_COMBOS["_default"])


# Spell rank lookup helpers
RANK_INDEX_MAP = {"q": 0, "w": 1, "e": 2, "r": 3}

def get_base_damage_at_rank(component: dict, spell_ranks: dict) -> float:
    """Return base damage for ability at current rank."""
    idx_key = component.get("rank_index")
    if idx_key is None:
        return component["base"][0] if component["base"] else 0
    rank = spell_ranks.get(idx_key, 1)
    base_list = component["base"]
    rank_idx = min(rank - 1, len(base_list) - 1)
    return base_list[rank_idx]
