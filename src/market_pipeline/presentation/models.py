from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class LatestOfferReportRow:
    product_title: str
    store_name: str
    price: Decimal
    currency: str
    observed_at: datetime
