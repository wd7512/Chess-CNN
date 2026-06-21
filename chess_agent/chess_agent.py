import json
import logging
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from chess_agent.board_extractor import crop_board, split_tiles
from chess_agent.config import (
    COOKIE_PATH,
    GAME_TIMEOUT,
    LOG_DIR,
    MAX_RETRIES,
    MOVE_TURN_TIMEOUT,
    OUTPUT_DIR,
    PIECE_CLASSIFIER_PATH,
)
from chess_agent.dom_actor import DOMActor
from chess_agent.dom_reader import DOMReader
from chess_agent.engine_client import pick_move
from chess_agent.fen_assembler import labels_to_fen
from chess_agent.game_state import GameState
from chess_agent.page_manager import PageManager
from chess_agent.piece_classifier import PieceClassifier

logger = logging.getLogger(__name__)


def _setup_logging():
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "game.log")
    fh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)


def _json_log(step, **kwargs):
    record = {"ts": datetime.now(timezone.utc).isoformat(), "step": step, **kwargs}
    line = json.dumps(record)
    logger.info(line)
    print(line, flush=True)


class ChessAgent:
    def __init__(self, game_url, our_color, cookie_path=None):
        self.game_url = game_url
        self.our_color = our_color
        self.cookie_path = cookie_path or COOKIE_PATH
        self.game_state = GameState()
        self._running = True
        self._browser = None
        self._context = None
        self._page = None

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        _json_log(-1, event="shutdown", signal=signum)
        self._running = False

    def run(self):
        _setup_logging()
        _json_log(0, event="start", url=self.game_url, color=self.our_color)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            self._browser = pw.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                no_viewport=True,
                viewport={"width": 1280, "height": 900},
            )
            self._inject_cookies()
            self._page = self._context.new_page()

            dom_reader = DOMReader(self._page)
            dom_actor = DOMActor(self._page, dom_reader)
            page_manager = PageManager(self._page, dom_reader, self.our_color)
            classifier = PieceClassifier(PIECE_CLASSIFIER_PATH)

            result = self._main_loop(page_manager, dom_reader, dom_actor, classifier)
            self._save_pgn()
            _json_log(-2, event="end", result=result)
            return result

    def _inject_cookies(self):
        cookie_file = self.cookie_path
        if not cookie_file.exists():
            _json_log(0, event="no_cookies")
            return
        try:
            cookies = json.loads(cookie_file.read_text())
            self._context.add_cookies(cookies)
            _json_log(0, event="cookies_loaded", count=len(cookies))
        except Exception as e:
            _json_log(0, event="cookie_error", error=str(e))

    def _main_loop(self, pm, reader, actor, classifier):
        game_start = time.time()

        pm.navigate_to_game(self.game_url)

        step = 0
        consecutive_failures = 0
        board = None
        last_fen = None

        while self._running:
            elapsed = time.time() - game_start
            if elapsed > GAME_TIMEOUT:
                _json_log(step, event="timeout", elapsed=elapsed)
                return "timeout"

            state = pm.detect_state()
            _json_log(step, event="state", state=state)

            if state == 'login':
                _json_log(step, event="abort", reason="login_required")
                return "login_required"
            if state == 'lobby':
                _json_log(step, event="abort", reason="no_game")
                return "no_game"
            if state == 'game_over':
                result = reader.get_game_result()
                _json_log(step, event="game_over", result=result)
                return result or "unknown"

            if not pm.wait_for_turn(timeout=MOVE_TURN_TIMEOUT):
                reader.dismiss_overlays()
                if reader.has_game_over_dialog():
                    result = reader.get_game_result()
                    _json_log(step, event="game_over", result=result)
                    return result or "unknown"
                _json_log(step, event="turn_timeout")
                return "turn_timeout"

            reader.dismiss_overlays()
            pm.wait_for_board_stability()

            screenshot_bytes = self._page.screenshot(type='png')
            img = cv2.imdecode(
                np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_GRAYSCALE
            )

            rect = reader.get_board_rect()
            if not rect:
                _json_log(step, event="no_board_rect")
                continue

            board_img = crop_board(img, rect)
            board_img = cv2.resize(board_img, (200, 200))

            tiles = split_tiles(board_img)
            labels = classifier.classify(tiles)

            orientation = reader.get_orientation()
            if orientation == 'black':
                rows = [labels[i*8:(i+1)*8] for i in range(8)]
                rows.reverse()
                rows = [row[::-1] for row in rows]
                labels = [l for row in rows for l in row]

            fen = labels_to_fen(labels)
            is_white = self.our_color == 'white'
            _json_log(step, event="board", fen=fen, orientation=orientation)

            board = None
            move_uci = None

            try:
                move_uci = pick_move(fen, is_white)
                _json_log(step, event="engine", move=move_uci)
            except Exception as e:
                _json_log(step, event="engine_error", error=str(e))
                consecutive_failures += 1
                if consecutive_failures >= MAX_RETRIES:
                    _json_log(step, event="abort", reason="engine_failures")
                    return "engine_failures"
                continue

            move_ok = False
            for attempt in range(MAX_RETRIES + 1):
                if attempt > 0:
                    _json_log(step, event="retry", attempt=attempt)

                pm.wait_for_board_stability()

                if not actor.click_move(move_uci):
                    _json_log(step, event="click_fail", attempt=attempt)
                    continue

                new_screenshot = self._page.screenshot(type='png')
                new_img = cv2.imdecode(
                    np.frombuffer(new_screenshot, np.uint8), cv2.IMREAD_GRAYSCALE
                )
                new_board = crop_board(new_img, rect)
                new_board = cv2.resize(new_board, (200, 200))
                new_tiles = split_tiles(new_board)
                new_labels = classifier.classify(new_tiles)

                if orientation == 'black':
                    rows = [new_labels[i*8:(i+1)*8] for i in range(8)]
                    rows.reverse()
                    rows = [row[::-1] for row in rows]
                    new_labels = [l for row in rows for l in row]

                new_fen = labels_to_fen(new_labels)

                if self.game_state.verify_move(fen, new_fen, move_uci):
                    move_ok = True
                    self.game_state.update(new_fen)
                    _json_log(step, event="move_ok", move=move_uci, fen=new_fen)
                    break
                else:
                    _json_log(
                        step, event="board_unchanged", move=move_uci,
                        old_fen=fen, new_fen=new_fen,
                    )

            if move_ok:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= MAX_RETRIES:
                    _json_log(step, event="abort", reason="move_failures")
                    return "move_failures"

            step += 1

        return "shutdown"

    def _save_pgn(self):
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        pgn_path = output_dir / "game.pgn"
        try:
            pgn_path.write_text(
                f"[Event \"Casual Game\"]\n"
                f"[Site \"https://lichess.org\"]\n"
                f"[Date \"{datetime.now(timezone.utc).strftime('%Y.%m.%d')}\"]\n"
                f"[White \"{'Agent' if self.our_color == 'white' else 'Opponent'}\"]\n"
                f"[Black \"{'Agent' if self.our_color == 'black' else 'Opponent'}\"]\n"
                f"[Result \"*\"]\n"
            )
            _json_log(-1, event="pgn_saved", path=str(pgn_path))
        except Exception as e:
            _json_log(-1, event="pgn_error", error=str(e))

    def _shutdown(self):
        self._running = False
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
