import asyncio
import logging
import re

import ankiconnect
import reverso

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send me a word.")
    return WORD


async def get_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    word = update.message.text
    logger.info(f"BEFORE TO THREAD")
    results = await asyncio.to_thread(reverso.get_reverso_result, word)
    logger.info(f"AFTER TO THREAD")
    await update.message.reply_text(f"Word: {results.en_word}")
    await update.message.reply_text(", ".join(results.ru_translations))
    logger.info(results.get_usage_samples_html())
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data='yes')],
        [InlineKeyboardButton("No", callback_data='no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(results.get_usage_samples_html(), reply_markup=reply_markup)
    return ACCEPT_OR_DECLINE


async def accept_or_decline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    query.answer()
    answer = query.data
    if answer == 'yes':
        query.edit_message_text(text='You selected yes!')
    elif answer == 'no':
        query.edit_message_text(text='You selected no!')


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
            ACCEPT_OR_DECLINE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, accept_or_decline)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
