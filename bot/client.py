
from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.logging_config import get_logger

logger = get_logger(__name__)

BASE_URL = "https://testnet.binancefuture.com"
ORDER_ENDPOINT = "/fapi/v1/order"
RECV_WINDOW = 5_000  
DEFAULT_TIMEOUT = 10  


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")


class NetworkError(Exception):
    """Raised on connection / timeout failures."""


class BinanceClient:
    """Thin, stateless wrapper around the Binance Futures REST API."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._session = self._build_session()

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        signed = self._sign(params)
        url = BASE_URL + ORDER_ENDPOINT
        headers = {"X-MBX-APIKEY": self._api_key}

        logger.info("→ POST %s | params=%s", url, self._redact(signed))

        try:
            response = self._session.post(
                url, params=signed, headers=headers, timeout=DEFAULT_TIMEOUT
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out after %ds: %s", DEFAULT_TIMEOUT, exc)
            raise NetworkError(
                f"Request to Binance timed out after {DEFAULT_TIMEOUT}s."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise NetworkError(
                "Could not connect to Binance Testnet. "
                "Check your network and try again."
            ) from exc

        logger.debug(
            "← HTTP %s | body=%s", response.status_code, response.text[:500]
        )

        return self._parse_response(response)

    @staticmethod
    def _build_session() -> requests.Session:
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        return session

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        signed = dict(params)
        signed["timestamp"] = int(time.time() * 1_000)
        signed["recvWindow"] = RECV_WINDOW

        query_string = urllib.parse.urlencode(signed)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        signed["signature"] = signature
        return signed

    @staticmethod
    def _parse_response(response: requests.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:200])
            raise BinanceAPIError(-1, f"Non-JSON response: {response.text[:200]}")

       
        if response.status_code != 200 or (
            isinstance(data, dict) and "code" in data and data["code"] != 200
        ):
            code = data.get("code", response.status_code)
            msg = data.get("msg", response.text)
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        logger.info("API call successful: orderId=%s", data.get("orderId", "N/A"))
        return data

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***"
        return redacted