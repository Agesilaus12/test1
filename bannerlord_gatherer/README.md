# Bannerlord Online — Gathering Bot

A local, screen-reading automation bot that runs a continuous gather → collect →
deposit loop for wood/stone gathering in Bannerlord Online. It reads the game's
**Alt-key text overlay** with OCR to find resource nodes and read your carry
capacity, simulates keyboard/mouse input to harvest, and loops.

An **optional Claude vision "advisor"** plugs in for the hard perception calls
(when local OCR can't find a target or the bot gets stuck) so you get AI-quality
scene understanding without paying API latency on every frame.

> ⚠️ **Read this first.** Automating gameplay in an online multiplayer game like
> Bannerlord Online almost certainly violates its Terms of Service and can get
> your account **banned**. It also affects other players and the shared economy.
> This project is provided for educational/personal-automation purposes — you are
> responsible for how you use it. Nothing here exploits, hacks, or modifies the
> game; it only reads the screen and simulates a human's keyboard/mouse, but that
> does not make it ToS-compliant.

---

## How it works

```
        ┌──────────────────────────────────────────────────────────┐
        │                     main.py loop                          │
        │   (F9 emergency stop releases all keys instantly)         │
        └───────────────┬──────────────────────────────────────────┘
                        │ ticks a state machine
                        ▼
   SETUP → SEEK_RESOURCE → NAVIGATE → GATHER → COLLECT → CHECK_CAPACITY
                ▲                                              │
                │                                     full ────┘
                │                                     ▼
                └──────────── DEPOSIT ← RETURN ←──────┘

   Perception (each state):
     • hold ALT → screen-capture (mss) → OCR (EasyOCR)  ← fast, local, free
     • find target labels ("tree", "rock", "deposit", …) → pixel position
     • read "84 / 100" capacity widget → know when you're full
     • frame-diff while moving → detect being stuck

   When local perception fails (no target / stuck repeatedly):
     • send a downscaled screenshot to Claude (Opus 4.8 vision)
     • get a structured {action, target_direction} answer back
```

| Layer | File | Job |
|---|---|---|
| Capture | `src/capture.py` | Fast region grab via `mss` |
| Vision (local) | `src/vision.py` | OCR the Alt overlay; find labels; parse capacity |
| Input | `src/controls.py` | DirectInput keys/mouse (`pydirectinput`) |
| Navigation | `src/navigation.py` | Turn-to-center + stuck detection/unstick |
| Advisor (AI) | `src/claude_advisor.py` | Claude vision for ambiguous scenes |
| Loop | `src/state_machine.py` | The gather cycle as explicit states |
| Entry | `src/main.py` | Wiring, emergency stop, dry-run |
| Calibration | `src/tools/region_picker.py` | Click to find UI pixel regions |

---

## Setup

1. **Python 3.10+** on the machine running the game (Windows; DirectInput is
   Windows-only). Install deps:
   ```bash
   pip install -r requirements.txt
   ```
   The first run downloads the EasyOCR models (~100 MB).

2. **Run the game windowed/borderless at 1920×1080** (or edit `config.yaml`
   to match your resolution).

3. **Calibrate the capacity region** — the one part you *must* get right:
   ```bash
   python -m src.tools.region_picker
   ```
   Hold Alt in-game first so the overlay is visible, screenshot it, then click
   the two corners around your carry/weight number. Paste the printed
   `{ left, top, width, height }` into `config.yaml` under `capacity.region`.

4. **Tune the label keywords** in `config.yaml` to match exactly what your
   Alt overlay prints for trees, rocks, the tool pickup, and the deposit point.

5. **Dry run first** (reads the screen, sends NO input — verify it finds your
   targets and reads capacity correctly):
   ```bash
   python -m src.main --dry-run
   ```

6. **Go live:**
   ```bash
   python -m src.main
   ```
   You have 3 seconds to focus the game window. **Press F9 to stop at any time.**

---

## Enabling the Claude advisor (optional)

The bot runs fully locally by default. To let Claude help when it's stuck:

```bash
pip install anthropic pydantic pillow
export ANTHROPIC_API_KEY=sk-ant-...     # your key
```

Then in `config.yaml`:
```yaml
advisor:
  enabled: true
  model: "claude-opus-4-8"
  effort: "low"          # fast/cheap perception call
  cooldown_s: 5.0        # never calls more often than this
  trigger_after_failed_reads: 3
```

It only fires after the local OCR has failed a few times in a row, and it's rate
limited by `cooldown_s`, so cost stays low. It returns a constrained JSON answer
(`action` + `target_direction`) that the state machine acts on.

---

## Tuning notes

- **Swing/collect counts** live in `config.yaml` → `gather` (3 swings/node,
  6 F-presses). Adjust `swing_interval_s` to your tool's animation length.
- **Stuck sensitivity** is `navigation.stuck_frame_diff`. Raise it if the bot
  thinks it's stuck while actually moving; lower it if it rams obstacles.
- **"Close enough to gather"** is a heuristic (label drops below 40% screen
  height). If it swings at air, increase that threshold in `state_machine.py`.

## Honest limitations

- **Navigation is heuristic, not real pathfinding.** It turns toward the target
  label and walks, with a back-up/strafe routine when stuck. It works well in
  open fields and poorly in cluttered terrain. The Claude advisor mitigates but
  doesn't eliminate this.
- **OCR depends on your overlay text.** If Bannerlord Online's Alt labels don't
  match the `labels` keywords, nothing will be found — calibrate them.
- **No anti-detection, intentionally.** This behaves like a naive macro. See the
  ToS warning above.
