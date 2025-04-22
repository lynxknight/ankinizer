import dataclasses
import logging
import os
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

from ankinizer import anki_agent
from ankinizer import reverso_agent
from ankinizer import env

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for the conversation
WORD, CUSTOM_TRANSLATION, ACCEPT_OR_DECLINE = range(3)

# Store user data
user_data = {}

ACCEPT_OR_DECLINE = "ACCEPT_OR_DECLINE"


class AcceptBoth:
    text = "OK"
    key = "accept_both"


class AcceptContextFixTranslation:
    text = "Fix TL"
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
    reverso_result: reverso_agent.ReversoResult


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send me a word.")
    return WORD


async def get_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    word = update.message.text
    word = word.strip().lower()
    await update.message.reply_text(f"{word=} received, getting translation...")
    results = await reverso_agent.get_reverso_result(word)
    await update.message.reply_text(f"Word: {results.en_word}")
    translation = ", ".join(results.ru_translations)
    await update.message.reply_markdown_v2(f"Translation: ` {translation} `")
    logger.info(results.get_usage_samples_html())
    await update.message.reply_html(results.get_usage_samples_html())
    context.user_data["reverso_result"] = results
    keyboard = [
        [InlineKeyboardButton(a.text, callback_data=a.key) for a in Actions.get_all()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Add to anki?", reply_markup=reply_markup)
    return ACCEPT_OR_DECLINE


async def handle_accept_both(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the case when user accepts both translation and context.
    
    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    query = update.callback_query
    reverso_results = context.user_data["reverso_result"]
    try:
        await anki_agent.add_card_to_anki(reverso_results)
    except Exception as e:
        logging.exception(e)
        await query.message.reply_text(f"Error adding card to Anki: {str(e)}")


async def accept_or_decline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    answer = query.data
    reverso_results = context.user_data["reverso_result"]
    await query.edit_message_text(text=Actions.get_key_to_text_map()[answer])
    if answer == Reject.key:
        pass
    elif answer == AcceptBoth.key:
        await query.message.reply_text("Adding card to Anki...")
        await handle_accept_both(update, context)
        await query.message.reply_text("Card added to Anki")
    elif answer == AcceptContextFixTranslation.key:
        await query.message.reply_text("Please enter your custom translation:")
        return CUSTOM_TRANSLATION
    return ConversationHandler.END


async def handle_custom_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    custom_translation = update.message.text
    reverso_results = context.user_data["reverso_result"]
    # Create a new ReversoResult with the custom translation
    modified_results = reverso_agent.ReversoResult(
        en_word=reverso_results.en_word,
        ru_translations=[custom_translation],  # Replace with user's translation
        usage_samples=reverso_results.usage_samples  # Keep original context
    )
    context.user_data["reverso_result"] = modified_results
    
    # Show the modified result and prompt for acceptance
    await update.message.reply_text(f"Word: {modified_results.en_word}")
    await update.message.reply_markdown_v2(f"Translation: ` {custom_translation} `")
    await update.message.reply_html(modified_results.get_usage_samples_html())
    
    keyboard = [
        [InlineKeyboardButton(a.text, callback_data=a.key) for a in Actions.get_all()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Add to anki?", reply_markup=reply_markup)
    return ACCEPT_OR_DECLINE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


async def handle_text_during_accept_or_decline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text input during ACCEPT_OR_DECLINE state by treating it as a rejection."""
    await update.message.reply_text("Text input during selection is treated as rejection.")
    return ConversationHandler.END


def main() -> None:
    env.setup_env()

    # Build and run the application
    application = (
        ApplicationBuilder()
        .token(os.environ["TELEGRAM_BOT_TOKEN"])
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, get_word)],
        states={
            ACCEPT_OR_DECLINE: [
                CallbackQueryHandler(accept_or_decline),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_during_accept_or_decline)
            ],
            CUSTOM_TRANSLATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_translation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main() 