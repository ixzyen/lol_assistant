"""
Kill Calculator — core logic.

Input:  my_state (from Live API), enemy_state (Live API + screen HP%),
        spell_ranks (from Live API).
Output: KillCalcResult with damage breakdown, confidence, flags, suggestion.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

from data.champion_stats  import calculate_stats_at_level
from data.item_stats       import (ITEM_STATS, SUMMONER_ADJUSTMENTS,
                                   get_item_stats, get_active_damage)
from data.champion_combos  import get_combo, get_base_damage_at_rank

logger = logging.getLogger(__name__)

# ── Kill confidence thresholds ─────────────────────────────────────────────────
THRESHOLD_GO       = 0.80   # ≥80% → GO
THRESHOLD_RISKY    = 0.60   # 60–79% → RISKY
# <60% → NO GO

# Minimum my HP% to even consider engaging
MIN_MY_HP_TO_ENGAGE = 0.35

# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class KillCalcResult:
    enemy_champion:     str
    my_champion:        str

    # Damage breakdown
    raw_damage:         float = 0.0
    real_damage:        float = 0.0   # after resistances
    active_item_damage: float = 0.0

    # Enemy effective HP
    enemy_current_hp:   float = 0.0
    enemy_max_hp:       float = 0.0
    enemy_hp_percent:   float = 1.0
    enemy_effective_hp: float = 0.0   # includes shields/flags

    # Stats used
    enemy_armor_used:   float = 0.0
    enemy_mr_used:      float = 0.0

    # Kill assessment
    kill_ratio:         float = 0.0   # real_damage / effective_hp
    confidence:         float = 0.0   # adjusted for uncertainty
    verdict:            str   = "NO GO"  # "GO" | "RISKY" | "NO GO"

    # Combo suggestion
    combo_label:        str   = ""
    spell_order:        str   = ""

    # Flags / warnings
    flags:              list  = field(default_factory=list)
    summoner_warnings:  list  = field(default_factory=list)
    item_flags:         list  = field(default_factory=list)

    # Blocked by auto-pause conditions
    paused:             bool  = False
    pause_reason:       str   = ""


# ── Utility functions ──────────────────────────────────────────────────────────

def _normalize_item_key(name: str) -> str:
    return (name.lower()
            .replace("'", "")
            .replace(" ", "_")
            .replace("-", "_"))


def _calc_effective_armor(base_armor: float, my_state: dict) -> float:
    """Apply armor penetration from my stats."""
    lethality    = my_state.get("lethality", 0)
    pen_pct      = my_state.get("armor_pen_pct", 0)  # 0.0–1.0
    level        = my_state.get("level", 1)

    # Lethality → flat pen scaled by level
    flat_pen = lethality * (0.6 + 0.4 * level / 18)

    armor_after_pct  = base_armor * (1 - pen_pct)
    armor_after_flat = max(0.0, armor_after_pct - flat_pen)
    return armor_after_flat


def _dmg_reduction(effective_armor: float) -> float:
    """Armor → damage multiplier (1.0 = no reduction)."""
    if effective_armor >= 0:
        return 100.0 / (100.0 + effective_armor)
    else:  # negative armor → bonus damage
        return 2.0 - 100.0 / (100.0 - effective_armor)


def _mr_reduction(effective_mr: float) -> float:
    return 100.0 / (100.0 + max(0.0, effective_mr))


def _build_enemy_stats(enemy: dict, hp_percent_override: Optional[float]) -> dict:
    """Calculate enemy's actual armor/MR/HP from level + items."""
    champ  = enemy.get("champion", "_default")
    level  = enemy.get("level", 1)
    items  = enemy.get("items", [])

    base   = calculate_stats_at_level(champ, level)
    armor  = base["armor"]
    mr     = base["mr"]
    max_hp = base["max_hp"]

    # If real-time max HP was read from panel, use it instead of calculated
    # This captures actual build (items + runes + growth) accurately
    if enemy.get("hp_max_real"):
        max_hp = float(enemy["hp_max_real"])

    item_shields = []
    item_revive  = False
    death_dance_flag = False

    for item_name in items:
        key   = _normalize_item_key(item_name)
        stats = ITEM_STATS.get(key, {})
        armor  += stats.get("armor",  0)
        mr     += stats.get("mr",     0)
        max_hp += stats.get("hp",     0)

        if stats.get("passive_shield"):
            item_shields.append((item_name, stats["passive_shield"]))
        if stats.get("active_shield"):
            item_shields.append((item_name, f"+{int(stats['active_shield']*100)}% maxHP"))
        if stats.get("revive"):
            item_revive = True
        if key == "deaths_dance":
            death_dance_flag = True

    hp_pct = hp_percent_override if hp_percent_override is not None \
             else enemy.get("hp_percent", 1.0)
    # Clamp hp_pct to valid range — OCR misreads can produce >1.0 or <=0
    if not hp_pct or hp_pct <= 0.0 or hp_pct > 1.0:
        hp_pct = 1.0
    current_hp = max_hp * hp_pct

    return {
        "armor":            armor,
        "mr":               mr,
        "max_hp":           max_hp,
        "current_hp":       current_hp,
        "hp_percent":       hp_pct,
        "item_shields":     item_shields,
        "item_revive":      item_revive,
        "death_dance_flag": death_dance_flag,
    }


def _calculate_combo_damage(my_state: dict, enemy_stats: dict,
                             spell_ranks: dict) -> tuple[float, float, list]:
    """
    Returns (physical_damage, magic_damage, damage_breakdown_list).
    """
    champ = my_state.get("champion", "_default")
    combo = get_combo(champ)
    total_ad = my_state.get("total_ad", 50)
    ap       = my_state.get("ap", 0)
    max_hp_enemy = enemy_stats.get("max_hp", 1000)

    phys_dmg  = 0.0
    magic_dmg = 0.0
    breakdown = []

    for comp in combo["damage_components"]:
        base = get_base_damage_at_rank(comp, spell_ranks)
        ad_r = comp.get("ad_ratio", 0)
        ap_r = comp.get("ap_ratio", 0)
        hp_r = comp.get("hp_ratio", 0)  # % of target max HP

        raw = base + (total_ad * ad_r) + (ap * ap_r) + (max_hp_enemy * hp_r)

        breakdown.append({
            "label": comp["label"],
            "damage": round(raw, 1),
            "type":  comp["type"],
        })

        if comp["type"] in ("physical", "true"):
            phys_dmg += raw
        else:
            magic_dmg += raw

    return phys_dmg, magic_dmg, breakdown


# ── Main calculator ────────────────────────────────────────────────────────────

def calculate_kill_chance(
    my_state:            dict,
    enemy:               dict,
    enemy_hp_percent:    Optional[float] = None,
    my_hp_percent:       Optional[float] = None,
    allies_nearby:       int = 0,
    game_time:           float = 0.0,
) -> KillCalcResult:
    """
    Main entry point.

    my_state:         dict from live_client.get_my_state()
    enemy:            dict from live_client.get_enemies_state()[i]
    enemy_hp_percent: float 0–1 from screen reader (overrides API value)
    my_hp_percent:    float 0–1 (for auto-pause check)
    allies_nearby:    rough count of visible allies near you (0 = solo gank)
    game_time:        seconds since game start
    """
    result = KillCalcResult(
        enemy_champion = enemy.get("champion", "Unknown"),
        my_champion    = my_state.get("champion", "Unknown"),
    )

    # ── Auto-pause checks ──────────────────────────────────────────────────────
    my_hp = my_hp_percent or my_state.get("hp_percent", 1.0)

    if game_time > 0 and game_time < 10:
        result.paused = True
        result.pause_reason = "Pre-game (< 10s)"
        return result

    if my_hp < MIN_MY_HP_TO_ENGAGE:
        result.paused = True
        result.pause_reason = f"Your HP too low ({my_hp:.0%})"
        return result

    if enemy.get("is_dead", False):
        result.paused = True
        result.pause_reason = "Enemy is dead"
        return result

    if game_time > 45 * 60:
        result.paused = True
        result.pause_reason = "Late game (>45min) — calc unreliable"
        return result

    # ── Build enemy stats ──────────────────────────────────────────────────────
    enemy_stats = _build_enemy_stats(enemy, enemy_hp_percent)

    result.enemy_armor_used = enemy_stats["armor"]
    result.enemy_mr_used    = enemy_stats["mr"]
    result.enemy_max_hp     = enemy_stats["max_hp"]
    result.enemy_current_hp = enemy_stats["current_hp"]
    result.enemy_hp_percent = enemy_stats["hp_percent"]

    # ── Calculate damage ───────────────────────────────────────────────────────
    spell_ranks = my_state.get("spell_ranks", {"q":1,"w":1,"e":1,"r":1})

    phys_raw, magic_raw, breakdown = _calculate_combo_damage(
        my_state, enemy_stats, spell_ranks)

    # Resistance reductions
    eff_armor = _calc_effective_armor(enemy_stats["armor"], my_state)
    eff_mr    = max(0.0, enemy_stats["mr"] - my_state.get("magic_pen_flat", 0))

    phys_dealt  = phys_raw  * _dmg_reduction(eff_armor)
    magic_dealt = magic_raw * _mr_reduction(eff_mr)
    total_dealt = phys_dealt + magic_dealt

    # Active damage items
    active_dmg = 0.0
    active_items_used = []
    for item_name in my_state.get("items", []):
        act = get_active_damage(item_name)
        if act.get("damage", 0) > 0:
            d = act["damage"] * _dmg_reduction(eff_armor) \
                if act.get("type") == "physical" else act["damage"]
            active_dmg += d
            active_items_used.append(f"{item_name} (+{d:.0f})")

    total_dealt += active_dmg

    result.raw_damage         = round(phys_raw + magic_raw, 1)
    result.real_damage        = round(total_dealt, 1)
    result.active_item_damage = round(active_dmg, 1)

    # ── Build effective HP (enemy) ─────────────────────────────────────────────
    effective_hp = enemy_stats["current_hp"]
    confidence_penalty = 0.0

    # Item shield flags
    for item_name, shield_val in enemy_stats["item_shields"]:
        if isinstance(shield_val, (int, float)):
            effective_hp += shield_val
            result.item_flags.append(f"⚠ {item_name}: +{shield_val:.0f} shield")
        else:
            result.item_flags.append(f"⚠ {item_name}: {shield_val} shield")
        confidence_penalty += 0.08

    if enemy_stats["death_dance_flag"]:
        # Death's Dance delays 30% dmg — treat as ~15% effective HP increase
        effective_hp *= 1.15
        result.item_flags.append("⚠ Death's Dance: 30% dmg delayed")
        confidence_penalty += 0.05

    if enemy_stats["item_revive"]:
        result.item_flags.append("🔴 Guardian Angel: revive possible")
        confidence_penalty += 0.20

    result.enemy_effective_hp = round(effective_hp, 1)

    # ── Summoner spell flags ───────────────────────────────────────────────────
    enemy_summoners = enemy.get("summoners", [])
    dmg_modifier = 1.0

    for s in enemy_summoners:
        adj = SUMMONER_ADJUSTMENTS.get(s, {})
        if "hp_modifier" in adj:
            effective_hp *= adj["hp_modifier"]
            result.summoner_warnings.append(
                f"⚠ {adj['label']}: ×{adj['hp_modifier']} effective HP")
            confidence_penalty += 0.08
        if "my_dmg_modifier" in adj:
            dmg_modifier *= adj["my_dmg_modifier"]
            result.summoner_warnings.append(
                f"⚠ {adj['label']}: your dmg ×{adj['my_dmg_modifier']}")
            confidence_penalty += 0.12

    adjusted_dealt = total_dealt * dmg_modifier

    # ── Eclipse / unknown item CD flag ────────────────────────────────────────
    ITEM_CD_FLAGS = {
        "eclipse":            "Eclipse proc (6s CD) — unknown state",
        "immortal_shieldbow": "Shieldbow shield (90s CD) — unknown state",
        "steraks_gage":       "Sterak's shield (60s CD) — unknown state",
        "gargoyle_stoneplate":"Gargoyle active (90s CD) — unknown state",
    }
    for item_name in enemy.get("items", []):
        key = _normalize_item_key(item_name)
        if key in ITEM_CD_FLAGS:
            result.item_flags.append(f"⚠ {ITEM_CD_FLAGS[key]}")
            confidence_penalty += 0.05  # small penalty per flagged item

    # ── Phase Rush flag ────────────────────────────────────────────────────────
    # Can't detect rune directly, but flag it as reminder
    if allies_nearby == 0:
        result.flags.append("Solo engage — watch for Phase Rush / Flash escape")

    # ── Kill ratio & confidence ────────────────────────────────────────────────
    kill_ratio  = adjusted_dealt / max(effective_hp, 1.0)
    # Base confidence tracks kill ratio, capped at 0.97
    base_conf   = min(0.97, kill_ratio)
    # Confidence reduced by uncertainty flags
    uncertainty = min(0.40, confidence_penalty)
    final_conf  = max(0.0, base_conf - uncertainty)

    result.kill_ratio  = round(kill_ratio, 3)
    result.confidence  = round(final_conf, 3)

    # ── Verdict ───────────────────────────────────────────────────────────────
    if final_conf >= THRESHOLD_GO:
        result.verdict = "GO"
    elif final_conf >= THRESHOLD_RISKY:
        result.verdict = "RISKY"
    else:
        result.verdict = "NO GO"

    # ── Combo suggestion ──────────────────────────────────────────────────────
    combo = get_combo(my_state.get("champion", "_default"))
    result.combo_label = combo["combo_label"]
    result.spell_order = combo["spell_order"]

    if active_items_used:
        result.combo_label += f" + {', '.join(active_items_used)}"

    return result


# ── Formatting ─────────────────────────────────────────────────────────────────

def format_result(r: KillCalcResult) -> str:
    """Format result for overlay display."""
    if r.paused:
        return f"[ PAUSED ] {r.pause_reason}"

    lines = []

    # Header
    verdict_icon = {"GO": "🟢", "RISKY": "🟡", "NO GO": "🔴"}.get(r.verdict, "⚪")
    lines.append(
        f"{verdict_icon} {r.verdict}  |  "
        f"Confidence: {r.confidence:.0%}  |  "
        f"Kill ratio: {r.kill_ratio:.0%}"
    )
    lines.append(f"Target: {r.enemy_champion}  "
                 f"HP: {r.enemy_hp_percent:.0%} ({r.enemy_current_hp:.0f} / {r.enemy_max_hp:.0f})")
    lines.append(f"Effective HP (with shields): {r.enemy_effective_hp:.0f}")
    lines.append("")

    # Damage summary
    lines.append(f"Your burst:   {r.real_damage:.0f} dmg  "
                 f"(raw {r.raw_damage:.0f}  |  after resists {r.real_damage:.0f})")
    lines.append(f"Enemy armor:  {r.enemy_armor_used:.0f}   |  MR: {r.enemy_mr_used:.0f}")
    if r.active_item_damage > 0:
        lines.append(f"Active items: +{r.active_item_damage:.0f} dmg")
    lines.append("")

    # Combo
    lines.append(f"Combo:  {r.spell_order}")
    lines.append("")

    # Flags
    all_warnings = r.flags + r.summoner_warnings + r.item_flags
    if all_warnings:
        lines.append("── Flags ──────────────────────")
        for w in all_warnings:
            lines.append(f"  {w}")

    return "\n".join(lines)
