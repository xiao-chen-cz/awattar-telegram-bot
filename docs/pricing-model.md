# Pricing Model

How the bot turns the raw Awattar marketdata API into the number you see in
the Telegram message.

The displayed price targets a specific reference customer:

> **Vienna 1220 household** on the **Awattar HOURLY** tariff, supplied via
> **Wiener Netze Netzebene 7 ohne Leistungsmessung** (a standard residential
> smart meter, no demand metering, not in a renewable energy community).

If you're outside Vienna 1220 or on a different network level/tariff, the
commodity part still applies but the grid component needs to be adjusted —
see [§4 Outside Vienna](#4-outside-vienna).

---

## 1. Formula

```
displayed_ct_per_kwh =
    (   EPEX_spot_ct_per_kwh                 # from api.awattar.at
      + 1.50                                  # Awattar HOURLY markup
      + grid_ct_per_kwh(slot_start)           # Wiener Netze NE7, SNAP-aware
    ) × 1.20                                  # 20% Austrian VAT (USt.)
```

where

```
grid_ct_per_kwh(slot_start) =
    6.28   if  4 ≤ month ≤ 9  AND  10 ≤ hour < 16     # SNAP
    7.68   otherwise                                   # normal
```

`slot_start` is always Vienna local time (Europe/Vienna), so DST is handled
automatically by the underlying timezone-aware `datetime`.

---

## 2. Components

### 2.1 EPEX spot (commodity)

Source: `https://api.awattar.at/v1/marketdata` returns `marketprice` in
**EUR/MWh** for each hourly slot. Divide by 10 to get **ct/kWh**.

This is the wholesale day-ahead price for the AT bidding zone. It can be
negative when renewable generation outpaces demand.

### 2.2 Awattar HOURLY markup — **1.50 ct/kWh (net)**

Source:
- [aWATTar HOURLY tariff page](https://www.awattar.at/tariffs/hourly)
- [Support: Wie setzt sich der HOURLY Tarif zusammen?](https://support.awattar.at/de/articles/101-wie-setzt-sich-der-hourly-tarif-zusammen)

The markup is added **before** VAT, so its gross effect is
`1.50 × 1.20 = 1.80 ct/kWh`.

### 2.3 Wiener Netze grid — **7.68 ct/kWh normal, 6.28 ct/kWh SNAP (net)**

Source: Wiener Netze official tariff sheet
[**WN-EX0105 v1/2026**](https://www.wienernetze.at/o/document/wn_ex0105-netznutzungs-und-netzverlustentgelt_2026_geschutzt),
valid from **1 January 2026** under E-Control's Systemnutzungsentgelte-Verordnung
2018 — Novelle 2026.

For Netzebene 7 **ohne Leistungsmessung**:

| Component                       | Normal     | SNAP       |
| ------------------------------- | ---------- | ---------- |
| Netznutzungs-Arbeitspreis       | 6.98 ct/kWh| 5.58 ct/kWh|
| Netzverlustentgelt              | 0.700 ct/kWh| 0.700 ct/kWh|
| **Sum (per-kWh grid, net)**     | **7.68**   | **6.28**   |

#### 2.3.1 The SNAP window

**SNAP** = *Sommer-Nieder-Arbeitspreis* — a time-of-use discount on the
Netznutzungs-Arbeitspreis that nudges consumption into solar-rich daytime
hours.

- **Months:** 1 April – 30 September (inclusive)
- **Hours:** 10:00 – 16:00 Vienna local time, daily
- **Discount:** 5.58 vs 6.98 ct/kWh on the Arbeitspreis component only — i.e.
  **−1.40 ct/kWh net**, or **−1.68 ct/kWh gross** after VAT
- **Eligibility:** smart meter that is electronically read out by the network
  operator (true for virtually all Vienna households post-rollout), and the
  meter is **not** assigned to a renewable energy community (Erneuerbare-
  Energiegemeinschaft)
- The Netzverlustentgelt component does **not** get the SNAP discount

Implementation: `awattar._grid_ct_kwh()` checks
`4 ≤ month ≤ 9 AND 10 ≤ slot.start.hour < 16`. Because Awattar slots are
1-hour windows starting on the hour, `start.hour ∈ {10, 11, 12, 13, 14, 15}`
correctly covers consumption in the 10:00–16:00 window.

### 2.4 VAT — 20%

Austrian *Umsatzsteuer* applies to the full above-the-line sum, including
the commodity markup and grid charges. **It also applies to negative spot
prices**, so a deeply negative wholesale price becomes slightly *more*
negative after VAT, partially offsetting (but not fully cancelling) the
positive grid component.

---

## 3. What is **not** in the displayed number

These are real costs but kept out of the bot for simplicity / accuracy
reasons. Add them yourself if you're trying to reproduce your bill:

| Item                                   | Approx (gross)      | Why excluded |
| -------------------------------------- | ------------------- | ------------ |
| Wiener Netze Grundpreis                | 54 €/year           | Fixed, not per-kWh |
| Awattar HOURLY service fee             | 5.75 €/month        | Fixed, not per-kWh |
| Gebrauchsabgabe Wien                   | ~0.6 ct/kWh         | Flat city tax, changes occasionally — kept off so the bot's per-kWh accuracy claim stays narrow |
| Erneuerbaren-Förderbeitrag + similar   | ~0.9 ct/kWh         | Annual federal levy, changes each year — same reason |

Total uncounted flat per-kWh additions: roughly **1.5 ct/kWh gross**. Add
that to the displayed number for a closer-to-bill estimate.

---

## 4. Outside Vienna

The commodity logic (Awattar HOURLY markup + VAT) is correct for any
Austrian Awattar HOURLY customer. The grid component is **Wiener-Netze-
specific** — other distribution operators (Netz Niederösterreich, Netz OÖ,
Salzburg Netz, etc.) publish their own SNE-V 2026 tariff sheets with
different rates and (often) different SNAP windows.

To adapt: replace `GRID_NORMAL_CT_KWH`, `GRID_SNAP_CT_KWH`, and the SNAP
window logic in `awattar.py` with the values from your operator's 2026
tariff sheet (search for "Netznutzungsentgelt 2026 Preisblatt" + operator
name).

---

## 5. Verification

Deployed 2026-05-13. Compared the live `/heute` output side-by-side against
the pre-deployment version. Expected per-slot delta on a May day (SNAP
season):

```
Δ normal hours  =  (1.50 + 7.68) × 1.20  =  11.016 ct/kWh
Δ SNAP hours    =  (1.50 + 6.28) × 1.20  =   9.336 ct/kWh
```

Observed deltas matched to 0.01 ct/kWh rounding across all 24 slots, with
the SNAP boundary landing exactly at the 10:00 and 16:00 transitions.

---

## 6. Change log

### 2026-05-13 — initial deployment of full-price model

Before this date the bot displayed only `(EPEX spot ÷ 10) × 1.20`, i.e. the
raw wholesale price with VAT — no markup, no grid, no SNAP. The displayed
number was always 10–11 ct/kWh below what a Vienna household actually pays.

Two pull-throughs in this release:

1. **Awattar HOURLY markup** — added `+ 1.50 ct/kWh` pre-VAT
   (commit `a10eaa8`).
2. **Wiener Netze grid + SNAP** — added the grid Arbeitspreis +
   Netzverlustentgelt pre-VAT, with the SNAP discount applied automatically
   for April–September slots 10:00–16:00 local
   (commit `7033cf5`).

Plus README and disclaimer updates so the in-bot footers correctly name the
tariff (`cdb40c7`).
