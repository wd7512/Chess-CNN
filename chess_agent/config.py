"""Centralized selectors, paths, and timeouts for the chess agent.

All Lichess DOM selectors are defined here with primary + fallback values.
Verify selectors against live Lichess before modifying (see docs/SELECTOR_AUDIT.md).
"""

from pathlib import Path

# --- Paths ---
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "Models"
PIECE_CLASSIFIER_PATH = str(MODEL_DIR / "Piece_Classifier.h5")
OPENING_BOOK_PATH = str(REPO_ROOT / "baron30.bin")
COOKIE_PATH = REPO_ROOT / "lichess_cookies.json"

# --- Directories ---
SCREENSHOT_DIR = "/app/screenshots"
LOG_DIR = "/app/logs"
OUTPUT_DIR = "/app/output"

# --- Lichess DOM Selectors ---
# Verified against live Lichess on 2026-06-21 (see docs/SELECTOR_AUDIT.md)

SELECTOR_BOARD = "cg-board"
SELECTOR_BOARD_WRAP = ".cg-wrap.manipulable"
SELECTOR_CLOCK_RUNNING = ".rclock.running"
SELECTOR_CLOCK_WHITE = ".rclock-white"
SELECTOR_CLOCK_BLACK = ".rclock-black"
SELECTOR_CLOCK_TOP = ".rclock-top"
SELECTOR_CLOCK_BOTTOM = ".rclock-bottom"
SELECTOR_SELECTED = "square.selected"
SELECTOR_LAST_MOVE = "square.last-move"
SELECTOR_MOVE_DEST = "square.move-dest"
SELECTOR_GAME_OVER = ".game-over"
SELECTOR_RESULT = ".result"
SELECTOR_PROMOTION = ".promotion"
SELECTOR_DRAW_OFFER = ".draw-offer"
SELECTOR_PLAYER = ".player"
SELECTOR_MOVES = ".moves"
SELECTOR_ROUND = "main.round"

# --- Timeouts (seconds) ---
MOVE_TURN_TIMEOUT = 60
GAME_TIMEOUT = 1800
BOARD_STABILITY_POLL_MS = 500
HEARTBEAT_INTERVAL = 30
AFTER_CLICK_WAIT = 1.0
VERIFY_SELECTED_TIMEOUT = 2.0
VERIFY_MOVE_TIMEOUT = 3.0
MAX_RETRIES = 3

# --- E2E Mode ---
E2E_OPPONENT_TIMEOUT = 120  # Maximum seconds to wait for opponent to join
E2E_MODE_ENV_VAR = "GAME_MODE"
E2E_MODE_VALUE = "e2e"
E2E_LICHESS_HOMEPAGE = "https://lichess.org/"
