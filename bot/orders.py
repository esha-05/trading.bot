
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceClient
from bot.logging_config import get_logger
from bot.validators import OrderParams

logger = get_logger(__name__)

@dataclass
class OrderResult:
    """Normalised view of a Binance order response."""

    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    raw: Dict[str, Any]

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "OrderResult":
        return cls(
            order_id=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            raw=data,
        )


class OrderService:

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    def place_order(self, params: OrderParams) -> OrderResult:
        payload = self._build_payload(params)
        logger.info("Placing %s %s order for %s — qty=%s price=%s",
                    params.order_type, params.side, params.symbol,
                    params.quantity, params.price)

        raw_response = self._client.place_order(payload)
        result = OrderResult.from_response(raw_response)

        logger.info(
            "Order placed — id=%s status=%s executedQty=%s avgPrice=%s",
            result.order_id, result.status, result.executed_qty, result.avg_price,
        )
        return result

    @staticmethod
    def _build_payload(params: OrderParams) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "symbol": params.symbol,
            "side": params.side,
            "type": params.order_type,
            "quantity": params.quantity,
        }

        if params.order_type == "LIMIT":
            payload["price"] = params.price
            payload["timeInForce"] = "GTC"  

        logger.debug("Built payload: %s", payload)
        return payload