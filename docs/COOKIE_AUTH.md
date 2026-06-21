# Cookie Authentication

## How It Works

1. **Export cookies** from your browser while logged into Lichess
   - Use [EditThisCookie](https://www.editthiscookie.com/) extension (Chrome/Firefox)
   - Use [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) for Netscape format
   - Or export manually via Chrome DevTools → Application → Cookies → Export

2. **Save as** `lichess_cookies.json` in the project root

3. **Playwright loads** them via `context.add_cookies(cookies)`

## Cookie Format

Playwright's `context.add_cookies()` expects a list of cookie objects:

```json
[
    {
        "name": "lila",
        "value": "your_session_token_here",
        "domain": ".lichess.org",
        "path": "/"
    },
    {
        "name": "lila2",
        "value": "your_second_token_here",
        "domain": ".lichess.org",
        "path": "/"
    }
]
```

### Minimal required fields
| Field | Value | Notes |
|-------|-------|-------|
| `name` | (from export) | e.g. `lila`, `lila2` |
| `value` | (from export) | Session token |
| `domain` | `.lichess.org` | Dot-prefixed for subdomain access |
| `path` | `/` | Root path |

Lichess typically uses 2 cookies: `lila` (session) and `lila2` (remember-me).

### EditThisCookie export → Playwright

EditThisCookie exports extra fields (`expirationDate`, `httpOnly`, `sameSite`, `secure`, `session`, `storeId`, `id`). Playwright ignores unknown fields, so you can pass the export directly.

**Either format works**, but the minimal format is recommended for clarity.

## Mounting in Docker

```bash
docker run --memory=2g \
  -v "$(pwd)/lichess_cookies.json:/app/lichess_cookies.json" \
  -e GAME_URL="https://lichess.org/AbCdEfGh" \
  chess-agent
```

## Verifying

Run the cookie test to verify your cookies work:

```bash
python tools/test_cookie_auth.py
```

This will:
1. Load `lichess_cookies.json`
2. Inject via Playwright
3. Navigate to Lichess
4. Report whether you're logged in

## Troubleshooting

- **"Not logged in"**: Export fresh cookies (session may have expired)
- **"Cookie file not found"**: Create `lichess_cookies.json` in the project root
- **"Invalid cookie format"**: Ensure the file is a valid JSON array of objects
- **Session expires mid-game**: Lichess sessions last ~24h. For casual games this is sufficient.
