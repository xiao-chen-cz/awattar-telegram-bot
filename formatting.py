from __future__ import annotations

from datetime import datetime

from awattar import PriceSlot

VAT_NOTE = "Energie + Netz Wien, inkl. 20% USt."


def _hh(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _range(slot: PriceSlot) -> str:
    return f"{_hh(slot.start)}–{_hh(slot.end)}"


def format_price(slot: PriceSlot) -> str:
    return (
        f"⚡ Aktueller Strompreis: <b>{slot.price_ct_kwh:.2f} ct/kWh</b>\n"
        f"({_range(slot)}, {VAT_NOTE})"
    )


def format_day(slots: list[PriceSlot], label: str) -> str:
    if not slots:
        return f"Keine Preisdaten für {label} verfügbar."

    lines = [f"{_range(s):<11}  {s.price_ct_kwh:>6.2f} ct/kWh" for s in slots]
    table = "\n".join(lines)
    header = f"<b>Strompreise {label}</b> ({VAT_NOTE})"
    return f"{header}\n<pre>{table}</pre>"


def format_cheapest(slots: list[PriceSlot], n: int = 3) -> str:
    if not slots:
        return "Keine Preisdaten für heute verfügbar."

    cheapest = sorted(slots, key=lambda s: s.price_ct_kwh)[:n]
    lines = [
        f"• {_range(s)}: <b>{s.price_ct_kwh:.2f} ct/kWh</b>" for s in cheapest
    ]
    body = "\n".join(lines)
    return f"💰 <b>{n} günstigste Stunden heute</b> ({VAT_NOTE})\n{body}"
