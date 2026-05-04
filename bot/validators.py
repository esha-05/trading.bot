from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bot.logging_config import get_logger

logger = get_logger(__name__)

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}
MIN_NOTIONAL = 5.0



@dataclass
class OrderParams:
    """Validated and normalised order parameters ready for the API layer."""

    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None


class ValidationError(ValueError):
    """Raised when any input parameter fails validation."""

def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
) -> OrderParams:
    """
    Validate all order parameters and return a clean OrderParams object.

    Raises:
        ValidationError: With a descriptive message on the first failure found.
    """
    logger.debug(
        "Validating inputs — symbol=%s side=%s type=%s qty=%s price=%s",
        symbol, side, order_type, quantity, price,
    )

    symbol = _validate_symbol(symbol)
    side = _validate_side(side)
    order_type = _validate_order_type(order_type)
    quantity = _validate_quantity(quantity)
    price = _validate_price(order_type, price)
    _validate_notional(quantity, price, order_type)

    params = OrderParams(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
    )
    logger.info("Input validation passed: %s", params)
    return params


def _validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValidationError("Symbol must not be empty.")
    if not symbol.isalnum():
        raise ValidationError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Use alphanumeric characters only (e.g. BTCUSDT)."
        )
    return symbol


def _validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def _validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def _validate_quantity(quantity: float) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity '{quantity}' is not a valid number.")
    if quantity <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got {quantity}.")
    return quantity


def _validate_price(order_type: str, price: Optional[float]) -> Optional[float]:
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price '{price}' is not a valid number.")
        if price <= 0:
            raise ValidationError(f"Price must be greater than zero, got {price}.")
        return price

    if price is not None:
        logger.warning(
            "Price=%s was supplied for a MARKET order and will be ignored.", price
        )
    return None


def _validate_notional(
    quantity: float, price: Optional[float], order_type: str
) -> None:
    """Warn (not error) when estimated notional is below the exchange minimum."""
    if order_type == "LIMIT" and price is not None:
        notional = quantity * price
        if notional < MIN_NOTIONAL:
            raise ValidationError(
                f"Estimated notional value ${notional:.2f} is below the minimum "
                f"${MIN_NOTIONAL:.2f} required by Binance Futures."
            )