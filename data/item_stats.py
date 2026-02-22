"""
Item stats relevant to kill calculator.
Covers: armor, MR, HP (for enemy effective HP),
        active damage (for your combo),
        shield items (for enemy effective HP flags).
"""

# --- Enemy defensive items ---
# These add to enemy's effective HP in the calculator.

ITEM_STATS = {
    # Armor items
    "thornmail":            {"armor": 60,  "hp": 350},
    "randuins_omen":        {"armor": 80,  "hp": 400},
    "frozen_heart":         {"armor": 90,  "hp": 0},
    "iceborn_gauntlet":     {"armor": 50,  "hp": 300},
    "jak_sho":              {"armor": 30,  "hp": 300, "mr": 30},
    "kaenic_rookern":       {"mr": 80,     "hp": 350},
    "spirit_visage":        {"mr": 60,     "hp": 450},
    "force_of_nature":      {"mr": 70,     "hp": 350},
    "warmogs_armor":        {"hp": 1000},
    "heartsteel":           {"hp": 800,    "armor": 0},
    "gargoyle_stoneplate":  {"armor": 60,  "mr": 60,  "hp": 150,
                             "active_shield": 0.40},  # +40% max HP shield on active
    "sterak_gage":          {"hp": 400,
                             "passive_shield": 0.20},  # 20% max HP shield on low HP
    "immortal_shieldbow":   {"hp": 250,
                             "passive_shield": 275},   # flat shield
    "guardian_angel":       {"armor": 40,  "revive": True},
    "deaths_dance":         {"armor": 45,  "hp": 0,
                             "damage_delay": 0.30},    # 30% dmg delayed = partial mitigation
    "black_cleaver":        {"hp": 400,    "armor": 0},
    "sundered_sky":         {"hp": 350,    "armor": 0},
    "titanic_hydra":        {"hp": 600,    "armor": 0},
    "maw_of_malmortius":    {"mr": 50,
                             "passive_shield": 200},   # flat magic shield
    "edge_of_night":        {"hp": 250,    "armor": 0,
                             "passive_shield": "spell"},
    "hollow_radiance":      {"hp": 350,    "mr": 50},
    "abyssal_mask":         {"hp": 500,    "mr": 0},
    "blade_of_the_ruined_king": {"hp": 0},
    "trinity_force":        {"hp": 200},
    "stridebreaker":        {"hp": 300},
    "ravenous_hydra":       {"hp": 0},
    "profane_hydra":        {"hp": 0},
    "serpents_fang":        {"hp": 0},
    "lord_dominiks_regards": {"hp": 0},
    "mortal_reminder":      {"hp": 0},
    "the_collector":        {"hp": 0},
    "infinity_edge":        {"hp": 0},
    "kraken_slayer":        {"hp": 0},
}

# --- Active damage items (YOUR items) ---
# damage field = flat damage added to combo. level-scaled where relevant.

ACTIVE_DAMAGE_ITEMS = {
    "galeforce":        {"damage": 150,  "type": "physical", "note": "dash + damage"},
    "hextech_rocketbelt": {"damage": 125, "type": "magic",   "note": "dash"},
    "youmuus_ghostblade": {"damage": 0,  "type": "none",     "note": "+MS only"},
    "the_collector":    {"damage": 0,    "type": "execute",
                         "note": "executes below 5% HP - flag only"},
}

# --- Summoner spell effective HP modifiers ---
SUMMONER_ADJUSTMENTS = {
    "SummonerBarrier":  {"hp_modifier": 1.25, "label": "Barrier"},
    "SummonerHeal":     {"hp_modifier": 1.18, "label": "Heal"},
    "SummonerShield":   {"hp_modifier": 1.15, "label": "Ignite(no adj)"},
    "SummonerExhaust":  {"my_dmg_modifier": 0.60, "label": "Exhaust"},
}

# --- Keystone rune adjustments ---
RUNE_ADJUSTMENTS = {
    "Grasp of the Undying": {"hp_modifier": 1.05},
    "Conqueror":            {"my_dmg_modifier": 1.08,   # rough avg stacks
                             "enemy_healing": 0.08},
    "Phase Rush":           {"note": "escape tool - reduce kill confidence"},
    "Lethal Tempo":         {"note": "sustained DPS - less relevant for burst"},
}


def get_item_stats(item_name: str) -> dict:
    """Normalize item name and return stats dict."""
    key = (item_name.lower()
           .replace("'", "")
           .replace(" ", "_")
           .replace("-", "_"))
    return ITEM_STATS.get(key, {})


def get_active_damage(item_name: str) -> dict:
    key = (item_name.lower()
           .replace("'", "")
           .replace(" ", "_"))
    return ACTIVE_DAMAGE_ITEMS.get(key, {})
