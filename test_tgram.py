import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import ankiconnect
import reverso
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import CallbackContext, ConversationHandler

from tgram import (
    get_word,
    handle_accept_both,
    handle_custom_translation,
    accept_or_decline,
    Actions,
    AcceptBoth,
    AcceptContextFixTranslation,
    Reject,
    CUSTOM_TRANSLATION,
)


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
    return reverso.ReversoResult(
        en_word="test",
        ru_translations=["тест"],
        usage_samples=[
            reverso.ReversoTranslationSample(
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
    with patch("reverso.get_reverso_result", return_value=sample_reverso_result):
        # Test getting word
        state = await get_word(mock_update, mock_context)
        assert state == "ACCEPT_OR_DECLINE"
        
        # Verify messages were sent
        assert mock_update.message.reply_text.call_count >= 3  # Word, translation, context
        mock_update.message.reply_text.assert_any_call("Word: test")
        mock_update.message.reply_text.assert_any_call("тест")
        
        # Test accepting both
        mock_update.callback_query.data = AcceptBoth.key
        state = await accept_or_decline(mock_update, mock_context)
        assert state == ConversationHandler.END
        
        # Verify Anki interaction
        with patch("ankiconnect.add_card_to_anki") as mock_add_card:
            await handle_accept_both(mock_update, mock_context)
            mock_add_card.assert_called_once_with(sample_reverso_result, sync=True)


@pytest.mark.asyncio
async def test_custom_translation_flow(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_update.message.text = "тест"
    mock_context.user_data["reverso_result"] = sample_reverso_result
    
    # Test getting word
    with patch("reverso.get_reverso_result", return_value=sample_reverso_result):
        state = await get_word(mock_update, mock_context)
        assert state == "ACCEPT_OR_DECLINE"
        
        # Test requesting custom translation
        mock_update.callback_query.data = AcceptContextFixTranslation.key
        state = await accept_or_decline(mock_update, mock_context)
        assert state == CUSTOM_TRANSLATION
        
        # Test custom translation
        mock_update.message.text = "проверка"
        state = await handle_custom_translation(mock_update, mock_context)
        assert state == "ACCEPT_OR_DECLINE"
        
        # Verify modified result
        modified_result = mock_context.user_data["reverso_result"]
        assert modified_result.en_word == "test"
        assert modified_result.ru_translations == ["проверка"]
        assert modified_result.usage_samples == sample_reverso_result.usage_samples
        
        # Test accepting modified result
        mock_update.callback_query.data = AcceptBoth.key
        state = await accept_or_decline(mock_update, mock_context)
        assert state == ConversationHandler.END
        
        # Verify Anki interaction with modified translation
        with patch("ankiconnect.add_card_to_anki") as mock_add_card:
            await handle_accept_both(mock_update, mock_context)
            mock_add_card.assert_called_once_with(modified_result, sync=True)


@pytest.mark.asyncio
async def test_reject_flow(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_update.message.text = "test"
    mock_context.user_data["reverso_result"] = sample_reverso_result
    
    # Test getting word
    with patch("reverso.get_reverso_result", return_value=sample_reverso_result):
        with patch("ankiconnect.add_card_to_anki") as mock_add_card:
            state = await get_word(mock_update, mock_context)
            assert state == "ACCEPT_OR_DECLINE"
            
            # Test rejecting
            mock_update.callback_query.data = Reject.key
            state = await accept_or_decline(mock_update, mock_context)
            assert state == ConversationHandler.END
            mock_add_card.assert_not_called() 