# Lichess DOM Selector Audit

**Date:** 2026-06-21 | **Method:** Playwright headless Chromium (realistic UA)
**Pages tested:** Homepage, TV (live game), Analysis, Puzzles

---

## Confirmed Selectors

### Board element (all pages)
| Selector | Tag | Notes |
|----------|-----|-------|
| **`cg-board`** | `<CG-BOARD>` | Primary. Present on every page with a board. |
| `.cg-wrap` | `<DIV>` or `<SPAN>` | Parent container; carries orientation & manipulable classes |

### Board bounding rect
Use `page.evaluate("document.querySelector('cg-board').getBoundingClientRect()")` → `{x, y, width, height}`  
Returns pixel position + dimensions of the interactive board area.

### Orientation
Detected from `.cg-wrap`'s class list:
| Selector | Meaning |
|----------|---------|
| `.cg-wrap.orientation-white` | Board oriented from White's perspective |
| `.cg-wrap.orientation-black` | Board oriented from Black's perspective |
| `.cg-wrap.manipulable` | Interactive board (vs. mini-board on homepage) |

*Preferred selector:* `.cg-wrap.manipulable.orientation-white` / `.cg-wrap.manipulable.orientation-black`

### Turn indicator
| Selector | Meaning |
|----------|---------|
| **`.rclock.running`** | The actively-counting clock (whose turn it is) |
| `.rclock-top` | Top clock (usually opponent on game page) |
| `.rclock-bottom` | Bottom clock (usually you on game page) |
| `.rclock-white` | White player's clock |
| `.rclock-black` | Black player's clock |

**Turn detection algorithm:**
1. Query `.rclock.running`
2. Check if it has class `rclock-white` or `rclock-black`
3. That color has the turn

### Square state classes (on `<square>` elements in `<cg-board>`)
| Class | Meaning |
|-------|---------|
| **`selected`** | Piece is currently selected (clicked) |
| **`last-move`** | Source or destination of the most recent move |
| `move-dest` | Legal destination square (shown after selecting a piece) |
| `en-passant` | En passant destination highlight |
| `check` | King is in check highlight |

### Game state / overlays
| Selector | Meaning |
|----------|---------|
| `.game-over` | Game over dialog |
| `.result` | Game result display |
| `.promotion` / `.promotion-choice` | Promotion piece selection dialog |
| `.draw-offer` | Draw offer notification |
| `.offer-draw` | Draw offer button |

### Other useful elements
| Selector | Tag | Notes |
|----------|-----|-------|
| `.player` | `<DIV>` | Player info (name, rating, title) |
| `.moves` | — | Moves list (not always rendered) |
| `main.round` | `<MAIN>` | Game round container |
| `.round__board` | — | Board section container |

---

## Critical Finding: Design Doc Selector `.rclock-turn` Is Wrong

The design document's proposed turn indicator selector **`.rclock-turn` does not exist** on Lichess.  
**Correct approach:** Use `.rclock.running` + color class (`.rclock-white` / `.rclock-black`).

This is the highest-risk selector. The audit confirms it must be fixed before implementation.

---

## Board DOM Structure (from live game)

```
<cg-board>                          ← board element
  <square class="selected" ...>     ← highlighted squares
  <square class="last-move" ...>
  <piece class="white queen" ...>   ← pieces
<cg-container>
<div class="cg-wrap cgv1 orientation-white manipulable">
  <div class="analyse__board main-board">
    <main class="analyse variant-standard">
```

---

## Clock/Turn DOM

```
<div class="rclock rclock-bottom rclock-white running">   ← active clock
  <div class="bar"></div>                                  ← time bar
  <div class="time">00:17</div>
</div>
<div class="rclock rclock-top rclock-black">               ← opponent clock
  <div class="bar"></div>
  <div class="time">00:33</div>
</div>
```

---

## Verified Against
- Homepage: mini-board TV preview
- TV page: live game with running clocks
- Analysis board: full board, clickable, FEN-loadable
- Puzzles: interactive puzzle board
- Game page (completed): analysis replay view
