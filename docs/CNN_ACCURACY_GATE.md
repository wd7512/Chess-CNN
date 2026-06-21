# CNN Accuracy Gate Report

**Date:** 2026-06-21 | **Model:** `Piece_Classifier.h5`
**Test method:** Lichess analysis board rendering → Playwright screenshot → board crop → 64 tiles → CNN → FEN

## Result: PASSED ✓

| Metric | Value |
|--------|-------|
| FEN-level accuracy | 5/5 (100.0%) |
| Average tile accuracy | 100.0% |
| Threshold | ≥90% |

## Per-Position Results

| Position | Status | Input FEN | Output FEN | Tile Acc. |
|----------|--------|-----------|------------|-----------|
| Opening (Italian Game) | PASS | `r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R` | `r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R` | 100.0% |
| Midgame (queens traded, imbalanced) | PASS | `r1b2rk1/pp2ppbp/2np2p1/8/2PNP3/6PB/PP3P1P/R2QKB1R` | `r1b2rk1/pp2ppbp/2np2p1/8/2PNP3/6PB/PP3P1P/R2QKB1R` | 100.0% |
| Endgame (few pieces) | PASS | `8/8/3k4/8/2K5/8/8/8` | `8/8/3k4/8/2K5/8/8/8` | 100.0% |
| Endgame (king + pawns) | PASS | `8/5k2/8/4K3/6P1/8/8/8` | `8/5k2/8/4K3/6P1/8/8/8` | 100.0% |
| Complex (castling + bishops) | PASS | `r3k2r/ppp2ppp/2n5/3N4/1b2P3/4B3/PPPP1PPP/R3K2R` | `r3k2r/ppp2ppp/2n5/3N4/1b2P3/4B3/PPPP1PPP/R3K2R` | 100.0% |

## Notes

- Screenshots saved in `docs/cnn_test_screenshots/`
- FEN comparison uses piece placement only (no castling/en-passant from CNN)
- Orientation: default white perspective on analysis board
