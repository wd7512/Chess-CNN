# Phase 3 — E2E Test

Play a full game of chess on Lichess anonymously. No cookies, no account. The agent creates a "Play with a friend" game, waits for an opponent (human), then plays autonomously until game end.

## How to Run

### Automated (recommended)

```bash
python tools/e2e_runner.py
```

This builds the Docker image, starts a container with `GAME_MODE=e2e`, and streams logs. The agent will print the game URL in the logs — share it with a friend to start the game.

### Manual (debugging)

```bash
export GAME_MODE=e2e
python run.py --e2e
```

Or without setting the env var:

```bash
python run.py --e2e
```

The `GAME_MODE=e2e` env var is auto-detected by the agent, so either works.

### Via Docker directly

```bash
docker build -t chess-agent .
docker run --rm \
  --memory=2g \
  -e GAME_MODE=e2e \
  -v "$(pwd)/output:/app/output" \
  chess-agent \
  python run.py --e2e
```

## Prerequisites

- **Docker running** — for the automated runner
- **No cookies needed** — the agent plays anonymously
- **A human opponent** — share the game URL with someone who can join and play

## What Happens

1. Runner builds Docker image (or uses existing)
2. Container starts with `GAME_MODE=e2e`
3. Agent launches Playwright Chromium
4. Agent navigates to `https://lichess.org/`
5. Agent clicks **"Play with a friend"**
6. A game URL is created — printed in logs
7. Agent waits up to **120 seconds** for an opponent to join
8. Once opponent joins, agent detects its color (white/black) from DOM
9. Agent enters the main loop: screenshot → CNN → engine → click → verify
10. Game continues until checkmate, stalemate, draw, resignation, or timeout
11. On game end: result is logged, PGN saved to `output/game.pgn`

## Success Criteria

- Agent creates a game via "Play with a friend"
- Opponent joins and game starts
- Agent plays autonomously (no human intervention)
- Game completes (win/loss/draw, no crashes)
- Result logged in JSON format
- PGN file generated at `output/game.pgn`
- Container exits cleanly

## How to Observe

### Watch logs

The runner streams all container logs to stdout. Each step is logged as JSON:

```json
{"ts": "2026-06-25T12:00:00", "step": 0, "event": "start"}
{"ts": "2026-06-25T12:00:05", "step": 0, "event": "e2e_game_created", "url": "https://lichess.org/abcdefgh"}
{"ts": "2026-06-25T12:01:30", "step": 0, "event": "e2e_game_started", "color": "white"}
{"ts": "2026-06-25T12:01:35", "step": 1, "event": "board", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"}
{"ts": "2026-06-25T12:01:36", "step": 1, "event": "engine", "move": "e2e4"}
{"ts": "2026-06-25T12:01:38", "step": 1, "event": "move_ok", "move": "e2e4", "fen": "...", "ts": "..."}
```

### Watch in browser

Copy the game URL from the logs and open it in your browser. You'll see the game in real-time as the agent plays.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--no-build` | off | Skip Docker build step |
| `--timeout N` | 3600 | Max runtime in seconds |

Example:

```bash
python tools/e2e_runner.py --no-build --timeout 1800
```

## Notes

- The agent plays as **anonymous** — no Lichess account needed
- The opponent must be a **human** (not another bot)
- Game is **casual** (unrated)
- PGN is saved to `output/game.pgn` (auto-created if missing)
- Container auto-cleans up with `--rm` flag
- Timeout applies per game (30 min) and per turn (60 s)
