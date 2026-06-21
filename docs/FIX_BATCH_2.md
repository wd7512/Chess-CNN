# Audit Fix Batch 2 — High Severity Bugs

Fix the following 3 high-severity bugs in the Chess-CNN repo at ~/repos/Chess-CNN.
Run `uv run python -m pytest tests/ -v` after fixes to verify no regressions.

---

## Finding #4 — High: FEN defaults to KQkq castling rights

- **File**: src.py, around line 179 where chess.Board is constructed from CNN FEN
- **Current behavior**: `chess.Board(fen_from_cnn)` creates a board with default castling rights (KQkq), even if the king or rook have moved. The engine may suggest illegal castling moves.
- **Expected behavior**: After constructing the board from CNN FEN, clear castling rights since we can't infer them from visual observation alone. The bot should only allow castling if it has tracked the game from the start.
- **Acceptance**: `chess.Board` constructed from CNN output has no castling rights.

Fix: After `board = chess.Board(fens["current"])`, add:
```python
board.castling_rights = chess.BB_VOID  # Clear all castling rights
```

Note: The better long-term fix is to track castling rights through the game by detecting when kings/rook

  s move from their starting squares. But for now, clearing rights prevents illegal castling suggestions.

---

## Finding #5 — High: Opening book queried at every search node

- **File**: Intermediate_Engines.py, reader.get(BOARD) is called inside min_maxN and min_maxN_pruned
- **Current behavior**: The polyglot opening book is queried at every node in the search tree, not just the root. This inflates evaluations (opponent picks book moves regardless of quality) and wastes computation.
- **Expected behavior**: Opening book should only be checked at the root of the search (depth == N). If a book move is found at root, return it immediately without searching.
- **Acceptance**: Opening book is only checked once per move decision, at the root.

Fix: In both min_maxN and min_maxN_pruned, only call reader.get(BOARD) when at the root depth. Pass the remaining depth N to know when we're at root. Or check before calling the search function.

---

## Finding #6 — High: No handling for illegal/rejected moves

- **File**: src.py, the verify_move_played function (added in batch 1) handles retries but the FEN tracking still has issues
- **Current behavior**: After a move is clicked, the bot sets fens["move_to"] to the expected post-move FEN. If the move was rejected (illegal or wrong coordinates), the next frame shows the old position, which matches neither move_from nor move_to, causing the bot to re-search and re-click — potentially the same wrong move.
- **Expected behavior**: After a rejected move (board unchanged after click), the bot should re-classify the board and re-plan, not repeat the same move.

Fix: In the verify_move_played function, if the board hasn't changed after clicking (FEN same as pre-move), increment a retry counter and re-search. If retries exhausted, log warning and wait for opponent.

---

## Constraints

- Do NOT modify test files
- Run `uv run python -m pytest tests/ -v` after all fixes to verify no regressions
- Commit with message: "Fix high-severity bugs: castling rights, opening book, move rejection"
