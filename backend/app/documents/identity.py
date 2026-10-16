"""E03: immutable quote content and its equivalence identity.

The caller must provide every input used to calculate the quoted price in
``price_values``. Adapting the shared A02 contract to this shape is separate
from defining the identity itself.
"""

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
from typing import Mapping

from .composition import GroupSchedule, QuotePdfSnapshot


@dataclass(frozen=True)
class VisibleQuote:
    """A copy of every customer-facing field rendered by E01."""

    company: str
    client: str
    service_address: str
    scope: str
    period: str
    groups: tuple[GroupSchedule, ...]
    subtotal: Decimal
    tax: Decimal
    total: Decimal

    @classmethod
    def from_pdf_snapshot(cls, quote: QuotePdfSnapshot) -> "VisibleQuote":
        return cls(
            company=quote.company,
            client=quote.client,
            service_address=quote.service_address,
            scope=quote.scope,
            period=quote.period,
            groups=tuple(quote.groups),
            subtotal=quote.subtotal,
            tax=quote.tax,
            total=quote.total,
        )

    def to_pdf_snapshot(self) -> QuotePdfSnapshot:
        """Pass only customer-facing values to the PDF composer."""
        return QuotePdfSnapshot(
            company=self.company,
            client=self.client,
            service_address=self.service_address,
            scope=self.scope,
            period=self.period,
            groups=self.groups,
            subtotal=self.subtotal,
            tax=self.tax,
            total=self.total,
        )


def _decimal_text(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("Los valores de precio deben ser Decimal")
    if not value.is_finite():
        raise ValueError("Los valores de precio deben ser finitos")
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class VersionSnapshot:
    """Content and version metadata; metadata does not affect identity."""

    visible: VisibleQuote
    price_values: tuple[tuple[str, Decimal], ...]
    code: str
    issued_at: date

    @classmethod
    def from_quote_pdf(
        cls,
        quote: QuotePdfSnapshot,
        price_values: Mapping[str, Decimal],
        *,
        code: str,
        issued_at: date,
    ) -> "VersionSnapshot":
        copied_prices = tuple(sorted(price_values.items()))
        for key, value in copied_prices:
            if not isinstance(key, str) or not key:
                raise ValueError("Cada valor de precio requiere una clave")
            _decimal_text(value)
        return cls(
            visible=VisibleQuote.from_pdf_snapshot(quote),
            price_values=copied_prices,
            code=code,
            issued_at=issued_at,
        )

    @property
    def identity(self) -> str:
        """Stable SHA-256 of visible content and price inputs (RF-34)."""
        payload = {
            "schema": 1,
            "visible": asdict(self.visible),
            "price_values": self.price_values,
        }
        canonical = json.dumps(
            payload,
            default=_decimal_text,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(canonical).hexdigest()
