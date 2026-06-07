# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single project, `bannerlord_gatherer/` — a local screen-reading automation bot
that runs a continuous wood/stone gathering loop in the game **Bannerlord Online**.
It OCRs the game's Alt-key text overlay to find resource nodes and read carry
capacity, then simulates keyboard/mouse to harvest, and loops.

## Critical execution constraint

**The bot cannot run in a headless/cloud environment.** Its first action every
cycle is to screenshot the screen (`mss`) and send DirectInput keystrokes to a
live game window. It requires:
- **Windows** (`pydirectinput` / DirectInput is Windows-only), and
- a **real display** with the game running.

In a cloud container `mss` fails with `XError: Cannot connect to display`. When
asked to "run" the bot, do not attempt it in a sandbox — it will fail at screen
capture. Code can be written, edited, and `py_compile`-checked anywhere; only the
live run must happen on the user's Windows PC. Use `--dry-run` for any read-only
verification that still requires a display.

## Commands

All commands run from inside `bannerlord_gatherer/`:

```bash
pip install -r requirements.txt          # first run also downloads EasyOCR models (~100MB)
python -m src.main                        # run the bot (needs Windows + display + game)
python -m src.main --dry-run              # reads screen + OCR, sends NO input (verification)
python -m src.main --config path.yaml     # alternate config
python -m src.tools.region_picker         # calibrate UI pixel regions by clicking corners
python -m py_compile src/*.py src/tools/*.py   # syntax check (works headless)
```

There is no test suite, linter, or build step configured.

**Emergency stop:** the bot binds a global hotkey (default **F9**, `keys.emergency_stop`)
that halts the loop and releases all held keys.

## Architecture

The design is **local-first**: fast, free local perception drives a real-time
state machine, with an **optional Claude vision API "advisor"** consulted only
when local heuristics fail (no target found, or stuck repeatedly). The advisor is
rate-limited and runs at low effort to keep latency/cost down — it is a fallback,
never in the hot path.

Data flow each tick: **hold Alt → capture frame → OCR → act**.

| Module | Responsibility |
|---|---|
| `src/state_machine.py` | The gather cycle as an explicit `State` enum. Each state handler returns the next state, so `main`'s loop stays trivial. States: `SETUP → SEEK_RESOURCE → NAVIGATE → GATHER → COLLECT → CHECK_CAPACITY → (RETURN → DEPOSIT) → loop`. `_nav_target` ('resource'/'deposit') reuses the seek/navigate code for both finding nodes and returning to deposit. |
| `src/vision.py` | `OCRBackend` (EasyOCR, lazy-imported) → `Detection(text, cx, cy, confidence)`. `find_label` matches overlay text against keyword lists; `read_capacity` parses the "current/max" widget via regex. |
| `src/controls.py` | `Controls` wraps `pydirectinput`. All sleeps route through `_sleep`, which applies `±jitter_pct` so timings aren't metronomic. Centralizing jitter here is intentional. |
| `src/navigation.py` | Heuristic, **not** real pathfinding: turn toward the target's horizontal label position; detect "stuck" via frame-to-frame pixel diff while moving; `unstick()` backs up + strafes. |
| `src/capture.py` | `ScreenCapture` (mss) — `grab()` returns BGR frames; `crop()` slices absolute-screen sub-regions (e.g. the capacity widget). |
| `src/session.py` | `SessionLimiter` — max runtime cap + randomized human-like breaks. Pacing exists to make a single instance look less like a 24/7 script. |
| `src/claude_advisor.py` | `ClaudeAdvisor` — sends a downscaled screenshot to Claude (`messages.parse`, structured `Advice` output) and returns `{action, target_direction}`. Lazy-imports `anthropic`/`pydantic`/`PIL` and never crashes the loop on failure. |
| `src/config.py` | `Config` — dict subclass with attribute access; `load_config()` reads `config.yaml`. |
| `src/main.py` | Wiring + loop + F9 stop. `--dry-run` monkeypatches every public `Controls` method to a no-op (underscore-prefixed helpers like `_sleep` are preserved). |

### Key conventions

- **`config.yaml` is the single source of truth** for keys, swing/collect counts,
  timings, label keywords, the capacity OCR region+regex, session pacing, and
  advisor settings. Coordinates assume 1920×1080 and must be recalibrated per setup
  via `region_picker`.
- **Optional deps degrade gracefully.** `easyocr`, `anthropic`, `pydantic`, `PIL`
  are imported lazily so unrelated work and `py_compile` run without them.
- **The advisor is off by default** (`advisor.enabled: false`); it needs
  `ANTHROPIC_API_KEY` and uses model `claude-opus-4-8`.

## Important context

- **Branch:** active development is on `claude/keen-cray-D91bq`; `main` only has a
  placeholder README. The bot code lives on the feature branch.
- **ToS:** automating an online multiplayer game like Bannerlord Online violates
  its Terms of Service and risks an account ban. The README documents this; keep
  the warning intact and do not add anti-detection/evasion features.
