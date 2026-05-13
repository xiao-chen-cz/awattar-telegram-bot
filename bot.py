from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from awattar import PriceSlot, fetch_day, now_vienna, today_vienna
from formatting import format_cheapest, format_day, format_price

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("awattar-bot")

HELP_TEXT = (
    "🔌 <b>Awattar AT Strompreis-Bot</b>\n\n"
    "/preis – aktueller Strompreis\n"
    "/heute – alle Stundenpreise heute\n"
    "/morgen – alle Stundenpreise morgen (ab ca. 14:00 verfügbar)\n"
    "/billig – die 3 günstigsten Stunden heute\n"
    "/tag YYYY-MM-DD – Stundenpreise für einen bestimmten Tag\n"
    "/info – Preiszusammensetzung &amp; Transparenz\n\n"
    "<i>Preise: Awattar HOURLY + Wiener Netze 1220, inkl. 20% USt. "
    "Details mit /info.</i>"
)

INFO_TEXT = (
    "🧮 <b>So setzt sich der Preis zusammen</b>\n\n"
    "<pre>(EPEX-Spot + 1,50 ct/kWh Awattar HOURLY\n"
    "            + Wiener Netze 1220 NE7) × 1,20 USt.</pre>\n"
    "<b>Netzanteil (netto):</b>\n"
    "• Normal: 7,68 ct/kWh (Arbeit 6,98 + Verlust 0,70)\n"
    "• SNAP: 6,28 ct/kWh (1.4.–30.9., täglich 10–16 Uhr)\n"
    "  → 1,68 ct/kWh günstiger pro kWh (brutto)\n\n"
    "<b>Nicht enthalten</b> (flat, einfach drauf rechnen):\n"
    "• 54 €/Jahr Netz-Grundpreis\n"
    "• 5,75 €/Monat Awattar-Servicegebühr\n"
    "• Gebrauchsabgabe Wien + Förderbeiträge (~1,5 ct/kWh)\n\n"
    "<b>Annahme:</b> Awattar HOURLY-Kunde mit Wiener Netze Smart Meter "
    "(Netzebene 7 ohne Leistungsmessung), nicht in einer "
    "Erneuerbare-Energiegemeinschaft.\n\n"
    "<b>Quellen:</b> Awattar HOURLY-Tarif + Wiener Netze WN-EX0105 "
    "v1/2026 (gültig ab 1.1.2026)."
)

API_ERROR = "⚠️ Awattar-API gerade nicht erreichbar. Bitte später erneut versuchen."
TAG_USAGE = "Format: /tag YYYY-MM-DD\nBeispiel: /tag 2026-04-30"
MORGEN_NOT_READY = (
    "📅 Die Preise für morgen werden täglich gegen 14:00 veröffentlicht. "
    "Bitte später erneut versuchen."
)


async def _today_slots() -> list[PriceSlot]:
    return await fetch_day(today_vienna())


async def start_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def info_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(INFO_TEXT, parse_mode=ParseMode.HTML)


async def preis_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        slots = await _today_slots()
    except Exception:
        logger.exception("fetch_day failed for /preis")
        await update.message.reply_text(API_ERROR)
        return

    now = now_vienna()
    current = next((s for s in slots if s.start <= now < s.end), None)
    if current is None:
        await update.message.reply_text(
            "Für die aktuelle Stunde liegt kein Preis vor."
        )
        return
    await update.message.reply_text(format_price(current), parse_mode=ParseMode.HTML)


async def heute_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        slots = await _today_slots()
    except Exception:
        logger.exception("fetch_day failed for /heute")
        await update.message.reply_text(API_ERROR)
        return
    await update.message.reply_text(
        format_day(slots, "heute"), parse_mode=ParseMode.HTML
    )


async def morgen_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    tomorrow = today_vienna() + timedelta(days=1)
    try:
        slots = await fetch_day(tomorrow)
    except Exception:
        logger.exception("fetch_day failed for /morgen")
        await update.message.reply_text(API_ERROR)
        return
    if not slots:
        await update.message.reply_text(MORGEN_NOT_READY)
        return
    await update.message.reply_text(
        format_day(slots, "morgen"), parse_mode=ParseMode.HTML
    )


async def tag_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 1:
        await update.message.reply_text(TAG_USAGE)
        return
    try:
        target = date.fromisoformat(args[0])
    except ValueError:
        await update.message.reply_text(TAG_USAGE)
        return
    try:
        slots = await fetch_day(target)
    except Exception:
        logger.exception("fetch_day failed for /tag %s", target)
        await update.message.reply_text(API_ERROR)
        return
    await update.message.reply_text(
        format_day(slots, f"am {target.isoformat()}"), parse_mode=ParseMode.HTML
    )


async def billig_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        slots = await _today_slots()
    except Exception:
        logger.exception("fetch_day failed for /billig")
        await update.message.reply_text(API_ERROR)
        return
    await update.message.reply_text(
        format_cheapest(slots, n=3), parse_mode=ParseMode.HTML
    )


def main() -> None:
    load_dotenv()
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        sys.exit("TELEGRAM_TOKEN missing. Copy .env.example to .env and set it.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(CommandHandler("preis", preis_cmd))
    app.add_handler(CommandHandler("heute", heute_cmd))
    app.add_handler(CommandHandler("morgen", morgen_cmd))
    app.add_handler(CommandHandler("billig", billig_cmd))
    app.add_handler(CommandHandler("tag", tag_cmd))

    logger.info("Application started — long polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
