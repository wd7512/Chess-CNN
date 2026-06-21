# Vision-Driven Chess Agent — Design Document

**Date:** 2026-06-21
**Author:** OWL
**Repo:** `wd7512/Chess-CNN`
**Final gate:** End-to-end test — a full game of chess played autonomously inside Docker against a live opponent on Lichess

---

## Goal

Replace Chess-CNN's macOS-only screen capture (mss) and click automation (pyautogui) with Playwright running in Docker. Keep the CNN for piece classification and the engine for chess logic — they work fine. Everything else gets replaced with DOM-aware, cross-platform equivalents.

**Final gate criteria:**
- [ ] Script runs inside Docker (no macOS-only dependencies)
- [ ] Plays a full game (all moves, start to checkmate/resign/draw) against a live opponent
- [ ] No human intervention during the game
- [ ] Game result is logged (win/loss/draw, move count, errors)
- [ ] Reproducible: `docker build && docker run` is all that's needed

---

## What Stays, What Goes

| Component | Old (src.py) | New | Why |
|-----------|-------------|-----|-----|
| Screen capture | `mss` (macOS only) | Playwright `page.screenshot()` | Cross-platform, Docker-friendly |
| Board detection | `cv2.matchTemplate` with `Blank_Board.png` (brittle, site-specific) | DOM: get board element bounds from Lichess | Reliable, no template image needed |
| Board extraction | Crop from screenshot using template match rect | Crop from screenshot using DOM element rect | Same OpenCV pipeline, better input |
| Orientation | MSE on rightmost column vs `blank_white.png`/`blank_black.png` (brittle) | DOM: read `.orientation-white` / `.orientation-black` class | Ground truth from the site itself |
| Piece classification | CNN (`Piece_Classifier.h5`) — 64 tiles × 25×25 grayscale | **UNCHANGED** — CNN does one thing well | Fast (<1ms), local, no API cost |
| FEN assembly | `undo_prepare_fen()` | **UNCHANGED** | Works correctly |
| Engine | `min_maxN_pruned` depth 3 | **UNCHANGED** (fix: opening book at root only) | Fast (<0.2s), deterministic |
| Click execution | `pyautogui.click` with manual coordinate math (buggy for black) | Playwright `page.mouse.click` with fixed coordinate math | Cross-platform, no display needed |
| Move verification | Screenshot + re-classify (expensive, slow) | DOM: check `.selected` class + board state change | Free, instant, reliable |
| Opponent detection | Template match `new_opp.png` (uncommitted file) | DOM: wait for turn indicator selector | No uncommitted dependencies |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN LOOP (chess_agent.py)                                 │
│                                                             │
│  0. PAGE STATE DETECTOR                                     │
│     - URL + DOM check: login | lobby | game | game_over     │
│     - Login → ABORT: "Cookies expired"                     │
│     - Lobby → ABORT: "No game in progress"                 │
│     - Game over → log result, exit                          │
│                                                             │
│  while not game_over and step < MAX_STEPS:                  │
│                                                             │
│    1. WAIT for our turn                                     │
│       - DOM: wait for turn indicator selector               │
│       - DOM: wait for board stability (no animation)        │
│       - Timeout: 60s → diagnostic screenshot → abort        │
│                                                             │
│    2. SCREENSHOT                                            │
│       - Playwright page.screenshot() → PNG                  │
│       - Save to /app/screenshots/step_N.png                 │
│                                                             │
│    3. EXTRACT BOARD                                         │
│       - DOM: get board element bounding rect (x, y, w, h)  │
│       - OpenCV: crop screenshot to board rect               │
│       - OpenCV: resize to 200×200                           │
│                                                             │
│    4. CLASSIFY PIECES (CNN)                                 │
│       - Split 200×200 → 64 tiles of 25×25                  │
│       - Run each tile through Piece_Classifier.h5           │
│       - Convert 64 labels → FEN string                      │
│                                                             │
│    5. OVERRIDE ORIENTATION FROM DOM                         │
│       - Read .orientation-white/.orientation-black class     │
│       - Apply FEN rank flip if playing as black             │
│                                                             │
│    6. OVERRIDE ACTIVE COLOR FROM DOM                        │
│       - Read turn indicator from DOM (ground truth)         │
│       - Override FEN active color field                     │
│                                                             │
│    7. ENGINE: pick_move(FEN) → move_uci                     │
│       - min_maxN_pruned(board, depth=3)                     │
│       - Opening book lookup at root only                    │
│       - SANITY: is move legal on reported FEN?              │
│         If not → retry from step 3 (board was misread)      │
│                                                             │
│    8. COMPUTE CLICK COORDINATES                             │
│       - Parse move_uci → source square, dest square         │
│       - Map algebraic → pixel using board rect + orientation│
│       - Fixed math (corrects black perspective bug)         │
│                                                             │
│    9. DOM VERIFY: click + confirm                           │
│       - Playwright: mouse.click(source_x, source_y)         │
│       - DOM: wait for .selected class on source (2s)        │
│       - Playwright: mouse.click(dest_x, dest_y)             │
│       - DOM: wait for .selected to disappear (3s)           │
│       - DOM: compare piece positions before vs after        │
│       - If board unchanged → retry from step 8              │
│       - If 3 consecutive failures → abort                   │
│                                                             │
│   10. LOG step, increment counter                           │
│                                                             │
│  End: log game result, save PGN                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Why |
|-----------|---------------|-----|
| CNN (`Piece_Classifier.h5`) | Classify 25×25 tile → piece label (13 classes) | Fast (<1ms), local, no API cost, does one thing well |
| OpenCV | Crop board from screenshot, resize to 200×200, split into 64 tiles | Standard image processing, works on any platform |
| DOM | Board location, orientation, turn indicator, selection verification, game state | Free, instant, ground truth from the site |
| Engine (`min_maxN_pruned`) | Chess logic: what move to play | Deterministic, fast (<0.2s at depth 3) |
| Playwright | Browser control: screenshot, click, wait for selectors, cookie injection | Cross-platform, Docker-friendly, no display needed |

---

## File Structure

```
Chess-CNN/
├── docs/
│   ├── AUDIT.md                    # existing audit
│   ├── VISION_AGENT_DESIGN.md      # this file
│   └── E2E_TEST.md                 # e2e test plan + results
├── src/
│   ├── chess_agent.py              # main loop, orchestration
│   ├── board_extractor.py          # OpenCV: crop, resize, split tiles
│   ├── piece_classifier.py         # CNN: load model, classify 64 tiles
│   ├── fen_assembler.py            # 64 labels → FEN string
│   ├── click_mapper.py             # algebraic square → pixel coordinate
│   ├── engine_client.py            # wraps Intermediate_Engines
│   ├── dom_verify.py               # Playwright DOM verification
│   └── config.py                   # selectors, paths, tuning
├── Models/
│   └── Piece_Classifier.h5         # CNN model (kept)
├── baron30.bin                     # opening book (kept, tested working)
├── Intermediate_Engines.py         # engine (kept, with fixes)
├── tests/
│   ├── test_board_extractor.py     # mock screenshot → tiles
│   ├── test_piece_classifier.py    # mock tiles → labels
│   ├── test_fen_assembler.py       # labels → FEN
│   ├── test_click_mapper.py        # algebraic → pixel (both orientations)
│   ├── test_engine_client.py       # FEN → move, opening book fix
│   ├── test_dom_verify.py          # mock Playwright page
│   └── test_e2e_smoke.py           # mock everything, 5-move loop
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Components

### config.py
```python
LICHESS_URL = "https://lichess.org"
MAX_STEPS = 200
ENGINE_DEPTH = 3
COOKIE_FILE = "lichess_cookies.json"
MODEL_PATH = "Models/Piece_Classifier.h5"
BOOK_PATH = "baron30.bin"
SELECTORS = {
    "board": ".main-board",
    "turn_indicator": ".rclock-turn",
    "selected_square": ".selected",
    "game_over": ".game-over",
    "orientation_white": ".orientation-white",
    "orientation_black": ".orientation-black",
}
```

### board_extractor.py
- `get_board_rect(page, selectors) → {x, y, w, h}` — DOM element bounds
- `crop_board(image, rect) → 200×200 ndarray` — OpenCV crop + resize
- `split_tiles(image_200) → list[64 tiles]` — 25×25 grayscale tiles

### piece_classifier.py
- `load_model(path)` — load `Piece_Classifier.h5` once at startup
- `classify_tiles(tiles) → list[64 labels]` — batch forward pass
- `one_hot_to_label(arr) → str` — existing function from src.py

### fen_assembler.py
- `labels_to_fen(labels, orientation) → fen_string` — existing `undo_prepare_fen` logic
- Handles rank flip for black orientation

### click_mapper.py
- `square_to_pixel(square, board_rect, orientation) → (x, y)`
- Fixes the black perspective bug from the audit (was `y + w` instead of `y + h`)

```python
def square_to_pixel(square, board_rect, orientation):
    col = ord(square[0]) - ord('a')  # a=0, ..., h=7
    row = 8 - int(square[1])          # 8→0, 1→7
    if orientation == "black":
        col = 7 - col
        row = 7 - row
    sq = board_rect['width'] / 8
    return (
        board_rect['x'] + (col + 0.5) * sq,
        board_rect['y'] + (row + 0.5) * sq
    )
```

### engine_client.py
- `pick_move(fen, depth=3) → move_uci`
- Wraps `min_maxN_pruned` from `Intermediate_Engines.py`
- Opening book lookup at root only (fix from audit: was at every node)
- <0.2s per move (benchmarked)

### dom_verify.py
- `detect_page_state(page) → 'login' | 'lobby' | 'game_waiting' | 'game_our_turn' | 'game_over'`
- `wait_for_our_turn(page) → None`
- `wait_for_board_stability(page) → None`
- `get_orientation(page) → 'white' | 'black'` (from DOM class)
- `get_active_color(page) → bool` (from turn indicator — ground truth)
- `click_square(page, x, y) → bool` (click + verify .selected class)
- `get_board_state(page) → piece_positions` (for before/after comparison)
- `is_game_over(page) → bool`

### chess_agent.py
- Page state detector → abort with actionable message if not in game
- Main loop orchestrating all components
- Cookie injection on startup
- Logging each step (screenshot, FEN, move, retries, result)
- Game result output (PGN + JSON summary)
- Cross-move consistency: verify board changed after each move

---

## Authentication: Cookie Injection

1. Human exports Lichess cookies from local browser (EditThisCookie or dev tools)
2. Saves as `lichess_cookies.json` in project directory
3. Script loads on startup: `context.add_cookies(json.load('lichess_cookies.json'))`
4. Navigates to lichess.org — already logged in
5. Fully headless for the entire game

No Xvfb, no VNC, no display infrastructure. Cookies mounted as Docker volume.

---

## Docker Setup

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy
WORKDIR /app
RUN apt-get update && apt-get install -y libgl1-mesa-glx  # OpenCV headless
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium
COPY src/ ./src/
COPY Models/ ./Models/
COPY baron30.bin .
COPY Intermediate_Engines.py .
CMD ["python", "src/chess_agent.py"]
```

```bash
docker build -t chess-agent .
docker run -v "$(pwd)/lichess_cookies.json:/app/lichess_cookies.json" chess-agent
```

---

## Per-Move Timing Budget

| Step | Time | Notes |
|------|------|-------|
| Wait for turn (DOM) | 0-60s | Opponent-dependent |
| Screenshot (Playwright) | <0.5s | |
| Board extraction (OpenCV) | <0.1s | Crop + resize |
| Piece classification (CNN) | <0.01s | 64 tiles, single forward pass |
| FEN assembly | <0.01s | |
| Engine | <0.2s | Depth 3, alpha-beta |
| Click execution + verify | 2-3s | DOM waits for selection |
| **Total (excluding opponent)** | **~3-4s** | vs ~10-20s with vision API |

No API calls. No network latency. The entire pipeline is local.

---

## End-to-End Test Plan

### Phase 1: Unit tests (no Docker, no browser)
- `test_board_extractor.py`: mock screenshot → correct tiles
- `test_piece_classifier.py`: mock tiles → correct labels
- `test_fen_assembler.py`: labels → FEN (both orientations)
- `test_click_mapper.py`: algebraic → pixel (both orientations, verifies black perspective fix)
- `test_engine_client.py`: FEN → move, opening book at root only
- `test_dom_verify.py`: mock Playwright page, test state machine
- `test_e2e_smoke.py`: mock everything, 5-move game loop

### Phase 2: Integration test (Docker, mock DOM)
- Build Docker container
- Run with a local HTML page that mimics Lichess DOM structure
- Verify full loop: screenshot → extract → classify → engine → click → verify
- Target: 10 moves without error

### Phase 3: E2E test (Docker, real browser, real game)
- Prerequisites:
  - Lichess account + exported cookies
  - Opponent: another bot, a friend, or an open challenge (casual/unrated)
- Run: `docker run -v cookies.json:/app/cookies.json chess-agent`
- Success criteria:
  - Game completes (checkmate, resign, or draw)
  - No human intervention during play
  - All moves logged
  - Game result recorded

---

## Known Risks

| Risk | Mitigation |
|------|-----------|
| CNN misclassifies edge tiles (border contamination from audit) | Acceptable for learning project; center tiles are reliable |
| Lichess DOM selectors change | Centralized in config.py; easy to update |
| Board element not found | Page state detector → abort with actionable message |
| Castling rights wrong on inferred FEN | Always clear castling rights (CNN can't see castling state) |
| 3 consecutive move failures | Abort with full log rather than desync cascade |
| Black perspective click math wrong | Unit test `test_click_mapper.py` verifies both orientations |
| Opening book at every node (audit fix) | Move `reader.get()` to root-only check |

---

## Success Metrics

- **Primary:** Full game played autonomously in Docker → pass/fail
- **Secondary:**
  - Move execution success: >90% of clicks verified on first try
  - Average move time (our side): <5s (excluding opponent)
  - Zero unrecoverable desyncs

---

## Out of Scope

- Improving engine strength (depth 3 is fine for learning)
- Supporting multiple chess sites (Lichess only for v1)
- Real-time games with clock pressure (unrated/casual only)
- GUI or web interface (CLI logging only)
- Full pre-game automation (cookie injection + manual game start is Phase 1)
- Fixing CNN edge tile accuracy (requires retraining or better board cropping)
