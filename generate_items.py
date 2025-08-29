#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fantasy Item Catalog Generator (refactored, config-driven)
- Produces a single pretty JSON with 1000+ items (default 5×200).
- Strict name↔type consistency:
    * Weapons: name core (e.g., "Axe", "Claymore") drives weapon_type.
    * Armor: full suit only (armor_type="suit"), names include suit nouns (Armor/Mail/Plate Armor/...).
    * Accessories: name core drives accessory_type.
- Consumables follow your exact 'effect' schema; consumable_type stays "potion".
- Image paths: res://assets/textures/<category>/<id>.png
- Deterministic with RNG_SEED; configurable via CLI.

Usage:
    python3 generate_items.py
    python3 generate_items.py --out assets/data/items.json --count 200 --seed 424242
"""

from __future__ import annotations
import argparse
import json
import os
import random
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Callable, Any
from collections import OrderedDict as OD

# =============================================================================
# Configuration (tweak here)
# =============================================================================

RNG_SEED = 424242
DEFAULT_OUTPUT_PATH = os.path.join("assets", "data", "items.json")
DEFAULT_PER_CATEGORY = 200  # 5×200 = 1000 items

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_MULT: Dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.5,
    "rare": 2.5,
    "epic": 4.0,
    "legendary": 6.5,
}
RARITY_COLORS: Dict[str, str] = {
    "common": "#FFFFFF",
    "uncommon": "#00FF00",
    "rare": "#0080FF",
    "epic": "#8000FF",
    "legendary": "#FF8000",
}

# Shop routing per category & rarity
SHOPS_ALL = ["blacksmith", "general_store", "magic_shop", "alchemist", "rare_goods", "hunters_guild", "dungeon_merchant"]

def shops_for(category: str, rarity: str) -> List[str]:
    if category == "weapon":
        return ["blacksmith", "general_store"] if rarity in ("common", "uncommon") else ["blacksmith", "rare_goods"]
    if category == "armor":
        return ["general_store", "blacksmith"] if rarity in ("common", "uncommon") else ["blacksmith", "rare_goods"]
    if category == "accessory":
        return ["general_store", "magic_shop"] if rarity in ("common", "uncommon") else ["magic_shop", "rare_goods"]
    if category == "consumable":
        return ["general_store", "alchemist"] if rarity in ("common", "uncommon") else ["alchemist", "rare_goods"]
    return ["general_store"]

# ---- Name pools ----
PFX_COMMON = [
    "Iron","Steel","Shadow","Storm","Ember","Frost","Moon","Sun","Dragon",
    "Raven","Phoenix","Crystal","Obsidian","Silver","Golden","Void","Arcane",
    "Whisper","Glacier","Oak","Sunsteel"
]
SUFFIX_FLAVOR = [
    " of Dawn"," of Dusk"," of Whispers"," of the Phoenix"," of the Glacier"," of Storms",
    " of Shadows"," of Radiance"," of Embers"," of Frost"," of the Dragon"," of the Raven",
    " of Clarity"," of Might"," of Swiftness"," of Focus"," of the Tide"," of Sparks"
]

# Weapons: map name cores to weapon_type; use this for generation + validation
WEAPON_NAME_CORES: List[Tuple[str, str]] = [
    ("Sword", "sword"), ("Blade", "sword"), ("Saber", "sword"), ("Cutlass", "sword"), ("Claymore", "sword"),
    ("Axe", "axe"), ("Waraxe", "axe"),
    ("Mace", "mace"), ("Hammer", "mace"), ("Maul", "mace"),
    ("Dagger", "dagger"), ("Dirk", "dagger"),
    ("Spear", "spear"),
    ("Halberd", "polearm"), ("Glaive", "polearm"),
    ("Lance", "lance"),
    ("Bow", "bow"), ("Crossbow", "crossbow"),
    ("Staff", "staff"),
    ("Scythe", "scythe"),
]
TYPE_TO_WEAPON_TOKENS: Dict[str, List[str]] = {
    "sword": ["sword","blade","saber","cutlass","claymore"],
    "axe": ["axe","waraxe"],
    "mace": ["mace","hammer","maul"],
    "dagger": ["dagger","dirk"],
    "spear": ["spear"],
    "lance": ["lance"],
    "polearm": ["halberd","glaive"],
    "bow": ["bow"],
    "crossbow": ["crossbow"],
    "staff": ["staff"],
    "scythe": ["scythe"],
}
WEAPON_TOKENS_FLAT = sorted({t for lst in TYPE_TO_WEAPON_TOKENS.values() for t in lst})

# Armor (suit-only): name cores; validate with tokens
ARMOR_CORES = [
    "Armor","Mail","Plate Armor","Scale Armor","Brigandine",
    "Leather Armor","Chainmail Armor","Dragonscale Armor","Battle Armor","War Armor"
]
ARMOR_TOKENS = [t.lower() for t in ["armor","mail","brigandine","dragonscale","war armor","plate armor","scale armor","chainmail"]]

# Accessories: map name cores to accessory_type
ACCESSORY_NAME_CORES: List[Tuple[str, str]] = [
    ("Ring", "ring"), ("Amulet", "amulet"), ("Charm", "charm"), ("Band", "band"),
    ("Brooch", "brooch"), ("Talisman", "talisman"), ("Circlet", "circlet"),
    ("Pendant", "pendant"), ("Bracelet", "bracelet"), ("Anklet", "anklet"), ("Sash", "sash")
]

# Consumables: base names + effect kind (consumable_type remains "potion" per your template)
CONSUMABLE_TEMPLATES: List[Tuple[str, str]] = [
    ("Health Potion", "heal"),
    ("Greater Health Potion", "heal"),
    ("Mana Potion", "mana_restore"),
    ("Elixir of Strength", "stat_boost"),
    ("Elixir of Dexterity", "stat_boost"),
    ("Elixir of Constitution", "stat_boost"),
    ("Elixir of Intelligence", "stat_boost"),
    ("Elixir of Wisdom", "stat_boost"),
    ("Elixir of Charisma", "stat_boost"),
    ("Potion of Swiftness", "speed_boost"),
]

# Materials
MATERIAL_TYPES = ["metal","wood","gem","stone","cloth","herb","essence","bone","leather"]
MATERIAL_CORES = [
    "Ingot","Bar","Ore","Shard","Crystal","Gem","Thread","Fiber","Silk","Heartwood","Wood","Plank",
    "Pelt","Leather","Feather","Bone","Scale","Powder","Resin","Herb","Blossom","Root","Seed","Essence","Core"
]

# Crafting materials pool (IDs)
CRAFT_POOL = [
    "iron_ingot","steel_ingot","leather_strip","oak_wood","obsidian_shard","ember_crystal",
    "arcane_thread","moonshade_fabric","vitality_herb","frost_core","storm_essence",
    "sunsteel_ingot","drakescale","pure_water","healing_herb","luminescent_moss",
    "crystal_shard","runed_stone","ghost_essence","phoenix_feather"
]

# Effects pool
SPECIAL_EFFECT_POOL = [
    "bleed_on_hit", "burn_on_hit", "freeze_on_hit", "shock_on_hit",
    "mana_leech", "life_leech", "backstab_bonus", "parry_window",
    "elemental_affinity:fire", "elemental_affinity:ice", "elemental_affinity:lightning",
    "clarity:spell_focus", "frost_aura", "fear_aura", "thorns", "regen_over_time",
    "dash_cooldown_reduction", "crit_chain", "lightning_chain"
]

ELEMENTS = ["fire","ice","lightning","poison"]

# =============================================================================
# Helpers (pure functions)
# =============================================================================

def to_id(name: str) -> str:
    s = name.strip().lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

_used_names: set[str] = set()
def unique_name(base: str, allow_suffix: bool = True, allow_flavor: bool = True) -> str:
    name = base
    if allow_flavor and allow_suffix and random.random() < 0.5:
        name += random.choice(SUFFIX_FLAVOR)
    tries, n = 0, name
    while n in _used_names and tries < 20:
        tries += 1
        n = f"{base} {random.randint(0, 999)}"
    _used_names.add(n)
    return n

def img_path(category: str, _id: str) -> str:
    return f"res://assets/textures/{category}/{_id}.png"

def pick_rarity() -> str:
    r = random.random()
    if r < 0.45: return "common"
    if r < 0.75: return "uncommon"
    if r < 0.92: return "rare"
    if r < 0.985: return "epic"
    return "legendary"

def level_for_rarity(r: str) -> int:
    return {"common": random.randint(1,4), "uncommon": random.randint(5,8),
            "rare": random.randint(9,12), "epic": random.randint(13,17),
            "legendary": random.randint(18,20)}[r]

def stat_bonus(r: str) -> int:
    return int(round(RARITY_MULT[r]))

def maybe_bonus(r: str) -> int:
    return stat_bonus(r) if random.random() < 0.5 else 0

def crit_chance(r: str) -> int:
    return {"common": random.randint(3,4), "uncommon": random.randint(5,7),
            "rare": random.randint(8,10), "epic": random.randint(10,12),
            "legendary": random.randint(12,15)}[r]

def crit_damage(r: str) -> int:
    return 120 + int(round(10 * RARITY_MULT[r]))

def maybe_effects(r: str) -> List[str]:
    effects: List[str] = []
    if random.random() < 0.33 or r in ("rare","epic","legendary"):
        count = 1 + (1 if r in ("epic","legendary") else 0)
        for _ in range(count):
            e = random.choice(SPECIAL_EFFECT_POOL)
            if e.startswith("elemental_affinity"):
                e = f"{e}:{5 + int(5 * RARITY_MULT[r])}%"
            elif e in ("bleed_on_hit","burn_on_hit","freeze_on_hit","shock_on_hit"):
                e = f"{e}:{10 + int(5 * RARITY_MULT[r])}%:{random.randint(3,6)}s"
            elif e == "clarity:spell_focus":
                e = f"clarity:spell_focus:{5 + int(5 * RARITY_MULT[r])}%"
            effects.append(e)
    return effects

def gold_value(r: str, min_v: int, max_v: int) -> int:
    idx = RARITY_ORDER.index(r)
    t = idx / (len(RARITY_ORDER)-1)
    base = min_v + (max_v - min_v) * t
    return int(base + random.randint(0, min_v))

def craft_mats(r: str, min_n: int, max_n: int, *, liquid: bool=False) -> Dict[str, int]:
    mats: Dict[str, int] = {}
    for _ in range(random.randint(min_n, max_n)):
        mat = random.choice(CRAFT_POOL)
        if liquid and mat != "pure_water" and random.random() < 0.33:
            mat = "pure_water"
        mats[to_id(mat)] = 1 + (RARITY_ORDER.index(r) // 2)
    return mats

def elem_res(r: str) -> int:
    if r == "common": return 0
    if r == "uncommon": return random.choice([0,5])
    if r == "rare": return random.choice([5,10,15])
    if r == "epic": return random.choice([10,15,20])
    return random.choice([15,20,25])

def consumable_desc(kind: str, r: str) -> str:
    return {
        "heal": "Restores a modest amount of health instantly." if r=="common" else
                "A potent brew that restores more health." if r=="uncommon" else
                "A strong restorative for grievous wounds." if r=="rare" else
                "An elite draught favored by champions." if r=="epic" else
                "A mythical concoction that mends any injury.",
        "mana_restore": "Replenishes a portion of mana instantly.",
        "stat_boost": "Temporarily enhances attributes.",
        "speed_boost": "Increases movement speed for a short time.",
    }[kind]

def build_effect(kind: str, r: str) -> Dict[str, Any]:
    eff = OD([
        ("type", kind), ("value", 0), ("duration", 0), ("instant", True),
        ("stats_affected", OD([
            ("health", 0), ("mana", 0),
            ("strength", 0), ("dexterity", 0), ("constitution", 0),
            ("intelligence", 0), ("wisdom", 0), ("charisma", 0),
        ]))
    ])
    if kind == "heal":
        v = 120 if r=="common" else 350 if r=="uncommon" else 600 if r=="rare" else 900 if r=="epic" else 1400
        eff["value"] = v; eff["stats_affected"]["health"] = v
    elif kind == "mana_restore":
        v = 100 if r=="common" else 200 if r=="uncommon" else 350 if r=="rare" else 500 if r=="epic" else 750
        eff["value"] = v; eff["stats_affected"]["mana"] = v
    elif kind == "stat_boost":
        dur = 300 if r in ("uncommon","common") else 600 if r=="rare" else 900 if r=="epic" else 1200
        amt = 1 if r=="common" else 2 if r=="uncommon" else 3 if r=="rare" else 4 if r=="epic" else 5
        which = random.choice(["strength","dexterity","constitution","intelligence","wisdom","charisma"])
        eff["duration"] = dur; eff["instant"] = False
        eff["stats_affected"][which] = amt
    elif kind == "speed_boost":
        eff["duration"] = 180 if r in ("common","uncommon") else 300 if r=="rare" else 420
        eff["instant"] = False
        eff["value"] = 15 if r=="common" else 20 if r=="uncommon" else 25 if r=="rare" else 30 if r=="epic" else 35
    return eff

# =============================================================================
# Builders (category-specific)
# =============================================================================

# -- Weapons --
def name_weapon() -> Tuple[str, str]:
    core, wtype = random.choice(WEAPON_NAME_CORES)
    base = f"{random.choice(PFX_COMMON)} {core}"
    name = unique_name(base, allow_suffix=True, allow_flavor=True)
    return name, wtype  # wtype derived from core

def weapon_item() -> Dict[str, Any]:
    r = pick_rarity()
    name, wtype_from_core = name_weapon()
    _id = to_id(name)
    base_atk = random.randint(10, 20)
    atk = int(round(base_atk * RARITY_MULT[r])) + random.randint(0, 3)
    item = OD([
        ("id", _id), ("name", name), ("type", "weapon"),
        ("weapon_type", wtype_from_core),
        ("rarity", r), ("level_requirement", level_for_rarity(r)),
        ("stats", OD([
            ("attack", atk),
            ("strength_bonus", stat_bonus(r)), ("dexterity_bonus", stat_bonus(r)),
            ("constitution_bonus", maybe_bonus(r)),
            ("intelligence_bonus", 0), ("wisdom_bonus", 0), ("charisma_bonus", 0),
            ("critical_chance", crit_chance(r)), ("critical_damage", crit_damage(r)),
        ])),
        ("special_effects", maybe_effects(r)),
        ("value", gold_value(r, 100, 900)),
        ("durability", random.randint(70,180)),
        ("crafting", OD([
            ("recipe_id", f"rcp_{_id}"),
            ("materials", craft_mats(r, 2, 4)),
        ])),
        ("shop_availability", shops_for("weapon", r)),
        ("image", img_path("weapons", _id)),
    ])
    # Validation
    low = name.lower()
    assert any(tok in low for tok in WEAPON_TOKENS_FLAT), f"Weapon name missing core: {name}"
    assert any(tok in low for tok in TYPE_TO_WEAPON_TOKENS.get(item['weapon_type'], [])), f"Weapon name/type mismatch: {name} vs {item['weapon_type']}"
    return item

# -- Armor (suit only) --
def name_armor() -> str:
    base = f"{random.choice(PFX_COMMON)} {random.choice(ARMOR_CORES)}"
    return unique_name(base, allow_suffix=True, allow_flavor=True)

def armor_item() -> Dict[str, Any]:
    r = pick_rarity()
    name = name_armor()
    # defensive retry to ensure tokens present
    tries = 0
    while not any(tok in name.lower() for tok in ARMOR_TOKENS) and tries < 5:
        name = name_armor(); tries += 1
    _id = to_id(name)
    base_def = random.randint(12, 20)  # suits are beefier
    defense = int(round(base_def * RARITY_MULT[r])) + random.randint(0, 3)
    res = {e: elem_res(r) for e in ELEMENTS}
    item = OD([
        ("id", _id), ("name", name), ("type", "armor"),
        ("armor_type", "suit"),
        ("rarity", r), ("level_requirement", level_for_rarity(r)),
        ("stats", OD([
            ("defense", defense),
            ("armor_class_bonus", min(int(RARITY_MULT[r]), 3)),
            ("strength_bonus", maybe_bonus(r)),
            ("dexterity_bonus", maybe_bonus(r)),
            ("constitution_bonus", maybe_bonus(r)),
            ("intelligence_bonus", 0), ("wisdom_bonus", 0), ("charisma_bonus", 0),
            ("elemental_resistance", res),
        ])),
        ("special_effects", maybe_effects(r)),
        ("value", gold_value(r, 120, 1800)),
        ("durability", random.randint(110,190)),
        ("crafting", OD([
            ("recipe_id", f"rcp_{_id}"),
            ("materials", craft_mats(r, 3, 5)),
        ])),
        ("shop_availability", shops_for("armor", r)),
        ("image", img_path("armor", _id)),
    ])
    assert any(tok in name.lower() for tok in ARMOR_TOKENS), f"Armor name not a suit: {name}"
    return item

# -- Accessories (name core drives accessory_type) --
def name_accessory() -> Tuple[str, str]:
    core, atype = random.choice(ACCESSORY_NAME_CORES)
    base = f"{random.choice(PFX_COMMON)} {core}"
    name = unique_name(base, allow_suffix=True, allow_flavor=True)
    return name, atype

def accessory_item() -> Dict[str, Any]:
    r = pick_rarity()
    name, atype = name_accessory()
    _id = to_id(name)
    item = OD([
        ("id", _id), ("name", name), ("type", "accessory"),
        ("accessory_type", atype),
        ("rarity", r), ("level_requirement", level_for_rarity(r)),
        ("stats", OD([
            ("strength_bonus", maybe_bonus(r)),
            ("dexterity_bonus", maybe_bonus(r)),
            ("constitution_bonus", maybe_bonus(r)),
            ("intelligence_bonus", maybe_bonus(r)),
            ("wisdom_bonus", maybe_bonus(r)),
            ("charisma_bonus", maybe_bonus(r)),
            ("mana_regeneration", int(round(RARITY_MULT[r]))),
            ("health_regeneration", max(int(round(RARITY_MULT[r])) - 1, 0)),
            ("experience_bonus", int(5 * RARITY_MULT[r]) if r in ("rare","epic","legendary") else 0),
        ])),
        ("special_effects", maybe_effects(r)),
        ("value", gold_value(r, 150, 1800)),
        ("durability", random.randint(40,120)),
        ("crafting", OD([
            ("recipe_id", f"rcp_{_id}"),
            ("materials", craft_mats(r, 2, 3)),
        ])),
        ("shop_availability", shops_for("accessory", r)),
        ("image", img_path("accessories", _id)),
    ])
    assert atype in name.lower(), f"Accessory name/type mismatch: {name} vs {atype}"
    return item

# -- Consumables (exact effect schema; type=potion) --
def name_consumable() -> Tuple[str, str]:
    base, kind = random.choice(CONSUMABLE_TEMPLATES)
    name = unique_name(base, allow_suffix=False, allow_flavor=False)
    return name, kind

def consumable_item() -> Dict[str, Any]:
    r = pick_rarity()
    name, kind = name_consumable()
    _id = to_id(name)
    eff = build_effect(kind, r)
    item = OD([
        ("id", _id), ("name", name), ("type", "consumable"),
        ("consumable_type", "potion"),
        ("rarity", r), ("effect", eff),
        ("stack_size", 99 if r in ("common","uncommon") else 10),
        ("value", gold_value(r, 20, 400)),
        ("crafting", OD([
            ("recipe_id", f"rcp_{_id}"),
            ("materials", craft_mats(r, 2, 3, liquid=True)),
        ])),
        ("shop_availability", shops_for("consumable", r)),
        ("description", consumable_desc(kind, r)),
        ("image", img_path("consumables", _id)),
    ])
    # Basic validation: must mention potion/elixir/etc. in name
    low = name.lower()
    assert any(k in low for k in ["potion","elixir","draught","scroll","tonic"]), f"Consumable name missing keyword: {name}"
    return item

# -- Materials --
def name_material() -> str:
    base = f"{random.choice(PFX_COMMON)} {random.choice(MATERIAL_CORES)}"
    return unique_name(base, allow_suffix=False, allow_flavor=False)

def material_item() -> Dict[str, Any]:
    r = random.choices(RARITY_ORDER, weights=[45,30,18,6,1])[0]
    name = name_material()
    _id = to_id(name)
    mtype = random.choice(MATERIAL_TYPES)
    territory_pool = ["verdant_lands_mines","forest_logging_camps","tannery","crystal_cavern","ashmire_deep","ember_hollows"]
    dungeons = ["ember_hollows","ashmire_deep","moonlit_keep","glacier_pass"]
    sources: List[Dict[str, Any]] = [
        OD([("type","territory_income"),("source_id",random.choice(territory_pool)),("rate_per_hour",round(random.uniform(1.5,4.5),2)),("drop_rate",0.0)]),
        OD([("type","shop"),("source_id",random.choice(["blacksmith","general_store","alchemist","rare_goods"])),("rate_per_hour",0.0),("drop_rate",0.0)]),
    ]
    if random.random() < 0.33:
        sources.append(OD([("type","dungeon_drop"),("source_id",random.choice(dungeons)),("rate_per_hour",0.0),("drop_rate",round(random.uniform(5.0,18.0),2))]))
    item = OD([
        ("id", _id), ("name", name), ("type", "crafting_material"),
        ("material_type", mtype),
        ("rarity", r), ("stack_size", 999), ("value", gold_value(r, 3, 45)),
        ("sources", sources),
        ("description", random.choice([
            "A bar of smelted stock, sturdy and ubiquitous.",
            "Highly sought for advanced recipes.",
            "Flickers with latent energy.",
            "Seasoned resource prized by artisans.",
            "Conductive material suited for runework."
        ])),
        ("image", img_path("materials", _id)),
    ])
    # Validation: ensure material-esque token appears
    low = name.lower()
    assert any(tok in low for tok in ["ingot","bar","ore","shard","crystal","gem","thread","fiber","silk","heartwood","wood","plank","pelt","leather","feather","bone","scale","powder","resin","herb","blossom","root","seed","essence","core"]), f"Material name lacks material token: {name}"
    return item

# =============================================================================
# Orchestration
# =============================================================================

BUILDERS: Dict[str, Callable[[], Dict[str, Any]]] = {
    "weapons": weapon_item,
    "armor": armor_item,
    "accessories": accessory_item,
    "consumables": consumable_item,
    "materials": material_item,
}

@dataclass
class GenConfig:
    per_category: int = DEFAULT_PER_CATEGORY
    out_path: str = DEFAULT_OUTPUT_PATH
    seed: int = RNG_SEED

def generate(cfg: GenConfig) -> Dict[str, Any]:
    random.seed(cfg.seed)
    os.makedirs(os.path.dirname(cfg.out_path), exist_ok=True)

    data = OD([
        ("version", "1.0"),
        ("categories", OD([
            ("weapons", [BUILDERS["weapons"]() for _ in range(cfg.per_category)]),
            ("armor", [BUILDERS["armor"]() for _ in range(cfg.per_category)]),
            ("accessories", [BUILDERS["accessories"]() for _ in range(cfg.per_category)]),
            ("consumables", [BUILDERS["consumables"]() for _ in range(cfg.per_category)]),
            ("materials", [BUILDERS["materials"]() for _ in range(cfg.per_category)]),
            ("rarity_multipliers", RARITY_MULT),
            ("rarity_colors", RARITY_COLORS),
        ]))
    ])
    return data

def write_json(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

# =============================================================================
# CLI
# =============================================================================

def parse_args() -> GenConfig:
    ap = argparse.ArgumentParser(description="Generate a Godot-ready item catalog JSON.")
    ap.add_argument("--out", dest="out_path", default=DEFAULT_OUTPUT_PATH, help="Output JSON path")
    ap.add_argument("--count", dest="count", type=int, default=DEFAULT_PER_CATEGORY, help="Items per category")
    ap.add_argument("--seed", dest="seed", type=int, default=RNG_SEED, help="Random seed")
    args = ap.parse_args()
    return GenConfig(per_category=args.count, out_path=args.out_path, seed=args.seed)

def main() -> None:
    cfg = parse_args()
    data = generate(cfg)
    write_json(cfg.out_path, data)
    total = cfg.per_category * 5
    print(f"✅ Wrote {cfg.out_path} with {total} items (armor = full suits).")

if __name__ == "__main__":
    main()
