#!/usr/bin/env python3
"""Phase 0.2: CNN Accuracy Gate.

Tests Piece_Classifier.h5 against known FENs rendered on Lichess analysis board.
Gate: ≥90% FEN-level accuracy to proceed.
"""

import json
import os
import sys
import time

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # suppress TF warnings

import cv2
import numpy as np
import tensorflow as tf
from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(REPO, "Models", "Piece_Classifier.h5")
REPORT_PATH = os.path.join(REPO, "docs", "CNN_ACCURACY_GATE.md")
SCREENSHOT_DIR = os.path.join(REPO, "docs", "cnn_test_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Ground truth FENs to test (opening, midgame, endgame)
TEST_POSITIONS = [
    {
        "name": "Opening (Italian Game)",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 4",
    },
    {
        "name": "Midgame (queens traded, imbalanced)",
        "fen": "r1b2rk1/pp2ppbp/2np2p1/8/2PNP3/6PB/PP3P1P/R2QKB1R w KQ - 0 10",
    },
    {
        "name": "Endgame (few pieces)",
        "fen": "8/8/3k4/8/2K5/8/8/8 w - - 0 1",
    },
    {
        "name": "Endgame (king + pawns)",
        "fen": "8/5k2/8/4K3/6P1/8/8/8 w - - 0 1",
    },
    {
        "name": "Complex (castling + bishops)",
        "fen": "r3k2r/ppp2ppp/2n5/3N4/1b2P3/4B3/PPPP1PPP/R3K2R w KQkq - 0 10",
    },
]


# ---- CNN pipeline (extracted from src.py) ----
piece_model = None


def load_model():
    global piece_model
    if piece_model is None:
        print(f"Loading model from {MODEL_PATH}...")
        piece_model = tf.keras.models.load_model(MODEL_PATH)
        print(f"  Model loaded. Input shape: {piece_model.input_shape}")
    return piece_model


LABELS = {0: '-', 1: 'B', 2: 'K', 3: 'N', 4: 'P', 5: 'Q', 6: 'R',
          7: 'b', 8: 'k', 9: 'n', 10: 'p', 11: 'q', 12: 'r'}


def one_hot_to_label(arr):
    return LABELS[np.argmax(arr)]


def undo_prepare_fen(arr):
    import chess
    board = chess.Board("8/8/8/8/8/8/8/8")
    arr_rev = np.reshape(arr, (8, 8))
    arr_out = []
    for row in arr_rev[::-1]:
        arr_out.append(row[::])
    arr_out = np.ravel(arr_out)
    for i, square in enumerate(chess.SQUARES):
        if arr_out[i] != "-":
            board.set_piece_at(square, chess.Piece.from_symbol(arr_out[i]))
    return board.fen().split(" ")[0]


def crop_board(screenshot_path, board_rect):
    """Crop the board region from a screenshot using OpenCV.
    
    Uses board_rect from Playwright's getBoundingClientRect().
    Adds a small margin since the rect may not perfectly align with pixel boundaries.
    """
    img = cv2.imread(screenshot_path)
    if img is None:
        return None

    x, y, w, h = int(board_rect["x"]), int(board_rect["y"]), int(board_rect["w"]), int(board_rect["h"])
    margin = 2  # small margin to avoid cropping edge pixels
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(img.shape[1] - x, w + 2 * margin)
    h = min(img.shape[0] - y, h + 2 * margin)
    
    cropped = img[y:y + h, x:x + w]
    return cropped


def classify_screenshot(board_img):
    """Run the full CNN pipeline on a cropped board image.
    
    Returns: (FEN_string, label_grid as 8x8 list)
    """
    gray = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (200, 200))
    
    # Split into 64 tiles
    inputs = []
    for i in range(8):
        for j in range(8):
            tile = resized[i * 25:(i + 1) * 25, j * 25:(j + 1) * 25] / 255.0
            inputs.append(tile)
    
    # Classify
    model = load_model()
    preds = model(np.array(inputs))
    labels = [one_hot_to_label(p) for p in preds]
    grid = [labels[i * 8:(i + 1) * 8] for i in range(8)]
    
    # Assemble FEN
    fen = undo_prepare_fen(labels)
    return fen, grid


def fen_to_grid(fen_str):
    """Convert a FEN to an 8x8 grid for display."""
    chars = []
    for ch in fen_str.split(" ")[0]:
        if ch.isdigit():
            chars.extend(["."] * int(ch))
        elif ch == "/":
            continue
        else:
            chars.append(ch)
    return [chars[i * 8:(i + 1) * 8] for i in range(8)]


def compare_grids(actual, expected):
    """Compare two 8x8 grids and return per-square matches."""
    matches = 0
    total = 64
    errors = []
    for i in range(8):
        for j in range(8):
            a = actual[i][j] if actual[i][j] != "-" else "."
            e = expected[i][j] if expected[i][j] not in "-." else "."
            if a == e:
                matches += 1
            else:
                errors.append((i, j, e, a))
    return matches, total, errors


def test_position(page, pos, save_screenshots=True):
    """Test a single position."""
    name = pos["name"]
    fen = pos["fen"]
    
    # URL-encode the FEN (replace spaces with _)
    url_fen = fen.replace(" ", "_")
    url = f"https://lichess.org/analysis/{url_fen}"
    
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"FEN: {fen}")
    print(f"URL: {url}")
    
    page.goto(url, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(4000)
    
    # Get board rect
    board_rect = page.evaluate("""() => {
        const b = document.querySelector('cg-board');
        if (!b) return null;
        const r = b.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height};
    }""")
    if not board_rect:
        print(f"  ERROR: No board found on page")
        return None
    
    print(f"  Board rect: ({board_rect['x']:.0f}, {board_rect['y']:.0f}) {board_rect['w']:.0f}×{board_rect['h']:.0f}")
    
    # Screenshot
    ss_path = os.path.join(SCREENSHOT_DIR, f"{name.replace(' ', '_').lower()}.png")
    if save_screenshots:
        page.screenshot(path=ss_path, full_page=False)
        print(f"  Screenshot: {ss_path}")
    
    # Crop board
    board_img = crop_board(ss_path, board_rect)
    if board_img is None:
        print(f"  ERROR: Could not read screenshot")
        return None
    
    # Save cropped board for inspection
    crop_path = ss_path.replace(".png", "_cropped.png")
    cv2.imwrite(crop_path, board_img)
    print(f"  Cropped board: {crop_path}")
    
    # Classify
    fen_out, grid = classify_screenshot(board_img)
    print(f"  CNN FEN: {fen_out}")
    
    # Compare
    expected_grid = fen_to_grid(fen)
    matches, total, errors = compare_grids(grid, expected_grid)
    accuracy = matches / total * 100
    
    print(f"  Accuracy: {matches}/{total} tiles ({accuracy:.1f}%)")
    
    if errors:
        print(f"  Errors ({len(errors)}):")
        for i, j, exp, got in errors[:10]:
            rank = 8 - i
            file_letter = chr(ord('a') + j)
            print(f"    {file_letter}{rank}: expected {exp}, got {got}")
    
    result = {
        "name": name,
        "fen_input": fen,
        "fen_output": fen_out,
        "fen_match": fen.split(" ")[0] == fen_out,
        "tile_accuracy_pct": accuracy,
        "matches": matches,
        "total": total,
        "errors": errors,
    }
    return result


def main():
    global piece_model
    
    print("=" * 60)
    print("CNN Accuracy Gate — Phase 0.2")
    print("=" * 60)
    print(f"Model: {MODEL_PATH}")
    print(f"Screenshots: {SCREENSHOT_DIR}/")
    
    # Load model first
    load_model()
    
    # Run tests
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = context.new_page()
        
        for pos in TEST_POSITIONS:
            r = test_position(page, pos, save_screenshots=True)
            if r:
                results.append(r)
        
        browser.close()
    
    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    
    fen_matches = sum(1 for r in results if r["fen_match"])
    print(f"FEN-level accuracy: {fen_matches}/{len(results)} ({fen_matches/len(results)*100:.0f}%)")
    
    tile_accs = [r["tile_accuracy_pct"] for r in results]
    avg_tile = sum(tile_accs) / len(tile_accs)
    min_tile = min(tile_accs)
    print(f"Tile-level accuracy: avg={avg_tile:.1f}%, min={min_tile:.1f}%")
    
    print(f"\nPer-position:")
    for r in results:
        status = "✓ PASS" if r["fen_match"] else "✗ FAIL"
        print(f"  {status} {r['name']}: FEN={'match' if r['fen_match'] else 'MISMATCH'} tiles={r['tile_accuracy_pct']:.1f}%")
        if not r["fen_match"]:
            print(f"         Input:  {r['fen_input']}")
            print(f"         Output: {r['fen_output']}")
    
    overall_fen_accuracy = fen_matches / len(results) * 100 if results else 0
    passed = overall_fen_accuracy >= 90.0
    
    print(f"\n{'='*60}")
    print(f"GATE: ≥90% FEN-level accuracy = {'PASSED ✓' if passed else 'FAILED ✗'}")
    print(f"      {overall_fen_accuracy:.1f}% ({fen_matches}/{len(results)} positions correct)")
    print(f"{'='*60}")
    
    # Write report
    write_report(results, passed, fen_matches, len(results), overall_fen_accuracy)
    
    if not passed:
        print("\nWARNING: CNN accuracy below threshold. Consider:")
        print("  - Injecting Lichess CSS to force training-compatible theme")
        print("  - Fine-tuning the CNN on actual Lichess screenshots")
        print("  - Proceeding (retry mode) — acceptable per your earlier decision")
        sys.exit(1)
    else:
        print("\nProceeding to Phase 0.3 (Docker smoke test).")


def write_report(results, passed, fen_matches, total, fen_accuracy):
    md = f"""# CNN Accuracy Gate Report

**Date:** 2026-06-21 | **Model:** `Piece_Classifier.h5`
**Test method:** Lichess analysis board rendering → Playwright screenshot → board crop → 64 tiles → CNN → FEN

## Result: {'PASSED ✓' if passed else 'FAILED ✗'}

| Metric | Value |
|--------|-------|
| FEN-level accuracy | {fen_matches}/{total} ({fen_accuracy:.1f}%) |
| Average tile accuracy | {sum(r['tile_accuracy_pct'] for r in results)/len(results):.1f}% |
| Threshold | ≥90% |

## Per-Position Results

| Position | Status | Input FEN | Output FEN | Tile Acc. |
|----------|--------|-----------|------------|-----------|
"""
    for r in results:
        status = "PASS" if r["fen_match"] else "FAIL"
        md += f"| {r['name']} | {status} | `{r['fen_input'].split(' ')[0]}` | `{r['fen_output']}` | {r['tile_accuracy_pct']:.1f}% |\n"

    md += f"""
## Notes

- Screenshots saved in `docs/cnn_test_screenshots/`
- FEN comparison uses piece placement only (no castling/en-passant from CNN)
- Orientation: default white perspective on analysis board
"""
    if not passed:
        md += """
## Next Steps (below threshold)

User decision: proceed with retry fallback. CNN errors trigger re-classification loop.
"""

    with open(REPORT_PATH, "w") as f:
        f.write(md)
    print(f"\nReport -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
