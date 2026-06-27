# Strauss FDE Deck (HTML)

A 20-slide presentation deck, built as a single self-contained HTML design.
This is the **canonical, editable version of the deck** — formatting and design
live entirely inside the HTML file as inline styles.

## Files (keep all four together in this folder)

| File | Role |
|------|------|
| `Strauss FDE Deck.dc.html` | The deck. All 20 slides, all content, all styling (inline). **This is the file you edit.** |
| `deck-stage.js` | Slide-deck shell: scaling, keyboard nav, thumbnail rail, print-to-PDF. |
| `image-slot.js` | Drag-and-drop screenshot placeholders used on the three demo slides. |
| `support.js` | Runtime that renders the `.dc.html`. |

The deck references the three `.js` files by relative path, so they must stay in
the same folder as the HTML.

## Previewing it

Open `Strauss FDE Deck.dc.html` in a browser. Because it loads the local scripts
and Google Fonts, serve the folder rather than double-clicking the file:

```bash
cd deck
python3 -m http.server 8000
# then open http://localhost:8000/Strauss%20FDE%20Deck.dc.html
```

Navigate with ← / → arrow keys. The thumbnail rail (left edge) jumps between slides.

## Editing without breaking the design

- **Safe:** edit text, numbers, colors, and styles *inside* `Strauss FDE Deck.dc.html`.
  Every style is inline in that one file, so changes preserve the design.
- The slide markup is between `<x-import ...>` and `</x-import>`. Each slide is a
  `<section data-label="...">`. Tabular content (stakeholder map, KPIs, risks,
  etc.) is data-driven from the `class Component` block near the bottom of the
  file — edit those arrays to change that copy.
- **Avoid:** re-implementing the deck in another framework (React, a slide
  library, PowerPoint) unless you intend a full redesign — the look will drift.

## Design system (for reference)

- **Type:** Newsreader (serif headlines), Libre Franklin (sans body), IBM Plex Mono (labels/technical tokens).
- **Palette:** warm off-white `#F4EFE7` ground, ink `#221D17`, single brick-red accent `#B23B26` (`#CB5238` on dark). Dark cover/closing on `#1F1A14`.
- Sage `#5E7350` for positive/"tradeoff accepted" notes; amber `#B0791D` for caution.

## Export

- **PDF:** open in browser → Print → Save as PDF (one page per slide, handled automatically).
- **PowerPoint:** ask the design environment to export to `.pptx`.
