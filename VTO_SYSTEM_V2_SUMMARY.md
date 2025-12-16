# VTO SYSTEM V2 - FINAL PRODUCTION SYSTEM
## Date: December 8, 2024

## KEY DISCOVERIES

### What Works:
- **SECONDARY ANCHOR: YES** - Locks in model face/appearance
- **FINAL ANCHOR: NO** - Was causing priority item to drop
- **Temperature: 0.0** - Deterministic
- **Accessories in base 4: YES** - Fixed to allow sunglasses, berets etc

### Image Count: 6 total
1. User photo (MODEL)
2. Item 1 (shoes - lowest priority)
3. Item 2 (bottom) + SECONDARY ANCHOR duplicate
4. Item 3 (top)
5. Item 4 (priority - outerwear/dress/accessory)

### Success Rate: ~66-75%
- 2-3 out of 3 runs are "perfect"
- Recommend: Regenerate button in frontend
- Cost per attempt: ~$0.04

---

## PROMPT STRUCTURE
```
"Professional fashion photo. Light grey studio backdrop. Front-facing pose."
"MODEL:", user_photo, user_description

[GARMENT ONLY: SHOES]:", shoes_img, json
[GARMENT ONLY: BOTTOM]:", bottom_img, json
"SECONDARY ANCHOR:", bottom_img  <-- Helps lock in model

[GARMENT ONLY: TOP]:", top_img, json

MASTER EXCLUSIONS block...

### FINAL PRIORITY ITEM FUSION (MUST APPEAR)
The model is now wearing: shoes, bottom, top.
Your FINAL TASK is to add the {priority_type}.

PRIORITY ITEM (ITEM 4 OF 4) - {TYPE}: priority_img
CRITICAL: This garment ABSOLUTELY MUST BE INCLUDED.
{json}
STRICT: MATCH SOURCE IMAGE EXACTLY...

ACTION: Generate now with ALL 4 items visible.
```

---

## BODY TYPE ROUTING

| Body Type | System | First Call | Notes |
|-----------|--------|------------|-------|
| Slim/Average | vto_production_v2.py | 4 items | No body type prompt |
| Curvy/Plus | Same + body prompt | 2 items | Segmented garments required |

---

## KNOWN LIMITATIONS

1. **Collar details** - Sometimes changes lapel/stand collar
2. **Button count** - May vary from source
3. **Trouser pooling** - Doesn't always match "pooling at floor"
4. **Random model** - ~1 in 3 runs might get wrong face (face swap fixes most)

---

## VALIDATION (Optional)
```python
def validate_vto_background(image, tolerance=50):
    # Check corner pixels are grey (180-240 range)
    # Returns True if valid, False to auto-regenerate
```

---

## COST ANALYSIS

- Per VTO attempt: ~$0.04
- With regenerate (avg 1.5 attempts): ~$0.06
- 50 VTOs for £4.99: $3.00 cost → $3.30 profit ✅

---

## FILES

- `vto_production_v2.py` - Current production system
- `vto_production_final.py` - Previous version (7 images, more jacket drops)
- `vto_production_layermap.py` - Same as v2 (working copy)
