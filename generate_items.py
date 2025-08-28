#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a single large JSON file (~1000 items) matching Example.json structure,
with category-correct names (weapons get weapon nouns, materials get material nouns, etc.).
IDs are lowercase_with_underscores derived from names.
"""

import json, os, random, re
from collections import OrderedDict

# ---------------- Config ----------------
TOTAL_PER_CATEGORY = 200                     # 5 x 200 = 1000
OUTPUT_PATH = os.path.join("assets", "data", "items.json")
RNG_SEED = 424242

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_MULT = OrderedDict([
    ("common", 1.0), ("uncommon", 1.5), ("rare", 2.5), ("epic", 4.0), ("legendary", 6.5)
])
RARITY_COLORS = OrderedDict([
    ("common", "#FFFFFF"), ("uncommon", "#00FF00"), ("rare", "#0080FF"),
    ("epic", "#8000FF"), ("legendary", "#FF8000")
])

# Shops
def shops_for(category: str, r: str):
    if category == "weapon":
        return ["blacksmith","general_store"] if r in ("common","uncommon") else ["blacksmith","rare_goods"]
    if category == "armor":
        return ["general_store","blacksmith"] if r in ("common","uncommon") else ["blacksmith","rare_goods"]
    if category == "accessory":
        return ["general_store","magic_shop"] if r in ("common","uncommon") else ["magic_shop","rare_goods"]
    if category == "consumable":
        return ["general_store","alchemist"] if r in ("common","uncommon") else ["alchemist","rare_goods"]
    return ["general_store"]

# ---------------- Name Lexicons (category-specific) ----------------
# Prefixes (safe across categories)
PFX_COMMON = [
    "Iron","Steel","Shadow","Storm","Ember","Frost","Moon","Sun","Dragon",
    "Raven","Phoenix","Crystal","Obsidian","Silver","Golden","Void","Arcane",
    "Whisper","Glacier","Oak","Sunsteel"
]
# Suffix flavor (only for gear/accessories, not materials)
SUFFIX_FLAVOR = [
    " of Dawn"," of Dusk"," of Whispers"," of the Phoenix"," of the Glacier"," of Storms",
    " of Shadows"," of Radiance"," of Embers"," of Frost"," of the Dragon"," of the Raven",
    " of Clarity"," of Might"," of Swiftness"," of Focus"," of the Tide"," of Sparks"
]

# Hard category cores:
WEAPON_CORES = [
    "Sword","Blade","Saber","Cutlass","Claymore","Axe","Waraxe","Mace","Hammer","Maul",
    "Dagger","Dirk","Spear","Halberd","Lance","Glaive","Staff","Scythe","Bow","Crossbow"
]
ARMOR_CORES = [
    "Helm","Helmet","Visor","Mask","Cowl","Cuirass","Hauberk","Chestplate","Plate","Mail",
    "Greaves","Leggings","Sabatons","Boots","Shield","Mantle","Cloak","Bracers","Gauntlets","Belt","Pauldron"
]
ACCESSORY_CORES = [
    "Ring","Amulet","Charm","Band","Brooch","Talisman","Circlet","Pendant","Bracelet","Anklet","Sash"
]
CONSUMABLE_TEMPLATES = [
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
MATERIAL_CORES = [
    "Ingot","Bar","Ore","Shard","Crystal","Gem","Thread","Fiber","Silk","Heartwood","Wood","Plank",
    "Pelt","Leather","Feather","Bone","Scale","Powder","Resin","Herb","Blossom","Root","Seed","Essence","Core"
]

# Pools for crafting materials (IDs expected in data)
CRAFT_POOL = [
    "iron_ingot","steel_ingot","leather_strip","oak_wood","obsidian_shard","ember_crystal",
    "arcane_thread","moonshade_fabric","vitality_herb","frost_core","storm_essence",
    "sunsteel_ingot","drakescale","pure_water","healing_herb","luminescent_moss",
    "crystal_shard","runed_stone","ghost_essence","phoenix_feather"
]

ELEMENTS = ["fire","ice","lightning","poison"]
SPECIAL_EFFECT_POOL = [
    "bleed_on_hit", "burn_on_hit", "freeze_on_hit", "shock_on_hit",
    "mana_leech", "life_leech", "backstab_bonus", "parry_window",
    "elemental_affinity:fire", "elemental_affinity:ice", "elemental_affinity:lightning",
    "clarity:spell_focus", "frost_aura", "fear_aura", "thorns", "regen_over_time",
    "dash_cooldown_reduction", "crit_chain", "lightning_chain"
]

# --------------- Utilities ---------------
def to_id(name: str) -> str:
    s = name.strip().lower()
    s = s.replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

_used_names = set()
def unique_name(base: str, allow_suffix: bool = True, allow_flavor: bool = True) -> str:
    # base must already be category-safe (e.g., "Iron Sword", "Dragon Silk", etc.)
    name = base
    if allow_flavor and allow_suffix and random.random() < 0.5:
        name += random.choice(SUFFIX_FLAVOR)
    tries = 0
    n = name
    while n in _used_names and tries < 15:
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

def maybe_effects(r: str):
    effects = []
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

def craft_mats(r: str, min_n: int, max_n: int, liquid: bool=False) -> OrderedDict:
    mats = OrderedDict()
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
    return random.choice([15,20,25])  # legendary

def consumable_desc(kind: str, r: str) -> str:
    return {
        "heal": "Restores a modest amount of health instantly." if r=="common" else "A potent brew that restores more health." if r=="uncommon" else "A strong restorative for grievous wounds." if r=="rare" else "An elite draught favored by champions." if r=="epic" else "A mythical concoction that mends any injury.",
        "mana_restore": "Replenishes a portion of mana instantly.",
        "stat_boost": "Temporarily enhances attributes.",
        "speed_boost": "Increases movement speed for a short time.",
    }[kind]

def build_effect(kind: str, r: str) -> dict:
    eff = {
        "type": kind, "value": 0, "duration": 0, "instant": True,
        "stats_affected": {"health":0,"mana":0,"strength":0,"dexterity":0,"constitution":0,"intelligence":0,"wisdom":0,"charisma":0}
    }
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
        eff.update({"duration": dur, "instant": False})
        eff["stats_affected"][which] = amt
    elif kind == "speed_boost":
        eff.update({"duration": 180 if r in ("common","uncommon") else 300 if r=="rare" else 420, "instant": False})
        eff["value"] = 15 if r=="common" else 20 if r=="uncommon" else 25 if r=="rare" else 30 if r=="epic" else 35
    return eff

# ---------------- Category-specific name builders ----------------
def name_weapon() -> str:
    base = f"{random.choice(PFX_COMMON)} {random.choice(WEAPON_CORES)}"
    return unique_name(base, allow_suffix=True, allow_flavor=True)

def name_armor() -> str:
    base = f"{random.choice(PFX_COMMON)} {random.choice(ARMOR_CORES)}"
    return unique_name(base, allow_suffix=True, allow_flavor=True)

def name_accessory() -> str:
    base = f"{random.choice(PFX_COMMON)} {random.choice(ACCESSORY_CORES)}"
    return unique_name(base, allow_suffix=True, allow_flavor=True)

def name_consumable() -> tuple[str, str]:
    # returns (name, effect_kind)
    base, kind = random.choice(CONSUMABLE_TEMPLATES)
    # Small chance to upgrade/downgrade naming by rarity elsewhere; here we keep names canonical
    return unique_name(base, allow_suffix=False, allow_flavor=False), kind

def name_material() -> str:
    base = f"{random.choice(PFX_COMMON)} {random.choice(MATERIAL_CORES)}"
    # No flavor suffix for materials to keep names clean and obvious
    return unique_name(base, allow_suffix=False, allow_flavor=False)

# ---------------- Validators (safety net) ----------------
def validate_category_name(category: str, name: str) -> bool:
    """Ensure the name contains one of the category's allowed nouns."""
    target = name.lower()
    def any_in(tokens): return any(t.lower() in target for t in tokens)
    if category == "weapons":   return any_in(WEAPON_CORES)
    if category == "armor":     return any_in(ARMOR_CORES)
    if category == "accessories": return any_in(ACCESSORY_CORES)
    if category == "consumables": return ("potion" in target) or ("elixir" in target) or ("draught" in target) or ("scroll" in target) or ("tonic" in target)
    if category == "materials": return any_in(MATERIAL_CORES)
    return True

# --------------- Generators ---------------
def gen_weapons(n: int):
    out = []
    for _ in range(n):
        r = pick_rarity()
        name = name_weapon()
        _id = to_id(name)
        base_atk = random.randint(10, 20)
        atk = int(round(base_atk * RARITY_MULT[r])) + random.randint(0, 3)
        item = OrderedDict([
            ("id", _id),
            ("name", name),
            ("type", "weapon"),
            ("weapon_type", random.choice(["sword","axe","mace","dagger","spear","lance","bow","crossbow","staff","polearm","scythe"])),
            ("rarity", r),
            ("level_requirement", level_for_rarity(r)),
            ("stats", OrderedDict([
                ("attack", atk),
                ("strength_bonus", stat_bonus(r)),
                ("dexterity_bonus", stat_bonus(r)),
                ("constitution_bonus", maybe_bonus(r)),
                ("intelligence_bonus", 0), ("wisdom_bonus", 0), ("charisma_bonus", 0),
                ("critical_chance", crit_chance(r)), ("critical_damage", crit_damage(r)),
            ])),
            ("special_effects", maybe_effects(r)),
            ("value", gold_value(r, 100, 900)),
            ("durability", random.randint(70,180)),
            ("crafting", OrderedDict([
                ("recipe_id", f"rcp_{_id}"),
                ("materials", craft_mats(r, 2, 4)),
            ])),
            ("shop_availability", shops_for("weapon", r)),
            ("image", img_path("weapons", _id)),
        ])
        assert validate_category_name("weapons", name)
        out.append(item)
    return out

def gen_armor(n: int):
    out = []
    for _ in range(n):
        r = pick_rarity()
        name = name_armor()
        _id = to_id(name)
        base_def = random.randint(5, 12)
        defense = int(round(base_def * RARITY_MULT[r])) + random.randint(0, 2)
        res = {e: elem_res(r) for e in ELEMENTS}
        item = OrderedDict([
            ("id", _id),
            ("name", name),
            ("type", "armor"),
            ("armor_type", random.choice(["helmet","chest","legs","gloves","boots","shield","cloak","belt","bracers"])),
            ("rarity", r),
            ("level_requirement", level_for_rarity(r)),
            ("stats", OrderedDict([
                ("defense", defense),
                ("armor_class_bonus", min(int(RARITY_MULT[r]), 3)),
                ("strength_bonus", maybe_bonus(r)),
                ("dexterity_bonus", maybe_bonus(r)),
                ("constitution_bonus", maybe_bonus(r)),
                ("intelligence_bonus", 0), ("wisdom_bonus", 0), ("charisma_bonus", 0),
                ("elemental_resistance", res),
            ])),
            ("special_effects", maybe_effects(r)),
            ("value", gold_value(r, 80, 1600)),
            ("durability", random.randint(80,180)),
            ("crafting", OrderedDict([
                ("recipe_id", f"rcp_{_id}"),
                ("materials", craft_mats(r, 2, 4)),
            ])),
            ("shop_availability", shops_for("armor", r)),
            ("image", img_path("armor", _id)),
        ])
        assert validate_category_name("armor", name)
        out.append(item)
    return out

def gen_accessories(n: int):
    out = []
    for _ in range(n):
        r = pick_rarity()
        name = name_accessory()
        _id = to_id(name)
        item = OrderedDict([
            ("id", _id),
            ("name", name),
            ("type", "accessory"),
            ("accessory_type", random.choice(["ring","amulet","charm","brooch","band","trinket"])),
            ("rarity", r),
            ("level_requirement", level_for_rarity(r)),
            ("stats", OrderedDict([
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
            ("crafting", OrderedDict([
                ("recipe_id", f"rcp_{_id}"),
                ("materials", craft_mats(r, 2, 3)),
            ])),
            ("shop_availability", shops_for("accessory", r)),
            ("image", img_path("accessories", _id)),
        ])
        assert validate_category_name("accessories", name)
        out.append(item)
    return out

def gen_consumables(n: int):
    out = []
    for _ in range(n):
        r = pick_rarity()
        name, kind = name_consumable()
        _id = to_id(name)
        eff = build_effect(kind, r)
        item = OrderedDict([
            ("id", _id),
            ("name", name),
            ("type", "consumable"),
            ("consumable_type", "potion"),  # stay aligned with your template
            ("rarity", r),
            ("effect", eff),
            ("stack_size", 99 if r in ("common","uncommon") else 10),
            ("value", gold_value(r, 20, 400)),
            ("crafting", OrderedDict([
                ("recipe_id", f"rcp_{_id}"),
                ("materials", craft_mats(r, 2, 3, liquid=True)),
            ])),
            ("shop_availability", shops_for("consumable", r)),
            ("description", consumable_desc(kind, r)),
            ("image", img_path("consumables", _id)),
        ])
        assert validate_category_name("consumables", name)
        out.append(item)
    return out

def gen_materials(n: int):
    out = []
    territory_pool = ["verdant_lands_mines","forest_logging_camps","tannery","crystal_cavern","ashmire_deep","ember_hollows"]
    dungeons = ["ember_hollows","ashmire_deep","moonlit_keep","glacier_pass"]
    for _ in range(n):
        r = random.choices(RARITY_ORDER, weights=[45,30,18,6,1])[0]
        name = name_material()  # e.g., "Dragon Silk", "Obsidian Shard"
        _id = to_id(name)
        mtype = random.choice(["metal","wood","gem","stone","cloth","herb","essence","bone","leather"])
        sources = [
            OrderedDict([
                ("type", "territory_income"),
                ("source_id", random.choice(territory_pool)),
                ("rate_per_hour", round(random.uniform(1.5, 4.5), 2)),
                ("drop_rate", 0.0),
            ]),
            OrderedDict([
                ("type", "shop"),
                ("source_id", random.choice(["blacksmith","general_store","alchemist","rare_goods"])),
                ("rate_per_hour", 0.0),
                ("drop_rate", 0.0),
            ])
        ]
        if random.random() < 0.33:
            sources.append(OrderedDict([
                ("type", "dungeon_drop"),
                ("source_id", random.choice(dungeons)),
                ("rate_per_hour", 0.0),
                ("drop_rate", round(random.uniform(5.0, 18.0), 2)),
            ]))
        item = OrderedDict([
            ("id", _id),
            ("name", name),
            ("type", "crafting_material"),
            ("material_type", mtype),
            ("rarity", r),
            ("stack_size", 999),
            ("value", gold_value(r, 3, 45)),
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
        assert validate_category_name("materials", name)
        out.append(item)
    return out

# ---------------- Main ----------------
def main():
    random.seed(RNG_SEED)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    data = OrderedDict([
        ("version", "1.0"),
        ("categories", OrderedDict([
            ("weapons", gen_weapons(TOTAL_PER_CATEGORY)),
            ("armor", gen_armor(TOTAL_PER_CATEGORY)),
            ("accessories", gen_accessories(TOTAL_PER_CATEGORY)),
            ("consumables", gen_consumables(TOTAL_PER_CATEGORY)),
            ("materials", gen_materials(TOTAL_PER_CATEGORY)),
            ("rarity_multipliers", RARITY_MULT),
            ("rarity_colors", RARITY_COLORS),
        ]))
    ])

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ Wrote {OUTPUT_PATH} with {TOTAL_PER_CATEGORY*5} items (category-safe names).")

if __name__ == "__main__":
    main()
