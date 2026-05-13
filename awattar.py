from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

VIENNA = ZoneInfo("Europe/Vienna")
API_URL = "https://api.awattar.at/v1/marketdata"
# HOURLY tariff: (EPEX spot + 1.50 ct/kWh markup) × 1.20 VAT.
# Grid fees and the €5.75/month service fee are billed separately.
HOURLY_MARKUP_CT_KWH = 1.50
VAT_MULTIPLIER = 1.20


@dataclass(frozen=True)
class PriceSlot:
    start: datetime
    end: datetime
    price_ct_kwh: float


def _to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _from_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=VIENNA)


async def fetch_day(target_date: date) -> list[PriceSlot]:
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=VIENNA)
    end = start + timedelta(days=1)

    params = {"start": _to_ms(start), "end": _to_ms(end)}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(API_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    slots = []
    for entry in payload.get("data", []):
        slots.append(
            PriceSlot(
                start=_from_ms(entry["start_timestamp"]),
                end=_from_ms(entry["end_timestamp"]),
                price_ct_kwh=(entry["marketprice"] / 10 + HOURLY_MARKUP_CT_KWH)
                * VAT_MULTIPLIER,
            )
        )
    slots.sort(key=lambda s: s.start)
    return slots


def now_vienna() -> datetime:
    return datetime.now(tz=VIENNA)


def today_vienna() -> date:
    return now_vienna().date()
