# Chess-CNN Self-Grill Report

**Date:** 2026-06-21  
**Griller:** opencode (big-pickle, plan agent)  
**Q&A turns:** 11 + summary

---

## Q&A Transcript

### Q1: board.turn and castling/en-passant
The FEN from CNN only encodes piece placement — no castling rights, no en-passant square, no halfmove clock. `chess.Board(fen).castling_rights` defaults to `KQkq`, so the engine thinks castling is always legal if king and rook are on starting squares. This could produce illegal moves.

**Verdict:** Correct. The engine will happily suggest O-O after the king has moved.

---

### Q2: MSE orientation heuristic blind spot
Lines 144-152 compare only the rightmost column of pixels (50 pixels). This only works if the site has a detectable border difference between white/black orientation. If the board is cropped tightly or has uniform borders, the heuristic is comparing noise. The orientation CNN would have used global features.

**Verdict:** Correct. The MSE hack is site-specific and brittle.

---

### Q3: eval_board + eval_space perspective and timing
Both functions score from white's perspective (consistent). But `eval_space` is called after the recursive move is pushed, meaning it evaluates mobility at different game states across depths. At depth 3 it measures our mobility; at depth 1 it measures opponent mobility. Asymmetric across the tree.

**Verdict:** Partially corrected by grill. The actual pattern: odd depths measure root-player mobility, even depths measure opponent mobility. Not catastrophic since the scale is small, but not clean design.

---

### Q4: Opening book called at every node
`reader.get(BOARD)` is called inside the recursive search, not just at the root. This means:
1. Wasted binary search overhead at every node
2. The "opponent" in the search picks book moves regardless of whether they're good, inflating the root player's evaluation
3. A tactical line reaching a book position breaks the search

**Verdict:** Correct. Fix: check book only at root, or before searching.

---

### Q5: Single-square misclassification cascade
If the CNN misclassifies one square for one frame, the engine searches a completely wrong position. It could suggest an illegal move. The click happens, the move is rejected by the site, and the bot is now desynced — it thinks it played, but the board is unchanged. On the next frame, it retries the same wrong move. Infinite loop.

**Verdict:** Correct. No guard against rejected moves at all.

---

### Q6: Black perspective click math (lines 205-209)
**Critical bug.** The formula uses `y + w` (width) instead of `y + h` (height) for vertical offset. More fundamentally, the flip formula is wrong even for square boards:

```
Current:  y + w - (8 - rank + 0.5) * sq
Correct:  y + h - (rank - 1 + 0.5) * sq
```

For rank 7, current formula gives 1.5 squares from top; correct gives 6.5. That's a ~5-square vertical error. **Every move the bot plays as black clicks on completely wrong squares.**

**Verdict:** Correct. This is the most impactful single bug.

---

### Q7: Test suite limitations
10,000 positions from 10 random half-moves, picking from only 2 legal moves each. Tests only that pruned == unpruned output. No test of chess strength, no endgame positions, no checkmate/stalemate/castling/en passant/promotion coverage. Not a test of correctness.

**Verdict:** Correct. It's a pruning consistency benchmark, not a chess test.

---

### Q8: Orientation_Classifier.h5 input shape
The model takes a 10x500x1 input — a thin horizontal strip across the full board width. The original design was to use the entire board's visual fingerprint for orientation. The MSE hack cherry-picks one column from that concept. The .h5 is still loaded at startup (line 13) but never called — dead code from a last-minute fallback.

**Verdict:** Correct reasoning. The gap between "whole-board strip CNN" and "single-column MSE hack" explains the brittleness.

---

### Q9: Edge tile border contamination
The matched region includes whatever border is in Blank_Board.png. Resizing to 200x200 compresses border pixels into edge tiles. Edge tiles are ~84% border, 16% actual square. The CNN was trained on clean tiles, so edge classifications are unreliable.

**Verdict:** Correct. Center tiles are fine; edge tiles are noisy.

---

### Q10: new_opp.png missing
`new_opp.png` is not committed to the repo. If absent, `cv2.imread` returns None and the program calls `exit()` at line 28. It's a hard startup dependency on an uncommitted file — the bot literally cannot run without someone manually screenshotting the "New Opponent" button on their target site.

**Verdict:** Correct. Not dead code — a startup crash.

---

### Q11: FEN tracking skip logic
The `fens` dict tracks `move_from` and `move_to` to skip frames during animation. But exact string matching on noisy CNN output means:
- Misclassification → FEN doesn't match move_to → bot searches and potentially moves twice
- CNN noise across frames can cause rapid position flickering
- The logic is both too strict (exact match on noisy input) and too permissive (no history verification)

**Verdict:** Correct. Identified the double-move risk from CNN noise.

---

### Q12: Highest-leverage fix
**Move validation after clicking.** After clicking a move, wait 1-2s, screenshot, verify the board changed as expected. If not, retry or re-plan.

This single defense-in-depth fix catches:
- Black perspective click bug
- Illegal moves from CNN misclassification  
- Desync cascades from rejected moves
- Any other single-point failure

Cost: ~2s/mouse click. Worth it.

**Verdict:** Correct. Defense-in-depth beats fixing individual bugs when 15+ compound.

---

## Bug Summary (ranked by severity)

| # | Severity | Bug | File:Line |
|---|----------|-----|-----------|
| 1 | **Critical** | Black perspective click formula wrong (y+w instead of y+h, wrong rank flip) | src.py:205-209 |
| 2 | **Critical** | new_opp.png missing → bot exits at startup | src.py:25-28 |
| 3 | **High** | No move validation → desync cascades from any failure | src.py:190-215 |
| 4 | **High** | FEN defaults to KQkq castling rights → illegal castling moves | src.py:179 |
| 5 | **High** | Edge tiles contaminated with border pixels → unreliable CNN on edges | src.py:138-161 |
| 6 | **Medium** | Opening book at every node inflates evaluation | Intermediate_Engines.py:187 |
| 7 | **Medium** | eval_space asymmetric across search depths | Intermediate_Engines.py:215 |
| 8 | **Medium** | Orientation CNN loaded but never used (dead code) | src.py:13 |
| 9 | **Medium** | No handle for rejected/illegal moves | src.py:213-214 |
| 10 | **Low** | test_engine.py: random.randint(0,1) only picks from first 2 moves | test_engine.py:270 |
| 11 | **Low** | test_engine.py: no correctness tests, only pruning consistency | test_engine.py:266-271 |
| 12 | **Low** | FEN tracking exact match on noisy CNN output | src.py:175 |
| 13 | **Low** | MSE orientation heuristic is site-specific and brittle | src.py:144-152 |
| 14 | **Info** | new_src.py has stub functions (YOLO board detection) — abandoned refactor | new_src.py:49-61 |
| 15 | **Info** | Transposition table in test_engine.py is module-level (grows forever) | test_engine.py:184 |

---

## Key Findings

1. **The bot cannot play as black.** The click coordinate formula is fundamentally wrong — every black move lands on the wrong square.

2. **The bot cannot start without manual setup.** new_opp.png is an uncommitted hard dependency.

3. **No failure recovery exists.** Any single CNN misclassification, illegal click, or rejected move desyncs the bot permanently.

4. **The "CNN" in Chess-CNN is real but fragile.** It works for piece classification on clean center tiles but degrades on edges due to border contamination.

5. **The engine is shallow** (3-ply, material + mobility eval) but that's the least of the problems. The vision pipeline failures dominate.
