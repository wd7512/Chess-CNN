# Vision-Driven Chess Agent — Design Review

**Reviewer:** OWL
**Date:** 2026-06-21
**Subject:** Review of `VISION_AGENT_DESIGN.md`
**Verdict:** The design is coherent and well-structured. The pipeline logic is sound, the component boundaries are clean, and the test plan is thoughtful. However, there are several significant gaps around error recovery, Docker robustness, CNN generalization strategy, and operational concerns that need to be addressed before implementation.

---

## 1. Architecture Soundness

### What's good

The pipeline is linear and easy to reason about: screenshot → extract → classify → assemble FEN → engine → click → verify. Each step feeds the next, and there are no circular dependencies. The decision to keep the CNN and engine unchanged is pragmatic — they're proven, and the design correctly identifies them as the stable core.

The retry logic (step 7: retry from step 3 on illegal move; step 9: retry from step 8 on failed click; abort after 3 consecutive failures) is well-designed. It creates a bounded recovery loop without the risk of infinite retry cascades.

### Issues

**1.1 — No explicit handling of "our turn but board state is stale."**  
The pipeline assumes that after clicking and verifying, the board is now in the opponent's turn state. But what if the opponent moves while we're mid-execution? The 3-4s per move window is small but nonzero on a real server. The `wait_for_our_turn` at the top of the loop would catch this on the *next* iteration, but the DOM verify at step 9 checks board state *before vs after our move*. If the opponent has already moved (e.g., we're playing a fast opponent or there's a network hiccup), the "after" comparison could fail spuriously.

**Suggestion:** Add a timestamp or sequence number to the board state check. Alternatively, compare only the squares involved in the move rather than the full board — a partial diff is more robust to opponent-in-flight moves.

**1.2 — The "board stability" wait (step 1) is underspecified.**  
The doc says "wait for board stability (no animation)" but doesn't specify *how*. Lichess animates piece moves with CSS transitions. A naive `time.sleep(1)` is fragile; a DOM-based check for animation state is better but not described.

**Suggestion:** Define the stability check explicitly. Options: (a) wait for the absence of `.animating` or `.move-anim` class on the board, (b) poll the board bounding rect for 500ms and confirm it hasn't shifted, (c) use `page.wait_for_function()` to check that no CSS transitions are running on the board element.

**1.3 — No handling of Lichess UI overlays.**  
Lichess shows popups: "Game over" dialogs, "Offer draw" buttons, "Takeback" requests, "Rematch" prompts. None of these are mentioned. A draw offer popup could block the board, and a game-over dialog could prevent the next click from landing.

**Suggestion:** Add a "dismiss overlays" step before screenshot, or at minimum, handle the game-over dialog explicitly in the page state detector. The `.game-over` selector is listed but there's no logic for dismissing the dialog to read the result.

---

## 2. Component Boundaries

### What's good

The separation is clean. Each component has a single responsibility, and the interfaces between them are simple data types (tiles, labels, FEN strings, pixel coordinates). This is well-designed for testing.

### Issues

**2.1 — `dom_verify.py` is doing too much.**  
It handles page state detection, turn waiting, board stability, orientation, active color, clicking, board state comparison, and game-over detection. That's at least 3 distinct responsibilities: (a) page lifecycle management, (b) DOM interaction, (c) game state inference.

**Suggestion:** Consider splitting into `page_manager.py` (state machine, navigation, lifecycle), `dom_reader.py` (read-only DOM queries: orientation, turn, board state), and `dom_actor.py` (click actions, verification). This is a minor concern for v1 but will matter when debugging — when a DOM check fails, you want to know whether it's a lifecycle issue or a DOM issue.

**2.2 — `board_extractor.py` mixes DOM access and image processing.**  
`get_board_rect(page, selectors)` takes a Playwright page object, while `crop_board` and `split_tiles` are pure OpenCV. This means `board_extractor` has two reasons to change: DOM structure changes and image processing changes.

**Suggestion:** Move `get_board_rect` into `dom_reader.py` (or wherever DOM queries live). `board_extractor` should accept a rect dict and an image — pure image processing with no browser dependency. This also makes it easier to test with synthetic images.

**2.3 — `chess_agent.py` is the orchestrator but also contains game logic.**  
The doc says it handles "cross-move consistency: verify board changed after each move." This logic could live in `dom_verify.py` or a dedicated `game_state.py`. The orchestrator should coordinate, not implement game rules.

**Suggestion:** Extract a `game_state.py` module that tracks the last known board state and determines whether a move was successfully applied. The orchestrator calls `game_state.update()` and `game_state.is_consistent()`.

---

## 3. Risk Assessment

### What's covered well

The known risks table is honest and practical. The CNN generalization risk is correctly identified as the highest. The DOM selector centralization is a good mitigation. The 3-failure abort prevents infinite loops.

### Missing risks

**3.1 — Network partition / Lichess server issues.**  
No mention of what happens if the WebSocket connection to Lichess drops mid-game. Lichess uses WebSocket for real-time game updates. If the connection drops, the DOM may not update, and the agent could be staring at a stale board forever.

**Mitigation:** Add a heartbeat check — if the board hasn't changed and it's been >30s since the opponent should have moved, check the connection. Playwright can listen for WebSocket events or network failures.

**3.2 — Lichess anti-bot measures.**  
Lichess actively detects and blocks bots that aren't registered through their official bot API. A headless Playwright browser playing moves in casual games may trigger rate-limiting, CAPTCHAs, or account suspension.

**Mitigation:** This should be called out as a project risk. The agent should play against other bots (which is allowed via the Lichess Bot API) or use a test account. At minimum, document that this is a risk to the account.

**3.3 — Cookie expiry during a game.**  
The doc mentions this briefly but doesn't quantify it. Lichess session cookies can expire after a few hours. A long game (200 moves at 3-4s each = ~10-13 minutes) is probably fine, but if the game goes long or the cookies are near expiry, mid-game expiry is possible.

**Mitigation:** Check cookie validity before starting. Add a "session refresh" step if possible (Lichess supports token refresh).

**3.4 — Clock pressure.**  
The doc says "casual/unrated only" but doesn't enforce this. If the agent accidentally joins a timed game, 3-4s per move may exceed the clock.

**Mitigation:** Add a check at game start: if the clock is visible and the time control is <10 minutes, abort with a clear message.

**3.5 — Stale FEN after opponent's move.**  
After the opponent moves, the FEN on the page changes. But the agent reads the FEN by screenshot+CNN, not from the DOM. If the opponent's move animation is still running when the screenshot is taken, the CNN may capture a board mid-animation.

**Mitigation:** This is partially covered by the "board stability" wait, but the interaction between animation state and FEN accuracy should be explicitly tested.

---

## 4. Testability

### What's good

The unit test plan is solid. Each component has a corresponding test file, and the tests are designed to run without Docker or a browser. The e2e smoke test that mocks everything is a good sanity check.

### Issues

**4.1 — No contract tests between components.**  
The unit tests test each component in isolation with mocks. But there are no tests that verify the *contracts* between components. For example: does `board_extractor` actually produce 64 tiles of 25×25 from a real Lichess screenshot? Does `piece_classifier` accept the exact format that `board_extractor` produces?

**Suggestion:** Add contract tests that chain two components together with real (or realistic) data. For example: screenshot → board_extractor → piece_classifier, using a known Lichess position. This catches shape mismatches, channel count issues (RGB vs grayscale), and normalization differences.

**4.2 — `test_dom_verify.py` with "mock Playwright page" is underspecified.**  
How do you mock a Playwright page? The doc doesn't specify the mocking approach. Playwright's page object is complex — mocking `page.query_selector()`, `page.screenshot()`, `page.mouse.click()`, and `page.wait_for_selector()` requires significant setup.

**Suggestion:** Specify the mocking framework (e.g., `unittest.mock`, `pytest-mock`, or a custom stub). Provide an example of the mock page class in the test plan. Without this, the test may end up testing the mock rather than the logic.

**4.3 — No negative/failure path tests.**  
All the described tests are happy-path. There are no tests for: CNN returning an invalid label, engine returning an illegal move, DOM timeout, board rect being zero-sized, screenshot failing.

**Suggestion:** Add at least one negative test per component. These are the tests that will save you at 2 AM when something goes wrong in Docker.

**4.4 — Phase 2 integration test uses "a local HTML page that mimics Lichess DOM structure."**  
This is a good idea but the doc doesn't specify who creates this HTML page or what it needs to replicate. Lichess's DOM is complex — the board, the pieces (using `<piece>` elements or CSS backgrounds), the coordinate labels, the animation classes.

**Suggestion:** Either (a) specify the minimal DOM structure needed for the integration test, or (b) use Lichess's actual site with a test account. A mock HTML page that doesn't accurately replicate Lichess's DOM will give false confidence.

---

## 5. Docker Feasibility

### What's good

Using the official Playwright Docker image is the right call. It bundles Chromium and all system dependencies. The `libgl1-mesa-glx` install for OpenCV headless is correct.

### Issues

**5.1 — Missing system dependencies.**  
OpenCV headless needs more than just `libgl1-mesa-glx`. The `opencv-python-headless` package typically requires `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender-dev`. The Dockerfile only installs one library.

**Suggestion:** Either use `opencv-python-headless` (which has fewer system deps) or install the full set:
```dockerfile
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev
```

**5.2 — `playwright install chromium` is redundant.**  
The `mcr.microsoft.com/playwright/python:v1.60.0-jammy` image already includes Chromium. Running `playwright install chromium` will either be a no-op or will install a second copy, wasting build time and image space.

**Suggestion:** Remove the redundant `playwright install chromium` line, or replace it with `playwright install-deps chromium` if system deps are missing.

**5.3 — No volume for screenshots/logs output.**  
The agent saves screenshots to `/app/screenshots/` inside the container. But there's no volume mount or output directory for artifacts. If the container crashes, all screenshots and logs are lost.

**Suggestion:** Add a volume mount for output:
```bash
docker run -v "$(pwd)/lichess_cookies.json:/app/lichess_cookies.json" \
           -v "$(pwd)/output:/app/screenshots" chess-agent
```

**5.4 — No health check or resource limits.**  
A headless browser in Docker can consume significant memory. No resource limits are specified. If Chromium leaks memory during a long game, the container could OOM.

**Suggestion:** Add `--memory=2g` to the docker run command in the docs. Add a health check if running as a service.

**5.5 — `requirements.txt` is not specified.**  
The doc references `requirements.txt` but doesn't list its contents. Critical dependencies include: `playwright`, `opencv-python` or `opencv-python-headless`, `tensorflow` or `keras` (for the CNN), `numpy`, `chess` (if used for FEN validation).

**Suggestion:** Either include the contents in the design doc or create the file as part of the implementation. The choice of `opencv-python` vs `opencv-python-headless` matters for Docker image size.

**5.6 — TensorFlow in Docker is heavy.**  
The CNN uses `Piece_Classifier.h5`, which implies TensorFlow/Keras. TensorFlow alone is ~1GB+ in a Docker image. This is worth noting for build times and image size.

**Suggestion:** Consider using `tensorflow-cpu` to avoid pulling GPU-related dependencies. Alternatively, consider ONNX Runtime for inference — it's much lighter and faster for a single-model forward pass.

---

## 6. CNN Generalization (Highest Risk)

### What's good

The doc correctly identifies this as the highest risk and proposes a 20-line validation script. The threshold (>90% accuracy to proceed) is a reasonable gate.

### Issues

**6.1 — "Test early" is necessary but not sufficient.**  
The mitigation is: test the CNN against Lichess screenshots, and if accuracy is <90%, retrain. But there's no plan for *what to do if retraining doesn't work*. What if the CNN architecture is fundamentally tied to the original training data's rendering style?

**Mitigation:** Define a fallback strategy. Options: (a) fine-tune the CNN on Lichess screenshots (transfer learning), (b) use a different board rendering (e.g., the Lichess board API or a custom HTML board that matches the training data), (c) accept lower accuracy and increase retry frequency, (d) use the Lichess API to read the game state directly (if available for the account type).

**6.2 — The 90% threshold is arbitrary.**  
90% tile accuracy means ~6 wrong tiles per board. That's enough to completely corrupt the FEN. A single wrong piece on a critical square (e.g., the king's position) makes the engine's move illegal, triggering a retry. If every move triggers a retry, the effective move time doubles.

**Mitigation:** Consider a per-board accuracy metric, not per-tile. What matters is whether the *FEN* is correct, not whether every tile is correct. Two wrong tiles on empty squares may produce the same FEN. Test FEN-level accuracy, not tile-level accuracy.

**6.3 — No mention of Lichess board themes.**  
Lichess users can change board themes (colors, piece sets). The default theme may differ from what the CNN was trained on. If the user's account has a custom theme, the CNN may fail even if it works on the default theme.

**Mitigation:** Either (a) force the default theme via CSS injection, (b) test against multiple themes, or (c) document that the agent requires the default theme.

**6.4 — Tile extraction may differ from training.**  
The CNN was trained on 25×25 grayscale tiles. The board extraction pipeline crops from a screenshot, resizes to 200×200, and splits into 64 tiles. But the resize interpolation, the anti-aliasing, and the exact pixel boundaries may differ from how the training data was generated. This is a silent failure mode — the CNN runs without error but produces garbage.

**Mitigation:** Compare the histogram and pixel distribution of extracted tiles against the training data. If they differ significantly, adjust the extraction pipeline (e.g., use different interpolation, add padding, adjust crop margins).

---

## 7. DOM Coupling

### What's good

Centralizing selectors in `config.py` is the right approach. It limits the blast radius of selector changes to a single file.

### Issues

**7.1 — The selectors are assumed, not verified.**  
The doc lists selectors like `.main-board`, `.rclock-turn`, `.selected`, `.game-over`, `.orientation-white`, `.orientation-black`. These are not verified against the current Lichess DOM. Lichess has changed its DOM structure multiple times in the past.

**Mitigation:** Before implementation, open Lichess in a browser, inspect the actual DOM, and verify each selector. Document the Lichess version or date when the selectors were verified.

**7.2 — `.rclock-turn` is not a real Lichess selector.**  
Lichess's turn indicator is typically `.rclock .turn` or similar. The selector `.rclock-turn` doesn't match Lichess's actual DOM as of 2026. This suggests the selectors were guessed rather than verified.

**Mitigation:** Verify all selectors against the live site. This is a "startling oops" — if the turn indicator selector is wrong, the agent will never detect its turn and will hang forever.

**7.3 — No fallback for selector changes.**  
If Lichess changes a selector, the agent aborts. There's no fallback mechanism (e.g., trying alternative selectors, or using the screenshot as a fallback for turn detection).

**Mitigation:** For critical selectors (turn indicator, board), define a primary and fallback selector. If the primary fails, try the fallback before aborting.

**7.4 — Lichess's DOM is not stable across versions.**  
Lichess deploys updates frequently. A selector that works today may break tomorrow. The design has no mechanism for detecting or adapting to DOM changes beyond manual config updates.

**Mitigation:** Add a "DOM health check" at startup: verify that all selectors resolve to elements on the page. If any fail, abort immediately with a clear message rather than failing mid-game.

---

## 8. Missing Pieces

### 8.1 — No PGN output specification.
The doc mentions "save PGN" in the architecture diagram and "Game result output (PGN + JSON summary)" in the component description, but there's no specification for:
- Where the PGN is saved (file path, stdout, both)
- What format (standard PGN with headers, or just moves)
- Whether all moves are recorded or only from the agent's perspective
- How the PGN is constructed (from the engine's move list, or from DOM move history)

**Suggestion:** Specify the PGN output format explicitly. At minimum: event, site, date, round, players, result, moves. Consider reading the move list from Lichess's DOM (the move history panel) rather than reconstructing from the engine — this captures the opponent's moves accurately.

### 8.2 — No logging format specification.
The doc says "Logging each step (screenshot, FEN, move, retries, result)" but doesn't specify:
- Log destination (stdout, file, both)
- Log format (plain text, JSON, structured)
- Log verbosity levels
- Whether screenshots are saved as files or only in memory

**Suggestion:** Define a structured logging format. JSON lines (one JSON object per line) is easy to parse and human-readable. Include: timestamp, step number, FEN, move, retry count, error (if any), screenshot filename.

### 8.3 — No graceful shutdown handling.
What happens if the Docker container is killed mid-game? What happens if the user presses Ctrl+C? There's no mention of signal handling or graceful shutdown.

**Suggestion:** Add a signal handler for SIGTERM and SIGINT. On shutdown: log the current state, save the partial PGN, close the browser cleanly.

### 8.4 — No game start automation.
The doc says "Full pre-game automation (cookie injection + manual game start is Phase 1)" is out of scope. But the agent needs to *start* a game somehow. How? Does the human manually create a game and the agent joins? Does the agent accept an open challenge? This gap makes the "no human intervention during the game" criterion ambiguous — the human intervenes *before* the game.

**Suggestion:** Document the game start procedure explicitly. Even if it's "human creates a casual game and sends the URL to the agent," this should be specified. Ideally, the agent should be able to accept an open challenge or create a seek.

### 8.5 — No move validation before clicking.
The engine picks a move based on the FEN assembled from the CNN's classification. If the CNN misclassifies the board, the engine may pick an illegal move. The doc mentions a "SANITY: is move legal on reported FEN?" check, but this only catches moves that are illegal *on the reported FEN* — it doesn't catch the case where the reported FEN is wrong but the move is legal on the wrong FEN.

**Suggestion:** After the engine picks a move, validate it against the *actual* board state by checking whether the source square actually contains the piece the engine thinks it's moving. This requires reading the DOM (Lichess highlights legal moves when you click a piece) or doing a more detailed board analysis.

### 8.6 — No en passant or promotion handling.
The click mapper maps a UCI move to source and destination squares. But UCI moves include promotion (e.g., `a7a8q`). How does the agent handle promotion? Does it always promote to queen? Does it read the promotion dialog from the DOM?

**Specify:** The promotion strategy. Always-queen is simplest but loses games where under-promotion is necessary. At minimum, document the choice.

### 8.7 — No mention of the Lichess API.
Lichess has a well-documented REST and WebSocket API. The agent could read the game state directly from the API rather than inferring it from screenshots and the CNN. This would be more reliable and faster.

**Suggestion:** Even if the CNN approach is the point of the project, consider using the Lichess API as a fallback for board state verification. The API can provide ground-truth FEN, which can be compared against the CNN's output for real-time accuracy monitoring.

### 8.8 — No timeout for the overall game.
The per-move timeout is 60s, but there's no overall game timeout. If the opponent is stalling or the game goes to 200 moves, the agent could run for hours.

**Suggestion:** Add a `GAME_TIMEOUT` constant (e.g., 30 minutes) and abort if exceeded.

### 8.9 — No specification for the `lichess_cookies.json` format.
The doc says "Human exports Lichess cookies from local browser" but doesn't specify the expected format. EditThisCookie exports cookies as a JSON array; Playwright's `context.add_cookies()` expects a specific format. These may not be compatible.

**Suggestion:** Specify the exact format expected. Provide a one-liner or script for exporting cookies in the correct format.

---

## Summary of Findings

| # | Severity | Finding | Section |
|---|----------|---------|---------|
| 1 | **High** | `.rclock-turn` selector is likely wrong — will cause infinite hang | 7.2 |
| 2 | **High** | No fallback if CNN generalization fails — "retrain" is not a plan | 6.1 |
| 3 | **High** | Missing OpenCV system dependencies in Dockerfile | 5.1 |
| 4 | **High** | No en passant/promotion handling specified | 8.6 |
| 5 | **High** | No game start procedure — "no human intervention" is ambiguous | 8.4 |
| 6 | **Medium** | No contract tests between components | 4.1 |
| 7 | **Medium** | No negative/failure path tests | 4.3 |
| 8 | **Medium** | No handling of Lichess UI overlays (draw offers, popups) | 1.3 |
| 9 | **Medium** | No network partition / WebSocket disconnect handling | 3.1 |
| 10 | **Medium** | No PGN output format specification | 8.1 |
| 11 | **Medium** | No logging format specification | 8.2 |
| 12 | **Medium** | No graceful shutdown / signal handling | 8.3 |
| 13 | **Medium** | No overall game timeout | 8.8 |
| 14 | **Medium** | Board stability wait is underspecified | 1.2 |
| 15 | **Medium** | Stale board state if opponent moves during execution | 1.1 |
| 16 | **Low** | `playwright install chromium` is redundant in official image | 5.2 |
| 17 | **Low** | No volume mount for screenshots/logs output | 5.3 |
| 18 | **Low** | `dom_verify.py` has too many responsibilities | 2.1 |
| 19 | **Low** | `board_extractor.py` mixes DOM and image processing | 2.2 |
| 20 | **Low** | TensorFlow in Docker is heavy — consider ONNX Runtime | 5.6 |
| 21 | **Low** | Lichess board theme may affect CNN accuracy | 6.3 |
| 22 | **Low** | Cookie export format not specified | 8.9 |
| 23 | **Low** | No Lichess API as fallback for board state verification | 8.7 |

---

## Overall Assessment

The design is **good but incomplete**. The core pipeline is sound, the component boundaries are clean, and the test plan is well-structured. The document demonstrates a clear understanding of the problem and a pragmatic approach to solving it.

However, the document has a pattern of **hand-waving at the edges** — critical operational details (selectors, error recovery, output formats, game start) are either unspecified or assumed. The most dangerous gaps are:

1. **The turn indicator selector is likely wrong**, which would cause the agent to hang forever on the first move.
2. **The CNN generalization mitigation has no fallback** beyond "retrain," which may not be sufficient.
3. **The Dockerfile is incomplete** — missing system deps will cause an immediate crash.
4. **No game start procedure** means the "no human intervention" criterion is unverifiable.

The document would benefit from a "pre-implementation verification" step: open Lichess, verify every selector, test the CNN against a Lichess screenshot, and confirm the Docker build works end-to-end *before* writing the main loop. This is essentially the doc's own Phase 0, and it's the most important thing missing.
