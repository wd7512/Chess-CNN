import time

from chess_agent.dom_reader import DOMReader
from chess_agent.page_manager import PageManager


class TestPageManager:
    def test_detect_state_game_with_board(self, page):
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.detect_state() == 'game'

    def test_detect_state_game_over(self, page):
        page.evaluate("window.showGameOver(true)")
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.detect_state() == 'game_over'

    def test_detect_state_lobby_no_board(self, page):
        page.evaluate("document.querySelector('cg-board').style.display = 'none'")
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.detect_state() == 'lobby'

    def test_wait_for_turn_returns_true_when_our_turn(self, page):
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.wait_for_turn(timeout=5) is True

    def test_wait_for_turn_timeout(self, page):
        page.evaluate("window.setTurn('black')")
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.wait_for_turn(timeout=1) is False

    def test_is_board_stable_true(self, page):
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.is_board_stable() is True

    def test_is_board_stable_with_anim(self, page):
        page.evaluate(
            "document.querySelector('cg-board').classList.add('anim')"
        )
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.is_board_stable() is False

    def test_wait_for_board_stability(self, page):
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.wait_for_board_stability(timeout_ms=500) is True

    def test_heartbeat_check_returns_true(self, page):
        pm = PageManager(page, DOMReader(page), 'white')
        assert pm.heartbeat_check() is True

    def test_heartbeat_check_board_gone(self, page):
        page.evaluate("document.querySelector('cg-board').remove()")
        pm = PageManager(page, DOMReader(page), 'white')
        pm._last_heartbeat = 0
        assert pm.heartbeat_check() is False
