import time

from chess_agent.click_mapper import uci_to_pixels
from chess_agent.config import AFTER_CLICK_WAIT, VERIFY_SELECTED_TIMEOUT, VERIFY_MOVE_TIMEOUT


class DOMActor:
    def __init__(self, page, dom_reader):
        self.page = page
        self.dom_reader = dom_reader

    def click_square(self, uci_square):
        rect = self.dom_reader.get_board_rect()
        if not rect:
            return False
        orientation = self.dom_reader.get_orientation()
        uci = uci_square + uci_square
        sx, sy, _, _ = uci_to_pixels(uci, rect, is_white=(orientation == 'white'))
        self.page.mouse.click(sx, sy)
        time.sleep(AFTER_CLICK_WAIT)
        return True

    def click_move(self, uci):
        rect = self.dom_reader.get_board_rect()
        if not rect:
            return False
        orientation = self.dom_reader.get_orientation()
        is_white = orientation == 'white'
        sx, sy, ex, ey = uci_to_pixels(uci, rect, is_white=is_white)

        self.page.mouse.click(sx, sy)
        if not self._wait_for_selected(VERIFY_SELECTED_TIMEOUT):
            return False

        time.sleep(AFTER_CLICK_WAIT)
        self.page.mouse.click(ex, ey)
        if self._wait_for_selected_gone(VERIFY_MOVE_TIMEOUT):
            return True

        return False

    def verify_move_made(self, uci, previous_fen):
        last_moves = self.dom_reader.get_last_move_squares()
        expected_source = uci[:2]
        expected_dest = uci[2:4]
        return expected_source in last_moves and expected_dest in last_moves

    def _wait_for_selected(self, timeout):
        start = time.time()
        while time.time() - start < timeout:
            if self.dom_reader.get_selected_square() is not None:
                return True
            time.sleep(0.1)
        return False

    def _wait_for_selected_gone(self, timeout):
        start = time.time()
        while time.time() - start < timeout:
            if self.dom_reader.get_selected_square() is None:
                return True
            time.sleep(0.1)
        return False
