# Fantasy Item Catalog Generator (Godot 4.4, D20‑inspired)

A deterministic Python generator that creates a **single, pretty‑formatted JSON** with **1000+ game items** for Godot 4.4 projects. Items are split evenly across categories (weapons, armor, accessories, consumables, materials), follow a strict schema (matching `Example.json`), and include **image paths** under `res://assets/textures/<category>/<id>.png`.

---

## TL;DR

```bash
python3 generate_items.py
# → writes pretty JSON to assets/data/items.json with 1000+ items
```

* IDs auto‑match names → `"Dragon Silk"` → `dragon_silk`.
* Names **always** match category (e.g., *Silk* → material, never weapon).
* Consumables use your exact `effect` block (with `instant`, `duration`, and `stats_affected`).
* Includes `rarity_multipliers` and `rarity_colors` so the data mirrors your original schema.

---

## Why this exists

Large item catalogs are tedious and error‑prone. This generator:

* keeps the JSON stable and readable for code reviews,
* enforces naming/category consistency,
* provides D20‑flavored rarity scaling out of the box,
* integrates directly with Godot via `res://` image paths.

---

## Requirements

* **Python 3.9+** (tested with 3.11)
* **Godot 4.4** (optional; for loading/previewing the data)

---

## Quick Start

1. Place **`generate_items.py`** in your repository root.
2. Ensure these folders exist (icons are optional but recommended):

   ```
   res://assets/textures/weapons/
   res://assets/textures/armor/
   res://assets/textures/accessories/
   res://assets/textures/consumables/
   res://assets/textures/materials/
   res://assets/data/
   ```
3. Run the script:

   ```bash
   python3 generate_items.py
   ```
4. Output: **`assets/data/items.json`** (pretty, readable, \~1000 items).

> ℹ️ The script is deterministic via `RNG_SEED`. Change the seed to regenerate a fresh catalog while keeping the same structure.

---

## Data Schema

The JSON mirrors `Example.json`. High‑level shape:

```jsonc
{
  "version": "1.0",
  "categories": {
    "weapons": [ /* weapon items */ ],
    "armor": [ /* armor items */ ],
    "accessories": [ /* accessory items */ ],
    "consumables": [ /* consumables */ ],
    "materials": [ /* crafting materials */ ],
    "rarity_multipliers": { /* as provided */ },
    "rarity_colors": { /* as provided */ }
  }
}
```

### Weapon item example

```json
{
  "id": "iron_sword",
  "name": "Iron Sword",
  "type": "weapon",
  "weapon_type": "sword",
  "rarity": "common",
  "level_requirement": 1,
  "stats": {
    "attack": 24,
    "strength_bonus": 1,
    "dexterity_bonus": 0,
    "constitution_bonus": 0,
    "intelligence_bonus": 0,
    "wisdom_bonus": 0,
    "charisma_bonus": 0,
    "critical_chance": 3,
    "critical_damage": 120
  },
  "special_effects": [],
  "value": 110,
  "durability": 100,
  "crafting": {
    "recipe_id": "rcp_iron_sword",
    "materials": {"iron_ingot": 2, "leather_strip": 1}
  },
  "shop_availability": ["blacksmith", "general_store"],
  "image": "res://assets/textures/weapons/iron_sword.png"
}
```

### Consumable item example (your required effect block)

```json
{
  "id": "greater_health_potion",
  "name": "Greater Health Potion",
  "type": "consumable",
  "consumable_type": "potion",
  "rarity": "uncommon",
  "effect": {
    "type": "heal",
    "value": 350,
    "duration": 0,
    "instant": true,
    "stats_affected": {
      "health": 350,
      "mana": 0,
      "strength": 0,
      "dexterity": 0,
      "constitution": 0,
      "intelligence": 0,
      "wisdom": 0,
      "charisma": 0
    }
  },
  "stack_size": 99,
  "value": 60,
  "crafting": {
    "recipe_id": "rcp_greater_health_potion",
    "materials": { "healing_herb": 3, "pure_water": 1, "luminescent_moss": 1 }
  },
  "shop_availability": ["alchemist"],
  "description": "A potent brew that restores more health.",
  "image": "res://assets/textures/consumables/greater_health_potion.png"
}
```

### Material item example

```json
{
  "id": "dragon_silk",
  "name": "Dragon Silk",
  "type": "crafting_material",
  "material_type": "cloth",
  "rarity": "rare",
  "stack_size": 999,
  "value": 35,
  "sources": [
    {"type": "territory_income", "source_id": "tannery", "rate_per_hour": 3.2, "drop_rate": 0.0},
    {"type": "shop", "source_id": "rare_goods", "rate_per_hour": 0.0, "drop_rate": 0.0}
  ],
  "description": "Luxurious cloth favored for masterwork gear.",
  "image": "res://assets/textures/materials/dragon_silk.png"
}
```

---

## Category Safety (names always match type)

To avoid mismatches like **“Dragon Silk”** being generated as a weapon, the generator uses:

* **Category‑specific noun lexicons** (e.g., weapons contain *Sword/Axe/Spear…*, materials contain *Silk/Shard/Crystal/Ingot/Ore…*), and
* A **validator** that asserts each item’s name includes a noun appropriate to its category. If a mismatch would occur, it’s caught during generation.

---

## Rarity & Scaling

D20‑flavored stat multipliers:

| Rarity    | Multiplier |
| --------- | ---------- |
| Common    | 1.0        |
| Uncommon  | 1.5        |
| Rare      | 2.5        |
| Epic      | 4.0        |
| Legendary | 6.5        |

* **Weapons:** attack scales by multiplier; crit chance/damage increase with rarity.
* **Armor:** defense + elemental resistances increase with rarity.
* **Accessories:** stat bonuses + regen + potential XP bonus.
* **Consumables:** `value`/`duration`/`potency` scale with rarity.

---

## Image Paths

Every item includes a PNG image path ready for Godot `load()`:

```
res://assets/textures/weapons/<id>.png
res://assets/textures/armor/<id>.png
res://assets/textures/accessories/<id>.png
res://assets/textures/consumables/<id>.png
res://assets/textures/materials/<id>.png
```

> Ensure your filenames match the generated `id` exactly.

---

## Godot Integration (example)

Minimal loader to read and show an item card.

**Scene tree (UI sample):**

```
InventoryView (Control)
├─ ItemCard (Control)
│  ├─ Icon (TextureRect)
│  ├─ Name (Label)
│  └─ Stats (Label)
```

**GDScript (drop onto `InventoryView`):**

```gdscript
extends Control

var items := {}

func _ready():
    var f := FileAccess.open("res://assets/data/items.json", FileAccess.READ)
    if f:
        items = JSON.parse_string(f.get_as_text())
        f.close()
    _show_first_weapon()

func _show_first_weapon():
    var weapon = items["categories"]["weapons"][0]
    $ItemCard/Name.text = weapon.name
    $ItemCard/Stats.text = "ATK: %d  Crit: %d%% x%d" % [
        weapon.stats.attack,
        weapon.stats.critical_chance,
        weapon.stats.critical_damage
    ]
    var tex: Texture2D = load(weapon.image)
    if tex: $ItemCard/Icon.texture = tex
```

---

## Customization

* **Change item counts:** edit `TOTAL_PER_CATEGORY`.
* **New shops:** add to the `SHOPS` list and to the `shops_for()` logic if needed.
* **New effects:** add labels to `SPECIAL_EFFECT_POOL` and expand the formatting rules.
* **Balance:** tweak `RARITY_MULT`, crit ranges, elemental resist ranges, and gold value ranges.
* **Determinism:** adjust `RNG_SEED` to regenerate a different but valid dataset.

---

## Project Structure (suggested)

```
.
├─ generate_items.py
├─ assets/
│  └─ data/
│     └─ items.json
└─ res/
   └─ assets/
      └─ textures/
         ├─ weapons/
         ├─ armor/
         ├─ accessories/
         ├─ consumables/
         └─ materials/
```

> Note: If your repo mirrors Godot’s `res://` at the root, you may keep `assets/` under `res://assets/` instead.

---

## Troubleshooting

* **Item shows wrong image / missing icon** → Ensure the file exists at the expected `image` path and the filename equals the item `id` (lowercase with underscores).
* **JSON not pretty‑printed** → The script writes with `indent=2`; if this fails, check write permissions or path existence.
* **Mismatched categories** → The validator should prevent this. If you hand‑edit names, keep category nouns (e.g., *Silk, Ingot* for materials).

---

## Contributing

1. Fork → create a feature branch.
2. Make changes (add cores/effects/shops, tweak balance).
3. Run `python3 generate_items.py` and verify `items.json`.
4. Open a PR describing changes and example items.

### Coding style

* Prefer `OrderedDict` for stable key order in JSON.
* Keep functions pure where possible; avoid global state except for name uniqueness.

---

## License

MIT (proposed). Replace with your preferred license before publishing.

---

## Changelog (example)

* **1.0.0** – Initial release: deterministic generator, 5 categories × 200, category‑safe names, D20 scaling, pretty JSON.

---

## Acknowledgments

* Inspiration: classic D20 itemization and Godot’s straightforward `res://` resource pipeline.
