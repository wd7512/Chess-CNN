# Audit Fix Batch 1 — Critical Bugs

Fix the following 3 critical bugs in the Chess-CNN repo at ~/repos/Chess-CNN.
Run `uv run python -m pytest tests/ -v` after each fix to verify.

---

## Finding #1 — Critical: Black perspective click formula wrong

- **File**: src.py, lines 204-209
- **Current behavior**: The black perspective click formula uses `y + w` (width) for vertical offset and `(8 - rank + 0.5)` for rank flip. This causes clicks to land on completely wrong squares when playing as black — a ~5-square vertical error.
- **Expected behavior**: Should use `y + h` (height) for vertical offset and `(rank - 1 + 0.5)` for rank flip. This correctly maps black's rank 7 to near the top of the board (white's view) and black's rank 1 to near the bottom.
- **Acceptance**: `uv run python -m pytest tests/test_click_math.py -v` passes (specifically `test_e7e5_symmetry` and `test_non_square_board_uses_height`)

Current buggy code (lines 204-209):
```python
            else:
                start_x = x + w - (ord(optimal_move[0]) - 97 + 0.5) * square_size
                start_y = y + w - (8 - int(optimal_move[1]) + 0.5) * square_size

                end_x = x + w - (ord(optimal_move[2]) - 97 + 0.5) * square_size
                end_y = y + w - (8 - int(optimal_move[3]) + 0.5) * square_size
```

Fix to:
```python
            else:
                start_x = x + w - (ord(optimal_move[0]) - 97 + 0.5) * square_size
                start_y = y + h - (int(optimal_move[1]) - 1 + 0.5) * square_size

                end_x = x + w - (ord(optimal_move[2]) - 97 + 0.5) * square_size
                end_y = y + h - (int(optimal_move[3]) - 1 + 0.5) * square_size
```

---

## Finding #2 — Critical: new_opp.png missing causes startup crash

- **File**: src.py, lines 25-28
- **Current behavior**: If `new_opp.png` doesn't exist, `cv2.imread` returns None and the program calls `exit()`. The bot cannot start without this file, but it's not committed to the repo.
- **Expected behavior**: If `new_opp.png` is missing, skip the "New Opponent" feature gracefully (set a flag that it's unavailable) and continue running. The bot should work without it.
- **Acceptance**: The bot starts and runs without `new_opp.png` present. The "New Opponent" auto-click feature is simply disabled.

Current code (lines 25-28):
```python
new_opp = cv2.imread('new_opp.png', cv2.IMREAD_GRAYSCALE)
if new_opp is None:
    print("Error loading new_opp image.")
    exit()
```

Fix: Replace the exit with a graceful fallback. Set `new_opp = None` and check `if new_opp is not None` before using it in the main loop (line 109).

---

## Finding #3 — Critical: No move validation after clicking

- **File**: src.py, around lines 213-220 (after pyautogui clicks)
- **Current behavior**: After clicking a move, the bot assumes it worked. If the move was rejected (wrong coordinates, illegal move), the bot is permanently desynced from the game state.
- **Expected behavior**: After clicking, wait briefly, take a new screenshot, and verify the board changed. If the expected position doesn't appear within 3 seconds, retry the click (up to 2 retries).
- **Acceptance**: The main loop has a retry mechanism. After clicking a move, it verifies the board state changed. On failure, it retries.

Add a `verify_move_played(expected_fen, max_retries=2)` function that:
1. Waits 1 second after the click
2. Takes a screenshot and classifies the board
3. Checks if the new FEN matches the expected post-move FEN
4. If not, retries the click (up to max_retries times)
5. If all retries fail, logs a warning and continues (don't crash)

---

## Constraints

- Do NOT modify test files
- Do NOT modify requirements.txt or pyproject.toml
- Run `uv run python -m pytest tests/ -v` after all fixes to verify
- Commit with message: "Fix critical bugs: black click math, new_opp.png crash, move validation"
