from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from awattar import PriceSlot, fetch_day, now_vienna, today_vienna
from formatting import format_cheapest, format_price, format_today

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("awattar-bot")

HELP_TEXT = (
    "🔌 <b>Awattar AT Strompreis-Bot</b>\n\n"
    "/preis – aktueller Strompreis\n"
    "/heute – alle Stundenpreise heute\n"
    "/billig – die 3 günstigsten Stunden heute\n\n"
    "<i>Preise = Spotpreis inkl. 20% USt., exkl. Netzentgelte und "
    "Awattar-Servicegebühr.</i>"
)

API_ERROR = "⚠️ Awattar-API gerade nicht erreichbar. Bitte später erneut versuchen."


async def _today_slots() -> list[PriceSlot]:
    return await fetch_day(today_vienna())


async def start_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


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
    await update.message.reply_text(format_today(slots), parse_mode=ParseMode.HTML)


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
    app.add_handler(CommandHandler("preis", preis_cmd))
    app.add_handler(CommandHandler("heute", heute_cmd))
    app.add_handler(CommandHandler("billig", billig_cmd))

    logger.info("Application started — long polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
