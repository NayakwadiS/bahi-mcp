# bahi-mcp

MCP server that gives AI assistants (Claude, Cursor, VS Code and others) access to **Indian mutual fund data**, **NSE/BSE market data** and **financial calculators**.

*Bahi* (बही) is the traditional Indian ledger. This server keeps the numbers straight so your assistant doesn't guess them.

> **Disclaimer:** bahi-mcp provides information and calculations from public data sources (AMFI via the [`mftool`](https://pypi.org/project/mftool/) library, and Yahoo Finance for stocks) and from assumptions you supply. It is **not investment or tax advice** and the author is not a SEBI-registered adviser. Data may be delayed or inaccurate, and tax rules change. Verify before making decisions.

## What you can ask

- "Compare these three flexi-cap funds on 3-year return, volatility and max drawdown."
- "How often has this fund beaten 12% on rolling 3-year returns?"
- "If I had invested ₹10,000 a month in scheme 119551 since January 2020, what would it be worth today, and what is my XIRR?"
- "What's the Nifty at, and how has RELIANCE done over the last year?"
- "How much tax would I pay if I sell this equity fund after 14 months with a ₹2 lakh gain?"
- "How much corpus do I need to retire at 55 if I spend ₹60,000 a month today?"

## Tools

**Mutual fund data** (AMFI)

| Tool | What it does |
|---|---|
| `search_schemes` | Search schemes by name, returns AMFI scheme codes |
| `get_scheme_quote` | Latest NAV and quote for a scheme code |
| `get_scheme_details` | Fund house, type, category, start date |
| `get_nav_history` | NAV history with optional date range (capped to keep responses small) |
| `get_portfolio_value` | Current value of a list of holdings (scheme code + units) |
| `clear_cache` | Drop cached AMFI data so the next call fetches fresh NAVs |

**Mutual fund analytics**

| Tool | What it does |
|---|---|
| `calculate_sip_returns` | Monthly SIP simulation on a fund's real NAV history: invested, units, value, absolute return, XIRR |
| `compare_funds` | Side-by-side 1/3/5-year returns, volatility, max drawdown and Sharpe ratio for 1 to 5 funds |
| `get_rolling_returns` | Distribution of rolling returns: min, max, mean, median, how often positive or above a threshold |

**Stocks and market data** (NSE/BSE, via Yahoo Finance; unofficial and best-effort)

| Tool | What it does |
|---|---|
| `get_stock_quote` | Latest price, day and 52-week range for an NSE/BSE stock |
| `get_index_quote` | Nifty 50, Sensex, Bank Nifty, Nifty IT, India VIX |
| `get_stock_history` | OHLCV history for a stock or index |

**Calculators**

| Tool | What it does |
|---|---|
| `calculate_xirr` | XIRR for any dated cash flows |
| `calculate_cagr` | CAGR between two values over a date range |
| `calculate_emi` | Loan EMI, total payment, total interest |
| `calculate_fd` / `calculate_rd` | Fixed and recurring deposit maturity |
| `calculate_lumpsum_value` | Future value of a one-time investment |
| `project_sip` | SIP projection at an assumed return, with optional yearly step-up |
| `calculate_swp` | Does a corpus last under a monthly withdrawal? |
| `plan_retirement` | Corpus needed and the monthly SIP to build it |
| `estimate_mf_tax` | Capital gains tax estimate on a fund redemption; use purchase/sale dates for exact 12-month classification |

Dates can be `DD-MM-YYYY` or `YYYY-MM-DD`.

## Install

Requires Python 3.10+.

```bash
pip install bahi-mcp                # mutual funds + calculators
pip install "bahi-mcp[stocks]"      # adds NSE/BSE stock and index data
```

Or run without installing, using [uv](https://docs.astral.sh/uv/):

```bash
uvx bahi-mcp
uvx --with yfinance bahi-mcp        # with stock data
```

## Configure your MCP client

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bahi-mcp": {
      "command": "uvx",
      "args": ["--with", "yfinance", "bahi-mcp"]
    }
  }
}
```

Drop `"--with", "yfinance"` if you don't need stock data. Restart Claude Desktop.

### Cursor and other clients

```json
{
  "mcpServers": {
    "bahi-mcp": {
      "command": "uvx",
      "args": ["--with", "yfinance", "bahi-mcp"]
    }
  }
}
```

For Cursor, save this in `~/.cursor/mcp.json`. Remove `"--with", "yfinance"` if you don't need stock data.

## Notes on data and accuracy

- **Mutual fund data** comes from AMFI through `mftool` (3.4 or newer). NAVs are published after market close, usually by about 9 PM IST. mftool caches NAVs for 24 hours, so use `clear_cache` after the evening update to see the latest.
- **Stock data** comes from Yahoo Finance through `yfinance`. It is unofficial, can be delayed, rate-limited or change without notice. Don't use it for trading decisions.
- **Tax estimates** follow the configured FY 2026-27 assumptions for equity funds (STCG 20%, LTCG 12.5% above the remaining ₹1.25 lakh annual exemption); provide purchase and sale dates for exact calendar 12-month classification, or holding days for an approximate 365-day cutoff. The exemption is shared across eligible gains in a financial year. Debt funds are modelled at slab rate only for units bought on/after 1 April 2023. Surcharge, loss set-off and older indexation rules are not modelled; verify current law and consult a tax professional.
- **Projections** (`project_sip`, `calculate_swp`, `plan_retirement`) assume constant returns. Real markets don't behave that way.

## Development

```bash
git clone https://github.com/NayakwadiS/bahi-mcp
cd bahi-mcp
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev,stocks]"
pytest
python -m bahi_mcp               # runs the server over stdio
```

Layout in `src/bahi_mcp/`:

- `analytics.py`, `fund_analytics.py`, `calculators.py`: pure Python, no network, fully tested offline
- `data.py`: AMFI access through `mftool`
- `market.py`: stock and index access through `yfinance`
- `server.py`: the MCP tool definitions

## Roadmap

- Portfolio overlap and fund-to-fund correlation
- Document search over factsheets and SEBI/RBI circulars
- Hosted version with caching

## Contributing

Issues and pull requests are welcome.

## License

MIT. See [LICENSE](LICENSE).
