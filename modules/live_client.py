"""
Live Client Data API module.
Riot's local API runs at https://127.0.0.1:2999 during active games.
No authentication required - local only.
"""

import requests
import urllib3
import logging
from typing import Optional

# Suppress SSL warnings for self-signed Riot cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://127.0.0.1:2999/liveclientdata"
TIMEOUT = 2.0  # seconds

logger = logging.getLogger(__name__)


def _get(endpoint: str) -> Optional[dict | list]:
    """Raw GET request to Live Client API."""
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", verify=False, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        logger.debug("Live Client API not available (game not running?)")
        return None
    except requests.exceptions.Timeout:
        logger.warning("Live Client API timeout")
        return None
    except Exception as e:
        logger.warning(f"Live Client API error: {e}")
        return None


def is_game_active() -> bool:
    """Check if a game is currently running."""
    return _get("gamestats") is not None


def get_game_stats() -> Optional[dict]:
    """Game time, map, mode."""
    return _get("gamestats")


def get_all_players() -> Optional[list]:
    """All player data including items, scores, summoner spells."""
    return _get("playerlist")


def get_active_player() -> Optional[dict]:
    """Your own champion stats, runes, abilities."""
    return _get("activeplayer")


def get_events() -> Optional[dict]:
    """All game events (kills, objectives, etc.)."""
    return _get("eventdata")


# ── High-level helpers ────────────────────────────────────────────────────────

def get_my_state() -> Optional[dict]:
    """
    Returns structured state for the local player.
    Includes: champion, level, AD, AP, spell ranks, items, HP, summoners.
    """
    player_data = get_active_player()
    all_players = get_all_players()

    if not player_data or not all_players:
        return None

    # Active player full stats
    stats = player_data.get("championStats", {})
    abilities = player_data.get("abilities", {})

    # Find yourself in player list (summonerName match)
    my_summoner = player_data.get("summonerName", "")
    my_player_entry = next(
        (p for p in all_players if p.get("summonerName") == my_summoner),
        None
    )

    # Spell ranks (1-indexed from API)
    spell_ranks = {
        "q": abilities.get("Q", {}).get("abilityLevel", 1),
        "w": abilities.get("W", {}).get("abilityLevel", 1),
        "e": abilities.get("E", {}).get("abilityLevel", 1),
        "r": abilities.get("R", {}).get("abilityLevel", 1),
    }

    # Items list
    items = []
    if my_player_entry:
        raw_items = my_player_entry.get("items", [])
        items = [item.get("displayName", "") for item in raw_items]

    # Summoner spells
    summoners = []
    if my_player_entry:
        s1 = my_player_entry.get("summonerSpells", {}).get("summonerSpellOne", {})
        s2 = my_player_entry.get("summonerSpells", {}).get("summonerSpellTwo", {})
        summoners = [s1.get("rawDisplayName", ""), s2.get("rawDisplayName", "")]

    # championName not in activeplayer API - get from playerlist by summonerName
    my_summoner_name = player_data.get("summonerName", "")
    champ_name = "Unknown"
    if all_players and my_summoner_name:
        for p in all_players:
            if p.get("summonerName", "") == my_summoner_name:
                champ_name = p.get("championName", "Unknown")
                break

    return {
        "champion":       champ_name,
        "level":          player_data.get("level", 1),
        "current_hp":     stats.get("currentHealth", 500),
        "max_hp":         stats.get("maxHealth", 1000),
        "hp_percent":     stats.get("currentHealth", 500) / max(stats.get("maxHealth", 1000), 1),
        "bonus_ad":       stats.get("bonusAttackDamage", 0),
        "total_ad":       stats.get("attackDamage", 50),
        "ap":             stats.get("abilityPower", 0),
        "armor_pen_flat": stats.get("armorPenetrationFlat", 0),
        # API returns 1.0 = no pen, 0.7 = 30% pen — convert to actual % pen
        "armor_pen_pct":  max(0.0, 1.0 - stats.get("armorPenetrationPercent", 1.0)),
        "magic_pen_flat": stats.get("magicPenetrationFlat", 0),
        "magic_pen_pct":  max(0.0, 1.0 - stats.get("magicPenetrationPercent", 1.0)),
        "lethality":      stats.get("armorPenetrationFlat", 0),
        "spell_ranks":    spell_ranks,
        "items":          items,
        "summoners":      summoners,
    }


def get_enemies_state(my_team: str = "ORDER") -> list[dict]:
    """
    Returns list of enemy player states.
    my_team: 'ORDER' (blue) or 'CHAOS' (red)
    """
    all_players = get_all_players()
    if not all_players:
        return []

    enemy_team = "CHAOS" if my_team == "ORDER" else "ORDER"
    enemies = [p for p in all_players if p.get("team") == enemy_team]

    result = []
    for p in enemies:
        items = [item.get("displayName", "") for item in p.get("items", [])]
        s1 = p.get("summonerSpells", {}).get("summonerSpellOne", {})
        s2 = p.get("summonerSpells", {}).get("summonerSpellTwo", {})

        result.append({
            "summoner_name": p.get("summonerName", ""),
            "champion":      p.get("championName", "Unknown"),
            "level":         p.get("level", 1),
            "position":      p.get("position", ""),
            "items":         items,
            "is_dead":       p.get("isDead", False),
            "respawn_timer": p.get("respawnTimer", 0.0),
            "summoners": [
                s1.get("rawDisplayName", ""),
                s2.get("rawDisplayName", ""),
            ],
            # HP% will be filled in from screen reading
            "hp_percent":    None,
        })

    return result


def get_my_team(active_player: Optional[dict] = None) -> str:
    """Detect which team you're on (ORDER=blue, CHAOS=red)."""
    if active_player is None:
        active_player = get_active_player()
    all_players = get_all_players()
    if not active_player or not all_players:
        return "ORDER"

    my_name = active_player.get("summonerName", "")
    for p in all_players:
        if p.get("summonerName") == my_name:
            return p.get("team", "ORDER")
    return "ORDER"


def get_game_time() -> float:
    """Returns current game time in seconds."""
    stats = get_game_stats()
    if stats:
        return stats.get("gameTime", 0.0)
    return 0.0


# ── Demo / test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if is_game_active():
        my = get_my_state()
        print("MY STATE:", my)
        enemies = get_enemies_state()
        print("ENEMIES:", enemies)
    else:
        print("No active game detected.")
