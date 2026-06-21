from chess_agent.dom_reader import DOMReader


class TestDOMReader:
    def test_get_board_rect(self, page):
        reader = DOMReader(page)
        rect = reader.get_board_rect()
        assert rect is not None
        assert 'x' in rect
        assert 'y' in rect
        assert 'w' in rect
        assert 'h' in rect
        assert rect['w'] > 0
        assert rect['h'] > 0

    def test_get_orientation_default_white(self, page):
        reader = DOMReader(page)
        assert reader.get_orientation() == 'white'

    def test_get_orientation_black(self, page):
        page.evaluate("window.setOrientation('black')")
        reader = DOMReader(page)
        assert reader.get_orientation() == 'black'

    def test_is_our_turn_white(self, page):
        reader = DOMReader(page)
        assert reader.is_our_turn('white') is True
        assert reader.is_our_turn('black') is False

    def test_is_our_turn_black(self, page):
        page.evaluate("window.setTurn('black')")
        reader = DOMReader(page)
        assert reader.is_our_turn('black') is True
        assert reader.is_our_turn('white') is False

    def test_is_our_turn_no_running(self, page):
        page.evaluate(
            "document.querySelectorAll('.rclock').forEach(e => e.classList.remove('running'))"
        )
        reader = DOMReader(page)
        assert reader.is_our_turn('white') is False

    def test_get_selected_square_none_initially(self, page):
        reader = DOMReader(page)
        assert reader.get_selected_square() is None

    def test_get_selected_square_with_selection(self, page):
        page.evaluate(
            "document.querySelector('square[data-coord=\"e2\"]').classList.add('selected')"
        )
        reader = DOMReader(page)
        assert reader.get_selected_square() == 'e2'

    def test_get_last_move_squares_empty(self, page):
        reader = DOMReader(page)
        assert reader.get_last_move_squares() == []

    def test_get_last_move_squares_with_moves(self, page):
        page.evaluate("window.addLastMove(['e2', 'e4'])")
        reader = DOMReader(page)
        moves = reader.get_last_move_squares()
        assert 'e2' in moves
        assert 'e4' in moves

    def test_has_game_over_dialog_false(self, page):
        reader = DOMReader(page)
        assert reader.has_game_over_dialog() is False

    def test_has_game_over_dialog_true(self, page):
        page.evaluate("window.showGameOver(true)")
        reader = DOMReader(page)
        assert reader.has_game_over_dialog() is True

    def test_get_game_result_none(self, page):
        reader = DOMReader(page)
        assert reader.get_game_result() is None

    def test_get_game_result_with_result(self, page):
        page.evaluate("window.showGameOver(true)")
        reader = DOMReader(page)
        assert reader.get_game_result() == '1-0'

    def test_dismiss_overlays_draw_offer(self, page):
        page.evaluate("window.showDrawOffer(true)")
        reader = DOMReader(page)
        assert page.query_selector('.draw-offer') is not None
        reader.dismiss_overlays()
        page.wait_for_timeout(500)
        assert page.query_selector('.draw-offer') is not None

    def test_is_board_visible_true(self, page):
        reader = DOMReader(page)
        assert reader.is_board_visible() is True

    def test_is_board_visible_false(self, page):
        page.evaluate("document.querySelector('cg-board').style.display = 'none'")
        reader = DOMReader(page)
        assert reader.is_board_visible() is False
