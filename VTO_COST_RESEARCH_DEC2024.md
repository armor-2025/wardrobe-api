# VTO Cost Research - December 3, 2024

## Summary of Tests

| Approach | Description Cost | VTO Cost | Total | Quality |
|----------|-----------------|----------|-------|---------|
| No descriptions | $0 | $0.039 | $0.039 | ❌ Inconsistent colors |
| Gemini 2.5 descriptions | $0.039 | $0.039 | $0.078 | ✅ Best quality |
| GPT-4o-mini (low-res) | $0.002 | $0.039 | $0.041 | ⚠️ Jacket color slightly off |

## Key Findings

1. **Descriptions ARE needed** for consistency - without them, 3 runs = 3 different jacket colors
2. **Gemini follows TEXT over images** when they conflict - wrong description = wrong clothes
3. **GPT-4o-mini low-res can't accurately see color shades** - calls dark indigo "medium wash"
4. **Gemini 2.5 descriptions are most accurate** - reads text, identifies brands, gets colors right

## Best Prompt for GPT-4o-mini (if using)
```
Describe each clothing item for recreation. 

Include:
- Brand name if visible
- Item type and style
- Any text/logos - transcribe EXACTLY
- Construction: neckline, closure, pockets, waistband

DO NOT describe colors or shades - the AI will see the colors from the images.
```

## Files

- `vto_complete_system_FINAL_PERFECT_NOV8_2024.py` - Working version with Gemini 2.5 descriptions ($0.078)
- `vto_FINAL_PRODUCTION_DEC2024.py` - GPT-4o-mini version ($0.041) - jacket color issues

## TODO

- Test with different clothes to see if jacket is edge case
- Try GPT-4o-mini HIGH detail for colors (costs more)
- Consider hybrid: GPT for structure, let Gemini see colors from images
