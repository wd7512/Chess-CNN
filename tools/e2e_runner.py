#!/usr/bin/env python3
"""Phase 3 E2E Test Runner.

Builds the Docker image, runs a container with GAME_MODE=e2e,
streams container logs to stdout, and reports the final result.

Usage:
    python tools/e2e_runner.py [--no-build] [--timeout 3600]

Prerequisites:
    - Docker running
    - No cookies needed (anonymous play)
    - A human opponent ready to join the game
"""

import argparse
import os
import subprocess
import sys
import time

IMAGE_NAME = "chess-agent-e2e"
CONTAINER_NAME = "chess-agent-e2e-run"
OUTPUT_DIR = os.path.abspath("output")


def build_image():
    print("[E2E] Building Docker image...")
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("[E2E] Build failed:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    print("[E2E] Build complete")


def run_container(timeout_seconds):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        "docker", "run",
        "--rm",
        "--name", CONTAINER_NAME,
        "--memory=2g",
        "-e", "GAME_MODE=e2e",
        "-v", f"{OUTPUT_DIR}:/app/output",
        IMAGE_NAME,
        "python", "run.py", "--e2e",
    ]

    print(f"[E2E] Starting container (timeout={timeout_seconds}s)...")
    print(f"[E2E] Game URL will appear in logs below")
    print(f"[E2E] Share the game link with a friend to start playing")
    print("-" * 60)

    container = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    start_time = time.time()
    result_lines = []
    timed_out = False

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"\n[E2E] TIMEOUT after {timeout_seconds}s — killing container")
            container.terminate()
            timed_out = True
            break

        line = container.stdout.readline()
        if not line:
            break

        line = line.rstrip()
        print(line)
        result_lines.append(line)

    container.wait()
    print("-" * 60)

    if timed_out:
        print(f"[E2E] Result: TIMEOUT (>{timeout_seconds}s)")
        return False

    exit_code = container.returncode
    print(f"[E2E] Container exit code: {exit_code}")

    for line in reversed(result_lines):
        if '"event":"end"' in line or '"event":"game_over"' in line:
            print(f"[E2E] Last event: {line}")
            break

    if exit_code == 0:
        pgn_path = os.path.join(OUTPUT_DIR, "game.pgn")
        if os.path.exists(pgn_path):
            size = os.path.getsize(pgn_path)
            print(f"[E2E] PGN saved ({size} bytes): {pgn_path}")
        else:
            print(f"[E2E] WARNING: no PGN file at {pgn_path}")
        return True
    else:
        return False


def main():
    parser = argparse.ArgumentParser(description="E2E test runner for chess agent")
    parser.add_argument("--no-build", action="store_true", help="Skip Docker build step")
    parser.add_argument(
        "--timeout", type=int, default=3600,
        help="Maximum runtime in seconds (default: 3600 = 60 min)",
    )
    args = parser.parse_args()

    if not args.no_build:
        build_image()
    else:
        print("[E2E] Skipping build (--no-build)")

    success = run_container(args.timeout)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
