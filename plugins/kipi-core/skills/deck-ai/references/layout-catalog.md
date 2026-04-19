# Layout Catalog

Layouts available to the `deck-ai` skill. The generator picks one per slide.
To force a layout, add `<!-- layout: <name> -->` at the top of the source slide.

## Layouts

| Name | When to use | Has image slot |
|---|---|---|
| `cover` | First slide. Big title, subtitle, optional hero image. | Optional |
| `center` | Single short statement or question. <25 words body. | No |
| `statement` | Full-bleed single sentence. Use for emphasis. | No |
| `two-cols` | Comparing two things side by side. | No |
| `image-right` | Concept + supporting visual (image on right). | Yes |
| `image-left` | Concept + supporting visual (image on left). | Yes |
| `quote` | Direct quote from a book / person. | No |
| `end` | Last slide. Thanks / homework / CTA. | No |
| `default` | Anything else. Title + body. | No |

## Image placeholders

Layouts with an image slot accept `{{IMG:keyword}}` in the slide body. The
`fetch_images.py` script replaces each placeholder with an Unsplash URL
found via keyword search. Keywords should be 1-3 words, concrete nouns.

Good: `{{IMG:mountain sunrise}}`, `{{IMG:koi fish}}`, `{{IMG:student writing}}`
Bad: `{{IMG:feeling of loneliness}}`, `{{IMG:theme of redemption}}`

## Layout pick rules (v1 deterministic)

Applied in order. First match wins.

1. Explicit hint (`<!-- layout: X -->`) → X
2. Slide index 0 → `cover`
3. Last slide with "homework" / "thanks" / "end" in title → `end`
4. Body contains "Anime anchor" or "Example:" callout → `image-right`
5. Body word count < 25 → `center`
6. Otherwise → `default`

To upgrade to LLM-driven layout choice: replace `pick_layout` in `generate.py`
with a prompt that enumerates the layouts and asks the model to choose per slide.
Keep the rule-based version as a fallback.
