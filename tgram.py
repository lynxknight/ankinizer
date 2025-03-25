import asyncio
import dataclasses
import logging

import ankiconnect
import reverso

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    MessageHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for the conversation
WORD, EDIT_NUMBERS = range(2)

# Store user data
user_data = {}

ACCEPT_OR_DECLINE = "ACCEPT_OR_DECLINE"


class AcceptBoth:
    text = "Accept both"
    key = "accept_both"


class AcceptContextFixTranslation:
    text = "Accept context, fix translation"
    key = "accept_context_fix_translation"


class Reject:
    text = "Reject"
    key = "reject"


class Actions:
    @staticmethod
    def get_all():
        return [AcceptBoth, AcceptContextFixTranslation, Reject]

    @staticmethod
    def get_key_to_text_map():
        return {a.key: a.text for a in Actions.get_all()}


@dataclasses.dataclass
class CallbackData:
    action_key: str
    reverso_result: reverso.ReversoResult


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send me a word.")
    return WORD


async def get_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    word = update.message.text
    results = await asyncio.to_thread(reverso.get_reverso_result, word)
    await update.message.reply_text(f"Word: {results.en_word}")
    await update.message.reply_text(", ".join(results.ru_translations))
    logger.info(results.get_usage_samples_html())
    await update.message.reply_html(results.get_usage_samples_html())
    context.user_data["reverso_result"] = results
    keyboard = [
        [InlineKeyboardButton(a.text, callback_data=a.key) for a in Actions.get_all()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Add to anki?", reply_markup=reply_markup)
    return ACCEPT_OR_DECLINE


async def accept_or_decline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    answer = query.data
    reverso_results = context.user_data["reverso_result"]
    await query.edit_message_text(text=Actions.get_key_to_text_map()[answer])
    if answer == Reject.key:
        pass
    elif answer == AcceptBoth.key:
        try:
            await query.message.reply_text("Adding to anki...")
            await asyncio.to_thread(
                ankiconnect.add_card_to_anki, reverso_results, sync=True
            )
            await query.message.reply_text("Added to anki and synced")
        except Exception as e:
            logging.exception(e)
            await query.message.reply_text("Something went wrong")
    elif answer == AcceptContextFixTranslation.key:
        await query.edit_message_text(ac)
        await query.message.reply_text("Not implemented yet")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def main() -> None:
    # TODO: conversation handler that accepts yes or no and on "yes" uploads to anki
    application = (
        ApplicationBuilder()
        .token("513477620:AAEh-LVlFF_5d0q-IeG2lLCkQCIWk-mrp0s")
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, get_word)],
        states={
            ACCEPT_OR_DECLINE: [CallbackQueryHandler(accept_or_decline)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
