"""
Champion base stats - armor, MR, HP per level.
Source: community-dragon / League wiki (patch 26.x)
Add more champions as needed.
"""

CHAMPION_STATS = {
    # Junglers you'll face most often
    "belveth": {
        "base_armor": 21, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 640, "hp_per_level": 105,
    },
    "khazix": {
        "base_armor": 21, "armor_per_level": 4.2,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 585, "hp_per_level": 100,
    },
    "jarvaniv": {
        "base_armor": 36, "armor_per_level": 4.6,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 592, "hp_per_level": 100,
    },
    "vi": {
        "base_armor": 33, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 613, "hp_per_level": 95,
    },
    "nocturne": {
        "base_armor": 33, "armor_per_level": 4.2,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 582, "hp_per_level": 85,
    },
    "warwick": {
        "base_armor": 33, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 653, "hp_per_level": 99,
    },
    "masteryi": {
        "base_armor": 33, "armor_per_level": 3.5,
        "base_mr": 32, "mr_per_level": 1.25,
        "base_hp": 654, "hp_per_level": 99,
    },
    "ekko": {
        "base_armor": 24, "armor_per_level": 4.2,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 655, "hp_per_level": 109,
    },
    "elise": {
        "base_armor": 24, "armor_per_level": 4.0,
        "base_mr": 32, "mr_per_level": 1.25,
        "base_hp": 553, "hp_per_level": 92,
    },
    "briar": {
        "base_armor": 26, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 645, "hp_per_level": 114,
    },
    "graves": {
        "base_armor": 30, "armor_per_level": 4.0,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 570, "hp_per_level": 95,
    },
    "xinzhao": {
        "base_armor": 33, "armor_per_level": 4.2,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 600, "hp_per_level": 100,
    },
    "reksai": {
        "base_armor": 36, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 575, "hp_per_level": 85,
    },
    "fiddlesticks": {
        "base_armor": 21, "armor_per_level": 4.0,
        "base_mr": 40, "mr_per_level": 2.05,
        "base_hp": 580, "hp_per_level": 102,
    },
    "shaco": {
        "base_armor": 21, "armor_per_level": 3.5,
        "base_mr": 32, "mr_per_level": 1.25,
        "base_hp": 560, "hp_per_level": 90,
    },
    "viego": {
        "base_armor": 33, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 600, "hp_per_level": 100,
    },
    "hecarim": {
        "base_armor": 31, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 593, "hp_per_level": 93,
    },
    # Laners you'll often 1v1 in a gank
    "darius": {
        "base_armor": 39, "armor_per_level": 4.0,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 650, "hp_per_level": 114,
    },
    "kayle": {
        "base_armor": 26, "armor_per_level": 4.0,
        "base_mr": 32, "mr_per_level": 1.25,
        "base_hp": 610, "hp_per_level": 103,
    },
    "veigar": {
        "base_armor": 18, "armor_per_level": 4.0,
        "base_mr": 30, "mr_per_level": 0.5,
        "base_hp": 550, "hp_per_level": 104,
    },
    "lucian": {
        "base_armor": 28, "armor_per_level": 4.7,
        "base_mr": 30, "mr_per_level": 0.5,
        "base_hp": 600, "hp_per_level": 95,
    },
    "nautilus": {
        "base_armor": 46, "armor_per_level": 4.7,
        "base_mr": 32, "mr_per_level": 2.05,
        "base_hp": 648, "hp_per_level": 109,
    },
    "malzahar": {
        "base_armor": 19, "armor_per_level": 4.0,
        "base_mr": 30, "mr_per_level": 0.5,
        "base_hp": 580, "hp_per_level": 95,
    },
    "aphelios": {
        "base_armor": 21, "armor_per_level": 4.2,
        "base_mr": 30, "mr_per_level": 0.5,
        "base_hp": 530, "hp_per_level": 92,
    },
    # Generic fallback values
    "_default": {
        "base_armor": 28, "armor_per_level": 4.0,
        "base_mr": 32, "mr_per_level": 1.5,
        "base_hp": 580, "hp_per_level": 95,
    },
}


def get_champion_stats(champion_name: str) -> dict:
    """Return base stats for champion. Falls back to _default if unknown."""
    key = champion_name.lower().replace("'", "").replace(" ", "").replace(".", "")
    return CHAMPION_STATS.get(key, CHAMPION_STATS["_default"])


def calculate_stats_at_level(champion_name: str, level: int) -> dict:
    """Calculate champion's total base stats at a given level."""
    stats = get_champion_stats(champion_name)
    lvl = max(1, min(18, level))
    return {
        "armor": stats["base_armor"] + stats["armor_per_level"] * (lvl - 1),
        "mr":    stats["base_mr"]    + stats["mr_per_level"]    * (lvl - 1),
        "max_hp": stats["base_hp"]   + stats["hp_per_level"]    * (lvl - 1),
    }
