import logging
import time

from chess_agent.config import (
    BOARD_STABILITY_POLL_MS,
    HEARTBEAT_INTERVAL,
    MOVE_TURN_TIMEOUT,
)

logger = logging.getLogger(__name__)


class PageManager:
    def __init__(self, page, dom_reader, our_color):
        self.page = page
        self.dom_reader = dom_reader
        self.our_color = our_color
        self._last_heartbeat = time.time()
        self._last_turn_check = None

    def detect_state(self):
        url = self.page.url.lower()
        if 'login' in url:
            return 'login'
        if not self.dom_reader.is_board_visible():
            return 'lobby'
        if self.dom_reader.has_game_over_dialog():
            return 'game_over'
        if self.dom_reader.is_board_visible():
            return 'game'
        return 'lobby'

    def navigate_to_game(self, game_url):
        self.page.goto(game_url, wait_until='domcontentloaded')
        self.page.wait_for_selector('cg-board', timeout=15000)
        self.wait_for_board_stability()
        self._last_heartbeat = time.time()

    def wait_for_turn(self, timeout=MOVE_TURN_TIMEOUT):
        start = time.time()
        while time.time() - start < timeout:
            self._heartbeat_check()
            if self.dom_reader.is_our_turn(self.our_color):
                self.wait_for_board_stability()
                return True
            time.sleep(0.5)
        return False

    def is_board_stable(self):
        has_anim = self.page.evaluate(
            "document.querySelector('cg-board')?.classList?.value?.includes('anim') ?? false"
        )
        return not has_anim

    def wait_for_board_stability(self, timeout_ms=2000):
        start = time.time()
        while (time.time() - start) * 1000 < timeout_ms:
            if self.is_board_stable():
                return True
            time.sleep(BOARD_STABILITY_POLL_MS / 1000)
        return False

    def heartbeat_check(self):
        if time.time() - self._last_heartbeat < HEARTBEAT_INTERVAL:
            return True
        self._last_heartbeat = time.time()
        return self._heartbeat_check()

    def _heartbeat_check(self):
        try:
            ok = self.page.evaluate("document.readyState === 'complete'")
            if not ok:
                logger.warning("Heartbeat: page not ready")
                return False
            visible = self.dom_reader.is_board_visible()
            if not visible:
                logger.warning("Heartbeat: board not visible")
                return False
            return True
        except Exception as e:
            logger.error("Heartbeat check failed: %s", e)
            return False
