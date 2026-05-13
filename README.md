# Awattar AT Telegram Bot

A small Telegram bot that exposes Austrian day-ahead electricity prices from the
[Awattar AT marketdata API](https://api.awattar.at/v1/marketdata).

## Commands

| Command            | Description                                          |
| ------------------ | ---------------------------------------------------- |
| `/preis`           | Current hour's price (gross, ct/kWh)                 |
| `/heute`           | All 24 hourly prices for today                       |
| `/morgen`          | Tomorrow's hourly prices (published ~14:00 Vienna)   |
| `/billig`          | The 3 cheapest hours of today                        |
| `/tag YYYY-MM-DD`  | Hourly prices for a specific day (past or future)    |
| `/help`            | Command list and pricing notes                       |

Prices shown reflect what a **Vienna household on Awattar HOURLY** actually
pays per kWh:

```
( EPEX spot  +  1.50 ct/kWh Awattar markup
              +  Wiener Netze NE7 grid (Arbeitspreis + Verlust) )  ×  1.20 VAT
```

The Wiener Netze **Sommer-Nieder-Arbeitspreis (SNAP)** is applied
automatically for slots between **10:00–16:00 local from 1 April to 30
September**, so the dynamic grid discount is visible in the daily curve.

**Not included** (flat / monthly, so easy to add on the side):

- 54 €/year network Grundpreis
- 5.75 €/month Awattar service fee
- Vienna Gebrauchsabgabe + Erneuerbaren-Förderbeiträge (~1.5 ct/kWh)

Customers outside Vienna 1220 or on a different network level should treat
the displayed values as Vienna-specific — the grid constants in
`awattar.py` would need to be adjusted for other operators.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# paste the token from @BotFather into .env
```

## Run

```bash
python bot.py
```

The bot uses long polling — no public URL or webhook needed.

## Deploy

Any host that can run a long-lived Python process works (Fly.io, Railway,
Hetzner, a Raspberry Pi, etc.). Provide `TELEGRAM_TOKEN` as an environment
variable; `.env` is loaded automatically when present.

Minimum requirements:

- Python 3.9+
- Outbound HTTPS to `api.telegram.org` and `api.awattar.at`

### Coolify (Dockerfile)

The repo ships a `Dockerfile` so Coolify can build and run it directly:

1. **New Resource → Application → Public Repository**, paste this repo's URL.
2. **Build Pack:** Dockerfile.
3. **Environment Variables:** add `TELEGRAM_TOKEN`.
4. **Network / Ports:** leave empty — this is a worker, not an HTTP service. Disable the health check.
5. Deploy. Logs should show `Application started — long polling`.

Stop any local instance before deploying: Telegram allows only one long-polling consumer per token, and a second instance causes 409 conflicts.

#### Why Dockerfile, not docker-compose

Single-process worker, one env var, no database — `docker-compose.yml` would be pure boilerplate here. Coolify manages restarts, env vars, and logs from the UI, so the compose layer adds no value at this size. If we ever add a second service (cache, scheduler, second bot), switch to compose at that point — the Dockerfile carries over unchanged.

### systemd example

```ini
[Service]
WorkingDirectory=/opt/awattar-bot
EnvironmentFile=/opt/awattar-bot/.env
ExecStart=/opt/awattar-bot/.venv/bin/python bot.py
Restart=on-failure
```

## Project layout

- `bot.py` — Telegram handlers + polling loop
- `awattar.py` — API client + price assembly (commodity + grid + VAT, SNAP-aware)
- `formatting.py` — message formatters
