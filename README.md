# Awattar AT Telegram Bot

A small Telegram bot that exposes Austrian day-ahead electricity prices from the
[Awattar AT marketdata API](https://api.awattar.at/v1/marketdata).

## Commands

| Command   | Description                                  |
| --------- | -------------------------------------------- |
| `/preis`  | Current hour's price (gross, ct/kWh)         |
| `/heute`  | All 24 hourly prices for today               |
| `/billig` | The 3 cheapest hours of today                |
| `/help`   | Command list and pricing notes               |

Prices shown are the **spot price including 20% Austrian VAT (USt.)**. Grid
fees and the Awattar service fee are **not** included.

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
- `awattar.py` — API client + unit conversion (EUR/MWh → ct/kWh, +20% VAT)
- `formatting.py` — message formatters
