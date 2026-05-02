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
