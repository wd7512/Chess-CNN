#!/usr/bin/env python3
"""Phase 0.1: Lichess DOM Selector Audit (final).

Deep inspect a real game page, analysis board with clicks, and FEN load.
"""

import json, os
from playwright.sync_api import sync_playwright

REPORT = os.path.join(os.path.dirname(__file__), "..", "docs", "SELECTOR_AUDIT.md")

def el_info(page, selector):
    try:
        el = page.query_selector(selector)
        if not el:
            return None
        return page.evaluate(f"""() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {{
                tag: el.tagName, id: el.id,
                cls: el.className.substring(0, 200),
                visible: el.checkVisibility(),
                rect: {{x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1)}},
                text: (el.innerText||'').substring(0, 80),
            }};
        }}""")
    except:
        return None


def scan_selectors(page):
    CANDIDATES = {
        "Board element":       ["cg-board", ".main-board", ".cg-board-wrap"],
        "Board wrap":          [".cg-wrap"],
        "Orientation white":   [".orientation-white"],
        "Orientation black":   [".orientation-black"],
        "Turn indicator":      [".rclock .turn", ".rclock-turn", ".turn-indicator"],
        "Player clocks":       [".rclock", ".rclock-top", ".rclock-bottom"],
        "Running clock":       [".rclock.running", ".rclock-top.running", ".rclock-bottom.running"],
        "Selected square":     ["square.selected", ".selected"],
        "Last move square":    ["square.last-move"],
        "Game over dialog":    [".game-over", ".game-over-box", ".result-wrap"],
        "Move list":           [".moves", ".move-list", ".tabs-panel", ".kifu"],
        "Promotion dialog":    [".promotion", ".promotion-choice"],
        "Player info":         [".player", ".ruser", ".round__player"],
        "Game result":         [".result", ".game__result"],
    }
    results = {}
    for cat, sels in CANDIDATES.items():
        for s in sels:
            info = el_info(page, s)
            if info and info["visible"]:
                results[cat] = {"sel": s, "info": info}
                break
    return results


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        all_results = {}

        # 1. Real game page (from the mini-game link on TV)
        print("=== 1. GAME PAGE ===")
        page.goto("https://lichess.org/4OE0zX8l/black", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(4000)
        print(f"URL: {page.url}  Title: {page.title()}")
        results = scan_selectors(page)
        all_results["Game Page"] = results

        # Deep inspect game page elements
        print("\n--- Game page deep dive ---")
        deep = page.evaluate("""() => {
            const data = {};
            // Round app
            const round = document.querySelector('main.round, .round, div.round');
            if (round) {
                data.roundTag = round.tagName;
                data.roundCls = round.className.substring(0, 150);
                data.roundKids = Array.from(round.children).map(c =>
                    c.tagName + '.' + (c.className||'').substring(0,60)
                );
            }
            // Board structure
            const board = document.querySelector('cg-board');
            if (board) {
                let el = board.parentElement;
                data.boardAncestry = [];
                for (let i=0; i<6 && el; i++) {
                    data.boardAncestry.push({tag: el.tagName, cls: el.className.substring(0,100)});
                    el = el.parentElement;
                }
                const pieces = board.querySelectorAll('piece');
                data.pieceCount = pieces.length;
                const sqs = board.querySelectorAll('square');
                data.squareCount = sqs.length;
                data.labelsBoard = board.closest('[class*="board"]')?.className || 'none';
            }
            // Clock with "running"
            const running = document.querySelector('.rclock.running, .rclock-top.running, .rclock-bottom.running');
            data.runningClock = running ? running.className.substring(0,100) : null;
            // Player turn info from the game data
            const gameEl = document.querySelector('[data-game-id]');
            if (gameEl) data.gameId = gameEl.getAttribute('data-game-id');
            // Check for round__app id
            data.roundApp = document.getElementById('round-app') ? 'yes' : 'no';
            return JSON.stringify(data, null, 2);
        }""")
        print(deep[:2000])

        # 2. Analysis board - click test
        print("\n=== 2. ANALYSIS BOARD (CLICK TEST) ===")
        page.goto("https://lichess.org/analysis", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        results = scan_selectors(page)
        all_results["Analysis Board"] = results

        # Click e2 and check selected
        board_rect = page.evaluate("""() => {
            const b = document.querySelector('cg-board');
            if (!b) return null;
            const r = b.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height};
        }""")
        if board_rect:
            sq = board_rect["w"] / 8
            print(f"  Board: {board_rect}, sq={sq}")
            # Click e2
            px, py = board_rect["x"] + 4.5*sq, board_rect["y"] + 6.5*sq
            print(f"  Click e2 @ ({px:.0f},{py:.0f})")
            page.mouse.click(px, py)
            page.wait_for_timeout(500)
            sel = page.evaluate("""() => {
                const s = document.querySelector('square.selected, .selected');
                if (!s) return 'no selected';
                return {cls: s.className, style: s.getAttribute('style'), html: s.outerHTML.substring(0,200)};
            }""")
            print(f"  After click: {json.dumps(sel, indent=2)[:300]}")

            # Get legal move highlights
            legal_sqs = page.evaluate("""() => {
                const sqs = document.querySelectorAll('square');
                return Array.from(sqs).filter(s => /(check|move-dest|en-passant)/.test(s.className)).slice(0,5).map(s => ({
                    cls: s.className, style: s.getAttribute('style')
                }));
            }""")
            print(f"  Legal move highlights: {json.dumps(legal_sqs, indent=2)[:400]}")

            # Click e4 to move
            px2, py2 = board_rect["x"] + 4.5*sq, board_rect["y"] + 4.5*sq
            page.mouse.click(px2, py2)
            page.wait_for_timeout(500)
            sel2 = page.evaluate("() => document.querySelector('square.selected, .selected') !== null")
            print(f"  After dest click, selected present: {sel2}")

        # 3. FEN load test
        print("\n=== 3. FEN LOAD TEST ===")
        test_fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R_w_KQkq_-_4_4"
        page.goto(f"https://lichess.org/analysis/{test_fen.replace(' ', '_')}",
                  wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        results = scan_selectors(page)
        all_results["Analysis (FEN loaded)"] = results
        fen_info = page.evaluate("""() => {
            const b = document.querySelector('cg-board');
            if (!b) return 'no board';
            return {pieces: b.querySelectorAll('piece').length};
        }""")
        print(f"  FEN loaded: {fen_info}")

        # Generate report
        md = f"""# Lichess DOM Selector Audit

**Date:** 2026-06-21 | **Method:** Playwright headless Chromium (realistic UA)

## Confirmed Selectors

"""
        for label, r in all_results.items():
            md += f"### {label}\n\n| Category | Selector | Tag | Classes | Position |\n|----------|----------|-----|---------|----------|\n"
            for cat, d in r.items():
                info = d["info"]
                rect = info["rect"]
                md += f"| {cat} | `{d['sel']}` | `<{info['tag']}>` | `{info['cls'][:60]}` | ({rect['x']},{rect['y']}) {rect['w']}×{rect['h']} |\n"
            md += "\n"

        md += """## Key Findings

### Board
- **Primary:** `cg-board` — works on all pages
- **Parent:** `.cg-wrap` — contains orientation class (`orientation-white` or `orientation-black`)
- On game/analysis pages, `.cg-wrap` also has class `manipulable` (distinguishes main board from mini-boards)
- Board bounding rect via `.getBoundingClientRect()` on cg-board

### Orientation
- **Primary:** Check `.cg-wrap` for `orientation-white` or `orientation-black` class
- More specific: `.cg-wrap.manipulable.orientation-white` or `.cg-wrap.manipulable.orientation-black`

### Turn Detection
- **No dedicated `.rclock-turn` selector exists.**
- Instead: look at the clock elements: `.rclock-top` and `.rclock-bottom`
- Each clock has `.rclock-white` or `.rclock-black` class
- Use `.rclock.running` to find which clock is actively counting down
- The running clock's color class indicates whose turn it is
- Example: `.rclock.running.rclock-white` = White's turn

### Selected Square
- `square.selected` — appears after clicking a piece
- Also: `square.last-move` highlights the last move's source and destination (has class `last-move`)

### Legal Move Highlights
- After selecting a piece, destination squares get classes like `move-dest`, `en-passant`, `check`

### Board Structure
- `<cg-board>` inside `<cg-container>` inside `<span|div class="cg-wrap ...">`
- Pieces are `<piece class="white queen" style="transform: translate(x, y)">`
- Squares are `<square class="last-move" style="transform: translate(x, y)">`

### Observations
- The `.rclock-turn` selector from the design doc does NOT exist on Lichess
- Turn must be detected from the `.running` class on clock elements
- The analysis board is the best environment for testing clicks and `.selected`
"""
        with open(REPORT, "w") as f:
            f.write(md)
        print(f"\nReport -> {REPORT}")

        ss = os.path.join(os.path.dirname(__file__), "..", "docs", "audit_screenshot.png")
        page.screenshot(path=ss, full_page=False)
        print(f"Screenshot -> {ss}")

        browser.close()

if __name__ == "__main__":
    main()
