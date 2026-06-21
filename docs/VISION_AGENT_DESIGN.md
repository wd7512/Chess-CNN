# Vision-Driven Chess Agent — Design Document

**Date:** 2026-06-21 | **Author:** OWL | **Repo:** `wd7512/Chess-CNN`

## Goal

Play a full game of chess autonomously on Lichess inside Docker. No macOS deps, no human intervention during play, no API calls. `docker build && docker run` is all that's needed.

**Final gate criteria:**
- [ ] Runs in Docker (no macOS-only deps)
- [ ] Plays a full game (start → checkmate/resign/draw) against a live opponent
- [ ] Zero human intervention during play
- [ ] Game result logged (win/loss/draw, move count, errors)
- [ ] PGN file generated

## Strategy

Replace everything screen-dependent (mss, pyautogui, cv2 template match) with Playwright + DOM. Keep the CNN and engine — they work.

| Keep | Replace | With |
|------|---------|------|
| CNN (`Piece_Classifier.h5`) | `mss` screen capture | Playwright `page.screenshot()` |
| Engine (`min_maxN_pruned`) | `cv2.matchTemplate` board detection | DOM board element rect |
| FEN assembly | `pyautogui.click` | Playwright `page.mouse.click()` |
| Opening book | Template-based orientation | DOM `.orientation-*` class |
| | Screenshot re-classify verification | DOM `.selected` + board state diff |
| | `new_opp.png` opponent detection | DOM turn indicator selector |

## Architecture

```
chess_agent.py (orchestrator)
  ├─ page_manager.py    — state machine, turn wait, board stability, heartbeat, selector health check
  ├─ dom_reader.py      — read-only DOM: board rect, orientation, turn, board state, overlays
  ├─ dom_actor.py       — clicks + verification (partial diff, not full board)
  ├─ board_extractor.py — pure OpenCV: crop → 200×200 → 64 tiles
  ├─ piece_classifier.py— CNN forward pass
  ├─ fen_assembler.py   — 64 labels → FEN
  ├─ engine_client.py   — min_maxN_pruned depth 3, opening book at root only
  ├─ click_mapper.py    — algebraic → pixel (both orientations), promotion → queen
  ├─ game_state.py      — cross-move consistency via partial diff
  └─ config.py          — all selectors, paths, timeouts
```

**Per-move loop:** wait turn → screenshot → crop board → CNN classify → assemble FEN → engine picks move → compute click coords → click source → click dest → verify via DOM partial diff → retry up to 3x on failure → abort on 3 consecutive failures.

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN LOOP (chess_agent.py)                                 │
│                                                             │
│  0. PAGE STATE DETECTOR                                     │
│     - URL + DOM: login | lobby | game | game_over           │
│     - Login → ABORT: "Cookies expired"                     │
│     - Lobby → ABORT: "No game in progress"                 │
│     - Game over → log result, exit                          │
│                                                             │
│  while not game_over and step < MAX_STEPS:                  │
│                                                             │
│    1. WAIT for our turn                                     │
│       - DOM: wait for turn indicator + board stability      │
│       - Timeout: 60s → diagnostic screenshot → abort        │
│                                                             │
│    2. SCREENSHOT                                            │
│       - Playwright page.screenshot() → PNG                  │
│                                                             │
│    3. EXTRACT BOARD                                         │
│       - DOM: board element bounding rect                    │
│       - OpenCV: crop + resize to 200×200                    │
│                                                             │
│    4. CLASSIFY PIECES (CNN)                                 │
│       - 64 tiles × 25×25 grayscale → forward pass           │
│       - 64 labels → FEN string                              │
│                                                             │
│    5. OVERRIDE ORIENTATION + ACTIVE COLOR FROM DOM          │
│       - .orientation-* class, turn indicator                │
│                                                             │
│    6. ENGINE: pick_move(FEN) → move_uci                     │
│       - min_maxN_pruned depth 3, book at root only          │
│       - Illegal on reported FEN? → retry from step 3        │
│                                                             │
│    7. COMPUTE CLICK COORDINATES                             │
│       - UCI → source/dest squares → pixel via board rect    │
│       - Fixed math (corrects black perspective bug)         │
│                                                             │
│    8. DOM VERIFY: click + confirm                           │
│       - click source → verify .selected (2s)                │
│       - click dest → verify .selected gone (3s)             │
│       - Partial diff: only squares in the move              │
│       - Unchanged? → retry from step 7 (max 3x)             │
│       - 3 consecutive failures → abort                      │
│                                                             │
│    9. LOG step, increment counter                           │
│                                                             │
│  End: log game result, save PGN                             │
└─────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- Partial diff (only squares in the move) for verification — robust to opponent-in-flight moves
- Board stability: poll bounding rect 500ms + check no CSS animation classes before screenshot
- Primary + fallback selectors for critical paths (turn indicator, board)
- Signal handler (SIGTERM/SIGINT): save partial PGN, close browser cleanly
- Heartbeat: if no DOM change >30s during opponent turn, check connection
- `GAME_TIMEOUT = 1800s` (30 min) overall; `MOVE_TURN_TIMEOUT = 60s` per move

## Game Start

Human creates a casual (unrated) game on Lichess, provides URL via `GAME_URL` env var. Agent navigates, runs DOM health check (all selectors resolve), confirms game state, aborts if clock <10 min. Human intervention ends when the main loop starts.

## Authentication

EditThisCookie JSON export → `lichess_cookies.json` → Playwright `context.add_cookies()`. Mounted as Docker volume. Format: JSON array of `{name, value, domain: ".lichess.org", path: "/"}`.

## Docker

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev
```

```bash
docker run --memory=2g \
  -v "$(pwd)/lichess_cookies.json:/app/lichess_cookies.json" \
  -v "$(pwd)/output:/app/screenshots" \
  -e GAME_URL="https://lichess.org/AbCdEfGh" \
  chess-agent
```

Use `tensorflow-cpu` (not GPU) in requirements.txt. Consider ONNX Runtime for lighter inference.

## Output

- **Logs:** JSON lines to stdout + `/app/logs/game.log` — `{ts, level, step, event, fen, move, retries, ...}`
- **Screenshots:** `/app/screenshots/step_N.png`
- **PGN:** `/app/output/game.pgn` — standard headers, moves from engine + DOM move history panel

## Test Plan

### Phase 0 — Pre-implementation (before writing any code)
0.1 Verify ALL selectors against live Lichess (board, turn, selected, game-over, orientation, overlays). Document date. Implement `verify_selectors()` startup health check.
0.2 Test CNN on Lichess screenshots: 3 positions (opening/midgame/endgame). Report **FEN-level** accuracy. Gate: ≥90%. Test default board theme. Compare pixel histograms vs training data.
0.3 Docker build: Chromium starts, OpenCV imports, CNN loads.
0.4 Cookie injection: export → load → verify logged in.

### Phase 1 — Unit tests (no Docker, no browser)
One file per component. Each includes ≥1 negative/failure path test.
- `test_board_extractor.py` `test_piece_classifier.py` `test_fen_assembler.py`
- `test_click_mapper.py` (both orientations) `test_engine_client.py` (root-only book)
- `test_dom_reader.py` `test_dom_actor.py` `test_page_manager.py` `test_game_state.py`
- `test_e2e_smoke.py` (mock everything, 5-move loop)

### Phase 1.5 — Contract tests
- `test_contract.py`: chain adjacent components (screenshot→extractor→classifier→assembler→engine→mapper). Catches shape/channel/normalization mismatches.

### Phase 2 — Integration (Docker, mock DOM)
Local HTML mimicking Lichess DOM. Full loop, 10 moves, zero errors.

### Phase 3 — E2E (Docker, real Lichess, real opponent)
Casual game, live opponent. Gate: game completes, no human intervention, PGN generated.

## Risks (behavior-changing only)

| Risk | Mitigation |
|------|-----------|
| CNN doesn't generalize to Lichess | Phase 0.2 gate; fallback: fine-tune, adjust pipeline, or use Lichess API as ground truth |
| Turn indicator selector wrong | Primary + fallback; startup health check aborts immediately with clear message |
| Dockerfile missing OpenCV deps | All 5 libs listed above |
| No game start procedure | Documented above — human provides URL |
| Promotion / en passant edge cases | Always promote to queen; under-promotion not supported (documented) |
| Lichess anti-bot | Test account, casual only, human-like delays |
| Container OOM | `--memory=2g` |
| Mid-game container kill | Signal handler saves partial PGN |
| WebSocket drop | Heartbeat check every 30s |
| UI overlays block board | `dismiss_overlays()` before each screenshot |
| TensorFlow image bloat | `tensorflow-cpu` or ONNX Runtime |

## Out of Scope

Engine improvement, multi-site support, timed games, GUI, full pre-game automation, CNN retraining, under-promotion, en passant beyond CNN inference.
