#!/usr/bin/env python3
"""CLI entry point for the vision-driven chess agent.

Usage:
    python run.py --url https://lichess.org/AbCdEfGh [--color white|black] [--cookie lichess_cookies.json]
"""
import argparse
import sys

from chess_agent.chess_agent import ChessAgent


def main():
    parser = argparse.ArgumentParser(description="Vision-driven chess bot for Lichess")
    parser.add_argument("--url", help="Lichess game URL (not needed with --e2e)")
    parser.add_argument("--color", choices=["white", "black"], default="white")
    parser.add_argument(
        "--cookie",
        default=None,
        help="Path to cookie JSON file (default: lichess_cookies.json in repo root)",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="E2E mode: create anonymous game via 'Play with a friend' on lichess.org",
    )
    args = parser.parse_args()

    if args.e2e:
        agent = ChessAgent(e2e=True)
    else:
        if not args.url:
            parser.error("--url is required without --e2e")
        agent = ChessAgent(
            game_url=args.url,
            our_color=args.color,
            cookie_path=args.cookie,
        )
    result = agent.run()
    print(f"\nGame result: {result}")
    sys.exit(0 if result in ("1-0", "0-1", "1/2-1/2") else 1)


if __name__ == "__main__":
    main()
