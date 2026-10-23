# bahi-mcp

MCP server that gives AI assistants (Claude, Cursor, VS Code and others) access to **Indian mutual fund data** and **investor analytics**.

*Bahi* (बही) is the traditional Indian ledger. This server keeps the numbers straight so your assistant doesn't guess them.

> **Disclaimer:** bahi-mcp provides information and calculations from publicly available data (AMFI, via the [`mftool`](https://pypi.org/project/mftool/) library). It is **not investment advice** and the author is not a SEBI-registered adviser. Data may be delayed or inaccurate. Verify before making decisions.

## What you can ask

- "Find SBI midcap direct growth schemes and give me the latest NAV."
- "If I had invested ₹10,000 a month in scheme 119551 since January 2020, what would it be worth today, and what is my XIRR?"
- "What's the CAGR if ₹1,00,000 became ₹2,40,000 between 2018-04-01 and 2025-04-01?"

## Tools

| Tool | What it does |
|---|---|
| `search_schemes` | Search schemes by name, returns AMFI scheme codes |
| `get_scheme_quote` | Latest NAV and quote for a scheme code |
| `get_scheme_details` | Fund house, type, category, start date |
| `get_nav_history` | NAV history with optional date range (capped to keep responses small) |
| `calculate_sip_returns` | Monthly SIP simulation on real NAV history: invested, units, value, absolute return, XIRR |
| `calculate_xirr` | XIRR for any dated cash flows |
| `calculate_cagr` | CAGR between two values over a date range |

Dates can be `DD-MM-YYYY` or `YYYY-MM-DD`.

## Install

Requires Python 3.10+.

```bash
pip install bahi-mcp
```

Or run without installing, using [uv](https://docs.astral.sh/uv/):

```bash
uvx bahi-mcp
```

## Configure your MCP client

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bahi-mcp": {
      "command": "uvx",
      "args": ["bahi-mcp"]
    }
  }
}
```

Restart Claude Desktop.

### Cursor and other clients

```json
{
  "bahi-mcp": {
    "command": "uvx",
    "args": ["bahi-mcp"]
  }
}
```

## Development

```bash
git clone https://github.com/YOUR_USERNAME/bahi-mcp
cd bahi-mcp
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m bahi_mcp               # runs the server over stdio
```

Calculations live in `src/bahi_mcp/analytics.py` (pure Python, fully tested offline). Data access is in `data.py`, and the MCP tools are defined in `server.py`.

## Roadmap

- Portfolio overlap and fund comparison
- Rolling returns and risk metrics
- Tax-aware SIP and redemption planning
- Document search over factsheets and SEBI/RBI circulars
- Hosted version with caching

## Contributing

Issues and pull requests are welcome.

## License

MIT. See [LICENSE](LICENSE).
