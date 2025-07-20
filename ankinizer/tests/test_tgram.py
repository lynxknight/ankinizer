import pytest
from unittest.mock import MagicMock, patch, call

from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import CallbackContext

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ankinizer import tgram
from ankinizer import reverso_agent
from ankinizer.tgram import First3, First5

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 123
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.message = MagicMock(spec=Message)
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    return context


@pytest.fixture
def sample_reverso_result():
    return reverso_agent.ReversoResult(
        en_word="test",
        ru_translations=["тест1", "тест2", "тест3", "тест4", "тест5", "тест6"],
        usage_samples=[
            reverso_agent.ReversoTranslationSample(
                en="This is a test",
                ru="Это тест"
            )
        ]
    )


@pytest.mark.asyncio
async def test_accept_both_flow(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_update.message.text = "test"
    mock_context.user_data["reverso_result"] = sample_reverso_result
    
    # Mock Reverso API
    with patch("ankinizer.reverso_agent.get_reverso_result", return_value=sample_reverso_result):
        # Test getting word
        state = await tgram.get_word(mock_update, mock_context)
        assert state == tgram.ACCEPT_OR_DECLINE
        
        # Verify messages were sent
        assert mock_update.message.reply_text.call_count >= 3  # Word, translation, context
        mock_update.message.reply_text.assert_any_call("Word: test")
        mock_update.message.reply_markdown_v2.assert_any_call("Translation: ` тест1, тест2, тест3 (3), тест4, тест5 (5), тест6 `")
        
        # Test accepting both
        mock_update.callback_query.data = tgram.AcceptBoth.key
        with patch("ankinizer.anki_agent.add_card_to_anki") as mock_add_card:
            state = await tgram.accept_or_decline(mock_update, mock_context)
            assert state == tgram.ConversationHandler.END
            mock_add_card.assert_called_once_with(sample_reverso_result)
            mock_update.callback_query.message.reply_text.assert_has_calls([
                call("Adding card to Anki..."),
                call("Card added to Anki")
            ])


@pytest.mark.asyncio
async def test_accept_first_n_flow(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_context.user_data["reverso_result"] = sample_reverso_result

    # Loop through both F3 and F5 cases
    for n, button_key in [(3, First3.key), (5, First5.key)]:
        # Reset the translations for each iteration to ensure the test is clean
        sample_reverso_result.ru_translations = ["тест1", "тест2", "тест3", "тест4", "тест5", "тест6"]
        mock_context.user_data["reverso_result"] = sample_reverso_result

        # Set the callback query data to the button key (F3 or F5)
        mock_update.callback_query.data = button_key
        
        # Patch the anki_agent and call the handler
        with patch("ankinizer.anki_agent.add_card_to_anki") as mock_add_card:
            state = await tgram.accept_or_decline(mock_update, mock_context)
            
            assert state == tgram.ConversationHandler.END
            modified_result = mock_context.user_data["reverso_result"]
            assert len(modified_result.ru_translations) == n
            mock_add_card.assert_called_once_with(modified_result)

@pytest.mark.asyncio
async def test_custom_translation_by_text_input(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_context.user_data["reverso_result"] = sample_reverso_result
    
    # Test requesting custom translation
    mock_update.callback_query.data = tgram.AcceptContextFixTranslation.key
    state = await tgram.accept_or_decline(mock_update, mock_context)
    assert state == tgram.CUSTOM_TRANSLATION
    
    # Test custom translation
    mock_update.callback_query = None
    mock_update.message.text = "проверка"
    state = await tgram.handle_custom_translation(mock_update, mock_context)
    assert state == tgram.ACCEPT_OR_DECLINE
    
    # Verify modified result
    modified_result = mock_context.user_data["reverso_result"]
    assert modified_result.en_word == "test"
    assert modified_result.ru_translations == ["проверка"]
    
    # Test accepting modified result
    mock_update.callback_query = MagicMock(spec=CallbackQuery)
    mock_update.callback_query.message = MagicMock(spec=Message)
    mock_update.callback_query.data = tgram.AcceptBoth.key
    with patch("ankinizer.anki_agent.add_card_to_anki") as mock_add_card:
        state = await tgram.accept_or_decline(mock_update, mock_context)
        assert state == tgram.ConversationHandler.END
        mock_add_card.assert_called_once_with(modified_result)
        mock_update.callback_query.message.reply_text.assert_has_calls([
            call("Adding card to Anki..."),
            call("Card added to Anki")
        ])


@pytest.mark.asyncio
async def test_reject_flow(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_update.message.text = "test"
    mock_context.user_data["reverso_result"] = sample_reverso_result
    
    with patch("ankinizer.reverso_agent.get_reverso_result", return_value=sample_reverso_result):
        # Verify no Anki interaction
        with patch("ankinizer.anki_agent.add_card_to_anki") as mock_add_card:
            state = await tgram.get_word(mock_update, mock_context)
            assert state == tgram.ACCEPT_OR_DECLINE
            # Test rejecting
            mock_update.callback_query.data = tgram.Reject.key
            state = await tgram.accept_or_decline(mock_update, mock_context)
            assert state == tgram.ConversationHandler.END
            mock_add_card.assert_not_called()
