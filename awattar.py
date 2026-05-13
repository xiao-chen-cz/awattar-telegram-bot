from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

VIENNA = ZoneInfo("Europe/Vienna")
API_URL = "https://api.awattar.at/v1/marketdata"
# Awattar HOURLY: EPEX spot + 1.50 ct/kWh; €5.75/month service fee separate.
HOURLY_MARKUP_CT_KWH = 1.50
# Wiener Netze 2026, Netzebene 7 ohne Leistungsmessung (residential smart meter):
# Netznutzungs-Arbeitspreis 6.98 ct/kWh (5.58 during SNAP) + Netzverlustentgelt
# 0.700 ct/kWh. The 54 €/year Grundpreis is billed separately.
# SNAP = Sommer-Nieder-Arbeitspreis, 1 Apr – 30 Sep, daily 10:00–16:00 local.
GRID_NORMAL_CT_KWH = 6.98 + 0.700
GRID_SNAP_CT_KWH = 5.58 + 0.700
VAT_MULTIPLIER = 1.20


def _grid_ct_kwh(slot_start: datetime) -> float:
    if 4 <= slot_start.month <= 9 and 10 <= slot_start.hour < 16:
        return GRID_SNAP_CT_KWH
    return GRID_NORMAL_CT_KWH


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
        start = _from_ms(entry["start_timestamp"])
        commodity = entry["marketprice"] / 10 + HOURLY_MARKUP_CT_KWH
        total = (commodity + _grid_ct_kwh(start)) * VAT_MULTIPLIER
        slots.append(
            PriceSlot(
                start=start,
                end=_from_ms(entry["end_timestamp"]),
                price_ct_kwh=total,
            )
        )
    slots.sort(key=lambda s: s.start)
    return slots


def now_vienna() -> datetime:
    return datetime.now(tz=VIENNA)


def today_vienna() -> date:
    return now_vienna().date()
