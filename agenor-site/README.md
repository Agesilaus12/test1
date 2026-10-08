# Agenor Logistics — saved site copy

A complete, self-contained copy of the design and content of
https://agenorlogistics.com/ (captured 2026-10-08).

Everything renders exactly like the original: same layout, color palette
(navy / aqua / sand / ink / mist), Roboto + JetBrains Mono typography, the
hero cinemagraph, the sailing-schedule table, and all section copy.

## Contents
- `index.html` — the full homepage markup
- `_astro/index.r7Eugx_X.css` — the compiled stylesheet (Tailwind build)
- `logo.png`, `hero.webp`, `hero.mp4`, `hero.webm`, `og.jpg`, `favicon.ico` — assets

Fonts load from the Google Fonts CDN (Roboto, JetBrains Mono), exactly as the
original does.

## View it locally
Serve the folder from its root (absolute `/...` paths need a web root):

```bash
cd agenor-site
python3 -m http.server 8099
# open http://localhost:8099/
```

Opening `index.html` directly with `file://` will not find the `/`-rooted
CSS and assets — use the local server above (or any static host).
