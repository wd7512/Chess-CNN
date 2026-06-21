import time


class DOMReader:
    def __init__(self, page):
        self.page = page

    def get_board_rect(self):
        js = """
            (() => {
                const el = document.querySelector('cg-board');
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height};
            })()
        """
        return self.page.evaluate(js)

    def get_orientation(self):
        for cls in self.page.evaluate(
            "document.querySelector('.cg-wrap')?.classList?.value ?? ''"
        ).split():
            if cls == 'orientation-white':
                return 'white'
            if cls == 'orientation-black':
                return 'black'
        return 'white'

    def is_our_turn(self, our_color):
        running = self.page.query_selector('.rclock.running')
        if not running:
            return False
        class_list = running.get_attribute('class') or ''
        running_color = 'white' if 'rclock-white' in class_list else 'black'
        return running_color == our_color

    def get_selected_square(self):
        el = self.page.query_selector('square.selected')
        if not el:
            return None
        return el.get_attribute('data-coord')

    def get_last_move_squares(self):
        els = self.page.query_selector_all('square.last-move')
        coords = []
        for el in els:
            coord = el.get_attribute('data-coord')
            if coord:
                coords.append(coord)
        return coords

    def has_game_over_dialog(self):
        return self.page.query_selector('.game-over') is not None

    def get_game_result(self):
        el = self.page.query_selector('.result')
        if not el:
            return None
        return el.text_content()

    def dismiss_overlays(self):
        dismiss_clicked = False
        for sel in ['.draw-offer button:has-text("Decline")',
                     '.draw-offer button:has-text("Cancel")',
                     '.promotion-choice',
                     '.offer-draw']:
            el = self.page.query_selector(sel)
            if el:
                try:
                    el.click()
                    dismiss_clicked = True
                    time.sleep(0.3)
                except Exception:
                    pass
        if not dismiss_clicked:
            overlays = self.page.query_selector_all('.game-over, .draw-offer')
            for ov in overlays:
                if ov.is_visible():
                    self.page.keyboard.press('Escape')
                    time.sleep(0.3)
                    break

    def is_board_visible(self):
        el = self.page.query_selector('cg-board')
        return el is not None and el.is_visible()
