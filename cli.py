#!/usr/bin/env python3
"""
CLI Layer — entry point for the Binance Futures Trading Bot.

Usage examples:
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 30000
  python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 30000 --log-level DEBUG
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from typing import Optional
from dotenv import load_dotenv
load_dotenv() 

from bot.logging_config import setup_logging

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
DIM = "\033[2m"


def _c(text: str, color: str) -> str:
    """Apply ANSI colour if stdout is a TTY."""
    return f"{color}{text}{RESET}" if sys.stdout.isatty() else text


def _separator(char: str = "─", width: int = 55) -> str:
    return _c(char * width, DIM)


def print_request_summary(symbol, side, order_type, quantity, price) -> None:
    print()
    print(_separator())
    print(_c("  ORDER REQUEST SUMMARY", BOLD))
    print(_separator())
    print(f"  Symbol   : {_c(symbol, CYAN)}")
    print(f"  Side     : {_c(side, YELLOW)}")
    print(f"  Type     : {order_type}")
    print(f"  Quantity : {quantity}")
    if price:
        print(f"  Price    : {price}")
    print(_separator())


def print_order_response(result) -> None:
    from bot.orders import OrderResult  # local import to avoid circularity
    print()
    print(_c("  ORDER RESPONSE", BOLD))
    print(_separator())
    print(f"  Order ID      : {_c(str(result.order_id), CYAN)}")
    print(f"  Status        : {result.status}")
    print(f"  Executed Qty  : {result.executed_qty}")
    avg = result.avg_price
    if avg and avg != "0" and avg != "0.00000":
        print(f"  Avg Price     : {avg}")
    print(_separator())


def print_success(order_id: int) -> None:
    print()
    print(_c(f"  ✔  Order {order_id} placed successfully.", GREEN + BOLD))
    print()


def print_failure(message: str) -> None:
    print()
    print(_c(f"  ✘  Order failed: {message}", RED + BOLD))
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            Binance USDT-M Futures Testnet — Trading Bot CLI
            ─────────────────────────────────────────────────
            Place MARKET or LIMIT orders on the Binance Futures Testnet.

            API credentials are read from environment variables:
              BINANCE_API_KEY    — your Testnet API key
              BINANCE_API_SECRET — your Testnet API secret
        """),
        epilog=textwrap.dedent("""\
            Examples:
              python cli.py --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.01
              python cli.py --symbol ETHUSDT --side SELL --type LIMIT  --quantity 0.1 --price 2000
        """),
    )

    parser.add_argument("--symbol",    required=True,  help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side",      required=True,  choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("--type",      required=True,  dest="order_type",
                        choices=["MARKET", "LIMIT"], help="Order type")
    parser.add_argument("--quantity",  required=True,  type=float, help="Order quantity")
    parser.add_argument("--price",     required=False, type=float, default=None,
                        help="Limit price (required for LIMIT orders)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Console log verbosity (default: INFO)")
    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(args.log_level)

    
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        print_failure(
            "BINANCE_API_KEY and BINANCE_API_SECRET environment variables must be set."
        )
        logger.error("Missing API credentials in environment.")
        sys.exit(1)

   
    print_request_summary(
        symbol=args.symbol.upper(),
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
    )

    
    from bot.validators import ValidationError, validate_order_inputs

    try:
        params = validate_order_inputs(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
    except ValidationError as exc:
        print_failure(str(exc))
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    
    from bot.client import BinanceAPIError, BinanceClient, NetworkError
    from bot.orders import OrderService

    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        service = OrderService(client)
        result = service.place_order(params)
    except NetworkError as exc:
        print_failure(f"Network error — {exc}")
        logger.error("Network error: %s", exc)
        sys.exit(1)
    except BinanceAPIError as exc:
        print_failure(f"[{exc.code}] {exc.message}")
        logger.error("API error %s: %s", exc.code, exc.message)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print_failure(f"Unexpected error — {exc}")
        logger.exception("Unexpected exception: %s", exc)
        sys.exit(1)


    print_order_response(result)
    print_success(result.order_id)


if __name__ == "__main__":
    main()