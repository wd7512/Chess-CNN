# Vision-Driven Chess Agent — Design Document

**Date:** 2026-06-21
**Author:** OWL
**Repo:** `wd7512/Chess-CNN`
**Final gate:** End-to-end test — a full game of chess played autonomously inside Docker against a live opponent on Lichess

---

## Goal

Replace Chess-CNN's brittle vision pipeline (template matching + CNN + manual coordinate math) with a multi-modal vision model that reads the board from screenshots and returns click actions. The engine stays unchanged.

**Final gate criteria:**
- [ ] Script runs inside Docker (no macOS-only dependencies)
- [ ] Plays a full game (all moves, start to checkmate/resign/draw) against a live opponent
- [ ] No human intervention during the game
- [ ] Game result is logged (win/loss/draw, move count, errors)
- [ ] Reproducible: `docker build && docker run` is all that's needed

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN LOOP (chess_agent.py)                                 │
│                                                             │
│  0. PAGE STATE DETECTOR                                     │
│     detect_page_state(page) → login | lobby | game | over   │
│     - Login page → ABORT: "Cookies expired"                │
│     - Lobby → ABORT: "No game in progress"                 │
│     - Game, not our turn → wait_for_our_turn()              │
│     - Game, our turn → enter loop                           │
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
│    3. VISION CALL 1: read_board(screenshot) → FEN          │
│       - Send image + prompt to OpenRouter vision model      │
│       - Parse JSON: {fen, orientation, confidence, notes}   │
│       - VALIDATE: legal position (kings, pawns, castling)   │
│       - If confidence != 'high': double-shot (2nd screenshot)│
│       - Retry up to 3x on failure                           │
│                                                             │
│    4. OVERRIDE ACTIVE COLOR FROM DOM                        │
│       - Read turn indicator from DOM (ground truth)         │
│       - Override FEN's active color field with DOM value    │
│       - This prevents wrong-active-color cascades           │
│                                                             │
│    5. ENGINE: pick_move(FEN) → move_uci                     │
│       - min_maxN_pruned(board, depth=3)                     │
│       - Opening book lookup at root only                    │
│       - SANITY: is move legal on reported FEN?              │
│         If not → retry step 3 (board was misread)           │
│                                                             │
│    6. VISION CALL 2: execute_move(screenshot, move)         │
│       - Send image + "click e2 then e4"                     │
│       - Parse JSON: {source: 'e2', dest: 'e4', reasoning}   │
│       - Map algebraic squares → pixel coords via grid math  │
│       - VALIDATE: coords within board bounding box          │
│       - Retry up to 3x on failure                           │
│                                                             │
│    7. DOM VERIFY: execute clicks + verify                   │
│       - click_source: mouse.click(x,y) → wait .selected     │
│       - click_dest: mouse.click(x,y) → wait .selected ↑     │
│       - compare DOM piece positions before vs after         │
│       - If board unchanged → retry from step 6              │
│       - If 3 consecutive failures → abort                   │
│                                                             │
│    8. LOG step, increment counter                           │
│                                                             │
│  End: log game result, save PGN                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Why |
|-----------|---------------|-----|
| Vision model | Spatial understanding: read board state, identify square locations | Good at visual pattern recognition |
| DOM | State detection: whose turn, game over, board changed, selection confirmed | Free, reliable, instant |
| Engine | Chess logic: what move to play | Deterministic, fast (<0.2s) |
| Playwright | Browser control: screenshot, click, wait for selectors | Cross-platform, Docker-friendly |

Each component does what it's best at. No component does another's job.

---

## File Structure

```
Chess-CNN/
├── docs/
│   ├── AUDIT.md                    # existing audit
│   ├── VISION_AGENT_DESIGN.md        # this file
│   └── E2E_TEST.md                 # e2e test plan + results
├── src/
│   ├── chess_agent.py              # main loop, orchestration
│   ├── vision.py                   # vision API calls (2-call split)
│   ├── engine_client.py            # wraps Intermediate_Engines
│   ├── dom_verify.py               # Playwright DOM verification
│   └── config.py                   # API key, model, selectors, tuning
├── Models/
│   ├── Piece_Classifier.h5         # kept for reference, not used
│   └── Orientation_Classifier.h5   # kept for reference, not used
├── baron30.bin                     # opening book (kept, tested working)
├── tests/
│   ├── test_vision.py              # vision call parsing + validation
│   ├── test_engine_client.py       # engine wrapper
│   ├── test_dom_verify.py          # DOM verification (mock page)
│   └── test_e2e_smoke.py           # smoke test: mock vision + engine
├── Dockerfile                      # based on playwright image
├── docker-compose.yml              # optional, for convenience
├── requirements.txt                # playwright, openai, python-chess
└── README.md                       # updated
```

---

## Components

### config.py
```python
OPENROUTER_API_KEY = "sk-..."
MODEL = "openrouter/anthropic/claude-sonnet-4"
LICHESS_URL = "https://lichess.org"
MAX_STEPS = 200
ENGINE_DEPTH = 3
ORIENTATION = "auto"  # "white" | "black" | "auto" (auto = DOM detection)
SELECTORS = {
    "board": ".main-board",
    "turn_indicator": ".rclock-turn",
    "selected_square": ".selected",
    "game_over": ".game-over",
    "orientation_white": ".orientation-white",
    "orientation_black": ".orientation-black",
}
```

### vision.py
- `read_board(image_path) → {fen, orientation, confidence, notes}`
  - Returns FULL FEN (all 6 fields) including castling rights
  - Returns orientation: "white" | "black"
  - Returns confidence: "high" | "medium" | "low"
  - Prompt enforces strict JSON schema with counter-examples
  - Handles markdown code fences, missing fields, commentary
- `execute_move(image_path, move_uci) → {source: 'e2', dest: 'e4', reasoning}`
  - Returns algebraic square names, NOT pixel coordinates
  - Script maps algebraic → pixels via grid math
- Handles OpenRouter API calls, JSON parsing, retries with backoff
- Double-shot on low confidence: take 2nd screenshot, compare FENs

### engine_client.py
- `pick_move(fen, depth=3) → move_uci`
- Wraps `min_maxN_pruned` from `Intermediate_Engines.py`
- Opening book lookup at root only (fix from audit: was at every node)
- Does NOT clear castling rights — vision model reports them accurately
- <0.2s per move (benchmarked: mid-game depth 3 = 0.19s)

### dom_verify.py
- `detect_page_state(page) → 'login' | 'lobby' | 'game_waiting' | 'game_our_turn' | 'game_over'`
- `wait_for_our_turn(page, selectors) → None`
- `wait_for_board_stability(page, selectors) → None`
- `get_orientation(page, selectors) → 'white' | 'black'` (from DOM class)
- `click_square(page, x, y, selectors) → bool` (click + verify .selected)
- `get_board_state(page, selectors) → piece_positions` (for before/after comparison)
- `is_game_over(page, selectors) → bool`

### chess_agent.py
- Page state detector → abort with actionable message if not in game
- Main loop orchestrating all components
- Board orientation detection: DOM → vision → config override (3-layer)
- Active color override from DOM turn indicator (ground truth)
- Logging each step (screenshot path, FEN, move, retries, result)
- Game result output (PGN + JSON summary)
- Cross-move consistency: verify next FEN matches expected post-move position

---

## Board Orientation Detection (3-layer)

1. **DOM** (primary): Check for `.orientation-white` / `.orientation-black` class on board element
2. **Vision model** (fallback): Ask in call 1 — "Is this board from white or black perspective?"
3. **Config override** (last resort): `ORIENTATION = "white"` in config.py

Validation: if first move fails (board unchanged), try flipping orientation and retry.

---

## Algebraic-to-Pixel Mapping

Vision model returns algebraic squares (`e2`, `e4`), not pixels. Script converts:

```python
def square_to_pixel(square, board_rect, orientation):
    """board_rect = {x, y, width, height} from DOM element"""
    col = ord(square[0]) - ord('a')  # a=0, b=1, ...
    row = 8 - int(square[1])          # 8→0, 7→1, ...
    if orientation == "black":
        col = 7 - col
        row = 7 - row
    sq = board_rect['width'] / 8
    return (
        board_rect['x'] + (col + 0.5) * sq,
        board_rect['y'] + (row + 0.5) * sq
    )
```

This fixes the black perspective bug from the audit (was `y + w` instead of `y + h`, wrong rank flip).

---

## Authentication: Cookie Injection

For Phase 1 (manual pre-game), no display server needed:

1. Human exports Lichess cookies from local browser (EditThisCookie extension or dev tools)
2. Saves as `lichess_cookies.json` in project directory
3. Script loads on startup: `context.add_cookies(json.load('lichess_cookies.json'))`
4. Navigates to lichess.org — already logged in
5. Fully headless for the entire game

No Xvfb, no VNC, no display infrastructure. Cookies mounted as Docker volume (not baked into image).

---

## Docker Setup

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
COPY baron30.bin .
COPY Intermediate_Engines.py .
CMD ["python", "src/chess_agent.py"]
```

```bash
docker build -t chess-agent .
docker run -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -v "$(pwd)/lichess_cookies.json:/app/lichess_cookies.json" \
  chess-agent
```

---

## End-to-End Test Plan

### Phase 1: Unit tests (no Docker, no API calls)
- `test_vision.py`: mock API responses, test JSON parsing + validation, FEN validation
- `test_engine_client.py`: test FEN → move, opening book, castling rights preserved
- `test_dom_verify.py`: mock Playwright page, test state machine logic
- `test_e2e_smoke.py`: mock vision + engine, run 5-move game loop

### Phase 2: Integration tests (Docker, mock API)
- Build Docker container
- Run with mocked vision responses (recorded real responses)
- Verify full loop: screenshot → vision → engine → DOM verify → repeat
- Target: 10 moves without error

### Phase 3: E2E test (Docker, real API, real game)
- Prerequisites:
  - Lichess account + exported cookies
  - OpenRouter API key with vision model access
  - Opponent: another bot, a friend, or an open challenge (casual/unrated)
- Run: `docker run -e OPENROUTER_API_KEY=... -v cookies.json:/app/cookies.json chess-agent`
- Success criteria:
  - Game completes (checkmate, resign, or draw)
  - No human intervention during play
  - All moves logged
  - Game result recorded

### Phase 4: Stress test (optional)
- Play 3+ games in sequence
- Track: win rate, average move time, vision error rate, retry rate

---

## Per-Move Timing Budget

| Step | Time |
|------|------|
| Wait for turn (DOM) | 0-60s (opponent-dependent) |
| Screenshot | <1s |
| Vision call 1 (read board) | 4-8s |
| Vision call 2 (execute move) | 4-8s |
| Engine | <0.2s |
| DOM verification | 2-3s |
| **Total (excluding opponent)** | **~10-20s** |
| **40-move game estimate** | **~7-13 min + opponent time** |

---

## Known Risks

| Risk | Mitigation |
|------|-----------|
| Vision model hallucinates FEN | Legal-position validation + double-shot on low confidence |
| Wrong active color from vision | DOM turn indicator overrides FEN active color |
| Vision model returns wrong squares | Board-bounds check + DOM verification retry |
| Board orientation wrong | 3-layer detection + flip-and-retry on first-move failure |
| Cookies expire mid-game | Page state detector catches login page → abort with message |
| Lichess DOM selectors change | Centralized in config.py; easy to update |
| Vision model JSON malformed | Post-hoc parsing handles code fences, missing fields, commentary |
| Rate limits on OpenRouter | Retry with backoff; use multiple keys if available |
| 3 consecutive move failures | Abort with full log rather than desync cascade |

---

## Success Metrics

- **Primary:** Full game played autonomously in Docker → pass/fail
- **Secondary:**
  - Vision FEN accuracy: >95% of moves have correct FEN
  - Move execution success: >90% of clicks verified on first try
  - Average move time (our side): <20s
  - Zero unrecoverable desyncs

---

## Out of Scope

- Improving engine strength (depth 3 is fine for learning)
- Supporting multiple chess sites (Lichess only for v1)
- Real-time games with clock pressure (unrated/casual only)
- GUI or web interface (CLI logging only)
- Full pre-game automation (cookie injection + manual game start is Phase 1)
