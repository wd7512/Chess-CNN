#!/usr/bin/env python3
"""Phase 0.4: Cookie Auth Test.

Verifies that Lichess cookies can be loaded and injected via Playwright.
Checks for a logged-in session on lichess.org.
"""

import json
import os
import sys

COOKIE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lichess_cookies.json")


def main():
    print("=" * 60)
    print("Cookie Auth Test — Phase 0.4")
    print("=" * 60)

    # Check if cookie file exists
    if not os.path.exists(COOKIE_PATH):
        print(f"\n  ✗ Cookie file not found: {COOKIE_PATH}")
        print(f"\n  To test: export cookies from Lichess to {COOKIE_PATH}")
        print(f"  See docs/COOKIE_AUTH.md for instructions.")
        print(f"\n  Example file created at: lichess_cookies.example.json")
        return

    print(f"  Cookie file: {COOKIE_PATH}")

    # Load cookies
    try:
        with open(COOKIE_PATH) as f:
            cookies = json.load(f)
        if not isinstance(cookies, list):
            raise ValueError("Cookies must be a JSON array")
        print(f"  Loaded {len(cookies)} cookie(s)")
        for c in cookies[:3]:
            print(f"    - {c.get('name')}: {c.get('value', '')[:20]}... domain={c.get('domain')}")
    except Exception as e:
        print(f"  ✗ Error loading cookies: {e}")
        return

    # Test injection
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ✗ Playwright not installed. Run: uv pip install playwright")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )

        # Inject cookies
        context.add_cookies(cookies)
        print("  ✓ Cookies injected")

        page = context.new_page()
        page.goto("https://lichess.org/", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)

        title = page.title()
        print(f"  Page: {title}")

        # Check if logged in by looking for sign-in button or user menu
        logged_in = page.evaluate("""() => {
            // Check for sign-in button (not logged in)
            const signin = document.querySelector('.signin');
            if (signin && signin.checkVisibility()) return false;
            // Check for user dropdown (logged in)
            const user = document.querySelector('.dasher');
            if (user) return true;
            return false;
        }""")

        if logged_in:
            print("\n  ✓ SUCCESS: Logged in to Lichess")
            # Try to get username
            username = page.evaluate("""() => {
                const link = document.querySelector('.user-link, .site-title-nav .user');
                return link ? link.innerText.trim() : 'unknown';
            }""")
            print(f"    Username: {username}")
        else:
            print("\n  ✗ NOT LOGGED IN")
            print("    Cookies may be expired or invalid.")
            print("    Export fresh cookies from an active Lichess session.")

        browser.close()


if __name__ == "__main__":
    main()
