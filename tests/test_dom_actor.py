from chess_agent.dom_actor import DOMActor
from chess_agent.dom_reader import DOMReader


class TestDOMActor:
    def test_click_square(self, page):
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.click_square('e2') is True

    def test_click_square_selects_it(self, page):
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        actor.click_square('e2')
        sel = page.evaluate(
            "document.querySelector('square.selected')?.getAttribute('data-coord')"
        )
        assert sel == 'e2'

    def test_click_move_source_and_dest(self, page):
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        actor.click_move('e2e4')
        sel = page.evaluate(
            "document.querySelector('square.selected')?.getAttribute('data-coord')"
        )
        assert sel is None

    def test_verify_move_made(self, page):
        page.evaluate("window.addLastMove(['e2', 'e4'])")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.verify_move_made('e2e4', None) is True

    def test_verify_move_made_wrong_move(self, page):
        page.evaluate("window.addLastMove(['d2', 'd4'])")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.verify_move_made('e2e4', None) is False

    def test_verify_no_move_made(self, page):
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.verify_move_made('e2e4', None) is False
