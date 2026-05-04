# Binance Futures Testnet Trading Bot

A clean-architecture CLI trading bot for the Binance USDT-M Futures Testnet.  
Built with Python 3.x using direct REST calls (`requests`) — no third-party Binance SDK required.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── logging_config.py    # Logging setup (rotating file + console)
│   ├── validators.py        # Input validation layer
│   ├── client.py            # Binance API wrapper (signing, HTTP, errors)
│   └── orders.py            # Order business logic + response model
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   ├── app.log              # Full runtime log (auto-created)
│   ├── market_order.log     # MARKET order log
│   └── limit_order.log      # LIMIT order log
├── .env                     # API credentials (not committed to git)
├── .env.example             # Safe template for credentials
├── requirements.txt
└── README.md
```

---

## Architecture — 4 Clean Layers

| Layer | File | Responsibility |
|-------|------|----------------|
| CLI | `cli.py` | Parse args, display output, orchestrate flow |
| Validation | `bot/validators.py` | Validate & normalise all user inputs |
| Order Logic | `bot/orders.py` | Build payloads, map responses to dataclass |
| API Client | `bot/client.py` | HMAC-SHA256 signing, HTTP transport, error parsing |
| Logging | `bot/logging_config.py` | Rotating file + console handlers |

---

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- Binance Futures Testnet account

### 2. Get Testnet API Credentials
1. Go to **https://testnet.binancefuture.com**
2. Log in with your **GitHub account**
3. Click profile icon → **API Key** → **Generate Key**
4. Copy your **API Key** and **Secret Key** immediately

### 3. Create Virtual Environment

```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Create `.env` File

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here
```

---

## How to Run

```bash
python cli.py --symbol SYMBOL --side SIDE --type TYPE --quantity QTY [--price PRICE] [--log-level LEVEL]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--symbol` | Yes | e.g. `BTCUSDT` |
| `--side` | Yes | `BUY` or `SELL` |
| `--type` | Yes | `MARKET` or `LIMIT` |
| `--quantity` | Yes | e.g. `0.01` |
| `--price` | LIMIT only | e.g. `78000` |
| `--log-level` | No | `DEBUG`/`INFO`/`WARNING`/`ERROR` |

---

## Example Commands

```bash
# MARKET BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# MARKET SELL
python cli.py --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01

# LIMIT SELL (above market price)
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 78000

# LIMIT BUY (below market price)
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 74000

# Debug mode
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG
```

---

## Example Output

### MARKET Order
```
───────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
───────────────────────────────────────────────────────
  Symbol   : BTCUSDT
  Side     : BUY
  Type     : MARKET
  Quantity : 0.01
───────────────────────────────────────────────────────

  ORDER RESPONSE
───────────────────────────────────────────────────────
  Order ID      : 3865478291
  Status        : FILLED
  Executed Qty  : 0.01
  Avg Price     : 75752.40
───────────────────────────────────────────────────────

  ✔  Order 3865478291 placed successfully.
```

### LIMIT Order
```
───────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
───────────────────────────────────────────────────────
  Symbol   : BTCUSDT
  Side     : SELL
  Type     : LIMIT
  Quantity : 0.01
  Price    : 78000.0
───────────────────────────────────────────────────────

  ORDER RESPONSE
───────────────────────────────────────────────────────
  Order ID      : 13105446095
  Status        : NEW
  Executed Qty  : 0.0000
───────────────────────────────────────────────────────

  ✔  Order 13105446095 placed successfully.
```

> `Status: NEW` = order is live on exchange, waiting for BTC to reach $78,000.

### Validation Error
```
  ✘  Order failed: Price is required for LIMIT orders.
```

---

## Logging

All activity saved to `logs/app.log` automatically.

**Format:**
```
2026-05-04 15:05:17 | INFO  | bot.validators | Input validation passed
2026-05-04 15:05:18 | INFO  | bot.client     | → POST https://testnet.binancefuture.com/fapi/v1/order | signature: ***
2026-05-04 15:05:18 | INFO  | bot.client     | API call successful: orderId=13105446095
2026-05-04 15:05:18 | ERROR | bot.client     | API error -4024: Limit price can't be lower than 75752.72
```

- API signatures always redacted as `***`
- Rotating file: 5 MB max, 3 backups

---

## Error Handling

| Error | Example | Handling |
|-------|---------|----------|
| Missing credentials | No `.env` | Exit with message |
| Invalid side | `--side HOLD` | Validation error (no API call) |
| Missing price | LIMIT without `--price` | Validation error (no API call) |
| Quantity ≤ 0 | `--quantity 0` | Validation error (no API call) |
| Notional < $5 | tiny qty | Validation error (no API call) |
| API rejection | price out of range | `BinanceAPIError` with code + message |
| Invalid symbol | `XYZUSDT` | `BinanceAPIError [-1121]` |
| Network timeout | no internet | Retry 3× then friendly message |

---

## Assumptions

1. USDT-M Futures only — targets `/fapi/v1/order`
2. Testnet only — base URL is `https://testnet.binancefuture.com`
3. LIMIT orders use GTC (Good-Till-Cancelled)
4. One-way position mode — `positionSide` defaults to `BOTH`
5. Minimum notional $5 enforced for LIMIT orders
6. Credentials loaded via `.env` using `python-dotenv`
7. No third-party Binance SDK — uses raw `requests` for full control

---

## Live Test Results

| Order | Symbol | Side | Type | Price | Result |
|-------|--------|------|------|-------|--------|
| 1 | BTCUSDT | BUY | MARKET | market | ✅ FILLED |
| 2 | BTCUSDT | SELL | LIMIT | $78,000 | ✅ NEW (live on exchange) |

Real log files included in `logs/` directory.
