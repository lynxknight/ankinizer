import dataclasses
import logging
import os
from typing import Dict, Any, cast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message, CallbackQuery
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
user_data: Dict[str, Any] = {}


class AcceptBoth:
    text = "OK"
    key = "accept_both"


class AcceptContextFixTranslation:
    text = "Custom"
    key = "accept_context_fix_translation"


class Reject:
    text = "Reject"
    key = "reject"


class First3:
    text = "F3"
    key = "accept_first_3"
    n = 3


class First5:
    text = "F5"
    key = "accept_first_5"
    n = 5


class Actions:
    @staticmethod
    def get_all():
        return [AcceptBoth, First3, First5, AcceptContextFixTranslation, Reject]

    @staticmethod
    def get_base_actions():
        return [AcceptBoth, AcceptContextFixTranslation, Reject]

    @staticmethod
    def get_key_to_text_map():
        return {a.key: a.text for a in Actions.get_all()}


@dataclasses.dataclass
class CallbackData:
    action_key: str
    reverso_result: reverso_agent.ReversoResult


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END
    await update.message.reply_text("Please send me a word.")
    return WORD

def format_ru_translations(ru_translations):
    for v in (3, 5):
        if len(ru_translations) >= v:
            ru_translations[v - 1] += f" ({v})" 
    return ru_translations



async def get_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None or update.message.text is None:
        return ConversationHandler.END
    
    word = update.message.text.strip().lower()
    await update.message.reply_text(f"{word=} received, getting translation...")
    results = await reverso_agent.get_reverso_result(word)
    await update.message.reply_text(f"Word: {results.en_word}")


    if context.user_data is None:
        context.user_data = {}
    context.user_data["reverso_result"] = results

    display_ru_translations = list(results.ru_translations)
    translation = ", ".join(format_ru_translations(display_ru_translations))
    await update.message.reply_markdown_v2(f"Translation: ` {translation} `")
    logger.info(results.get_usage_samples_html())
    await update.message.reply_html(results.get_usage_samples_html())
    
    keyboard = [
        [InlineKeyboardButton(a.text, callback_data=a.key) for a in Actions.get_all()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Add to anki?", reply_markup=reply_markup)
    return ACCEPT_OR_DECLINE


async def handle_add_to_anki(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the case when user accepts both translation and context."""
    if update.callback_query is None or update.callback_query.message is None or context.user_data is None:
        return
    
    query = update.callback_query
    reverso_results = context.user_data.get("reverso_result")
    if not isinstance(reverso_results, reverso_agent.ReversoResult):
        await query.message.reply_text("Error: Invalid reverso result")
        return
        
    await query.message.reply_text("Adding card to Anki...")
    try:
        await anki_agent.add_card_to_anki(reverso_results)
        await query.message.reply_text("Card added to Anki")
    except Exception as e:
        logging.exception(e)
        await query.message.reply_text(f"Error adding card to Anki: {str(e)}")


async def accept_or_decline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query is None or context.user_data is None:
        return ConversationHandler.END
    
    query = update.callback_query
    if query.data is None:
        return ConversationHandler.END
        
    answer = query.data
    reverso_results = context.user_data.get("reverso_result")
    if not isinstance(reverso_results, reverso_agent.ReversoResult):
        if query.message is not None:
            await query.message.reply_text("Error: Invalid reverso result")
        return ConversationHandler.END
        
    if query.message is None:
        return ConversationHandler.END
        
    await query.edit_message_text(text=Actions.get_key_to_text_map()[answer])
    if answer == Reject.key:
        pass
    elif answer == AcceptBoth.key:
        await handle_add_to_anki(update, context)
    elif answer == AcceptContextFixTranslation.key:
        await query.message.reply_text("Enter custom translation:")
        return CUSTOM_TRANSLATION
    elif answer == First3.key:
        return await handle_first_n_translations(update, context, First3.n)
    elif answer == First5.key:
        return await handle_first_n_translations(update, context, First5.n)
    return ConversationHandler.END


async def handle_first_n_translations(update: Update, context: ContextTypes.DEFAULT_TYPE, n: int) -> int:
    """Handle accepting first N translations."""
    if (
        update.callback_query is None
        or update.callback_query.message is None
        or context.user_data is None
        or not isinstance(context.user_data.get("reverso_result"), reverso_agent.ReversoResult)
    ):
        return ConversationHandler.END

    reverso_results = cast(reverso_agent.ReversoResult, context.user_data.get("reverso_result"))
    reverso_results.ru_translations = reverso_results.ru_translations[:n]
    await handle_add_to_anki(update, context)
    return ConversationHandler.END


async def handle_custom_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is not None and update.message.text is not None:
        # Handle manual text input
        custom_translation = update.message.text
        reverso_results = context.user_data.get("reverso_result")
        if not isinstance(reverso_results, reverso_agent.ReversoResult):
            await update.message.reply_text("Error: Invalid reverso result")
            return ConversationHandler.END
            
        # Create a new ReversoResult with the custom translation
        modified_results = reverso_agent.ReversoResult(
            en_word=reverso_results.en_word,
            ru_translations=[custom_translation],  # Replace with user's translation
            usage_samples=reverso_results.usage_samples  # Keep original context
        )
        context.user_data["reverso_result"] = modified_results
        
        # Show the modified result and prompt for acceptance
        await update.message.reply_text(f"Word: {modified_results.en_word}")
        await update.message.reply_markdown_v2(f"Translation: `{custom_translation}`")
        await update.message.reply_html(modified_results.get_usage_samples_html())
        
        keyboard = [
            [InlineKeyboardButton(a.text, callback_data=a.key) for a in Actions.get_base_actions()]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Add to anki?", reply_markup=reply_markup)
        return ACCEPT_OR_DECLINE
    
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text("Operation cancelled due to unexpected button press.")
    return ConversationHandler.END



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


async def handle_text_during_accept_or_decline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text input during ACCEPT_OR_DECLINE state by treating it as a rejection."""
    if update.message is None:
        return ConversationHandler.END
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
            CUSTOM_TRANSLATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_translation)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()