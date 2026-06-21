#!/usr/bin/env python3
"""Check how Lichess indicates the current player's turn on live game pages."""

import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    )
    page = context.new_page()

    # TV page has live game with clocks
    page.goto("https://lichess.org/tv", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(5000)

    print(f"TV URL: {page.url}")

    # Check all clock classes
    clocks = page.evaluate("""() => {
        const els = document.querySelectorAll('.rclock');
        return Array.from(els).map(el => ({
            cls: el.className,
            html: el.outerHTML.substring(0, 500),
            hasBar: !!el.querySelector('.bar'),
            barStyle: el.querySelector('.bar')?.getAttribute('style') || null,
        }));
    }""")
    print("\nClocks:")
    print(json.dumps(clocks, indent=2))

    # Check for any element with 'turn' in class or id
    turn_els = page.evaluate("""() => {
        const all = document.querySelectorAll('*');
        const matches = [];
        for (const el of all) {
            const cls = el.className || '';
            const id = el.id || '';
            if (typeof cls === 'string' && (cls.includes('turn') || cls.includes('Turn'))) {
                matches.push({tag: el.tagName, cls: cls.substring(0, 100), id: id});
            }
        }
        return matches.slice(0, 20);
    }""")
    print(f"\nElements with 'turn': {json.dumps(turn_els, indent=2)[:2000]}")

    # Check data-turn or data-state attributes on round/game elements
    game_state = page.evaluate("""() => {
        const results = {};
        // Check main round element
        const main = document.querySelector('main.round, main.tv-single');
        if (main) {
            results.mainAttrs = {};
            for (const attr of main.attributes) {
                results.mainAttrs[attr.name] = attr.value;
            }
        }
        // Check tv-single
        const tv = document.querySelector('.tv-single, .round');
        if (tv) {
            results.tvAttrs = {};
            for (const attr of tv.attributes) {
                results.tvAttrs[attr.name] = attr.value;
            }
        }
        // Check for game data on any element
        const withData = document.querySelector('[data-game-id]');
        if (withData) {
            results.gameData = {};
            for (const attr of withData.attributes) {
                if (attr.name.startsWith('data-'))
                    results.gameData[attr.name] = attr.value.substring(0, 100);
            }
        }
        // Look at the setup div
        const setup = document.querySelector('.setup');
        if (setup) results.setupText = setup.innerText?.substring(0, 100);
        return results;
    }""")
    print(f"\nGame state attrs: {json.dumps(game_state, indent=2)[:2000]}")

    # Check what class indicates the active/running clock
    bar_info = page.evaluate("""() => {
        const clocks = document.querySelectorAll('.rclock');
        return Array.from(clocks).map(c => {
            const bar = c.querySelector('.bar');
            const time = c.querySelector('.time');
            return {
                cls: c.className.substring(0, 80),
                barCls: bar?.className || null,
                barTransform: bar?.getAttribute('style') || null,
                timeHTML: time?.outerHTML?.substring(0, 200) || null,
            };
        });
    }""")
    print(f"\nClock bar info: {json.dumps(bar_info, indent=2)}")

    browser.close()
