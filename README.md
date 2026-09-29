# playwright-mcp

A standalone [MCP](https://modelcontextprotocol.io) server (`browser_mcp.py`) that lets an
LLM read JavaScript-rendered webpages as token-efficient Markdown.

It keeps one warm headless Chromium instance, opens an isolated browser context per
request, extracts the main content with `trafilatura` (dropping navigation, ads and
boilerplate), and converts it to Markdown with `markdownify`.

## Tool

`fetch_webpage_markdown(url: str, wait_for_selector: str = "") -> str`

- Navigates with `wait_until="domcontentloaded"` (15 s timeout).
- If `wait_for_selector` is given, waits up to 5 s for it; otherwise waits 1 s for client hydration.
- Falls back to the raw page HTML if content extraction fails.
- Output uses ATX (`#`) headers; `script`, `style`, `noscript`, `svg` and `button` are stripped.

## Recommended: run in Docker (isolated)

Dependencies, Chromium and every page it opens live inside a throwaway container:
non-root user, no host mounts, no extra capabilities, memory/CPU capped, removed on exit.
Nothing is installed on your system.

```bash
docker build -t browser-mcp .
```

```json
{
  "mcpServers": {
    "browser": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--memory=1g", "--cpus=1", "--pids-limit=256",
        "--ipc=host",
        "browser-mcp"
      ]
    }
  }
}
```

Notes: only `http(s)` URLs are accepted (no `file://`). The container can still reach your
LAN/localhost services through Docker's network; add a restrictive `--network` or firewall
rule if you need to block that.

## Install without Docker

Requires Python 3.10+. Use a virtual environment:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

On Linux, Chromium may also need system libraries: `sudo playwright install-deps chromium`.
Outside Docker, Chromium's own sandbox is enabled; set `BROWSER_MCP_NO_SANDBOX=1` only if it
cannot start (for example as root or in a container).

## Register with an MCP client

Add to `claude_desktop_config.json` (or your client's MCP settings), using the absolute
path to `browser_mcp.py` and the Python interpreter that has the dependencies installed:

```json
{
  "mcpServers": {
    "browser": {
      "command": "python",
      "args": ["/absolute/path/to/playwright-mcp/browser_mcp.py"]
    }
  }
}
```

Restart the client after editing the config.

## Usage example

Ask the assistant:

> Use fetch_webpage_markdown to read https://example.com and summarize it.

For pages that render content client-side, pass a selector to wait for:

```json
{
  "url": "https://news.ycombinator.com/",
  "wait_for_selector": "tr.athing"
}
```

To try the server interactively: `npx @modelcontextprotocol/inspector python browser_mcp.py`.
