import pytest
from unittest.mock import MagicMock, patch

from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import CallbackContext

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ankinizer import tgram
from ankinizer import reverso_agent

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
        ru_translations=["тест"],
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
        mock_update.message.reply_markdown_v2.assert_any_call("Translation: ` тест `")
        
        # Test accepting both
        mock_update.callback_query.data = tgram.AcceptBoth.key
        state = await tgram.accept_or_decline(mock_update, mock_context)
        assert state == tgram.ConversationHandler.END
        
        # Verify Anki interaction
        with patch("ankinizer.anki_agent.add_card_to_anki") as mock_add_card:
            await tgram.handle_accept_both(mock_update, mock_context)
            mock_add_card.assert_called_once_with(sample_reverso_result)


@pytest.mark.asyncio
async def test_custom_translation_flow(mock_update, mock_context, sample_reverso_result):
    # Setup
    mock_update.message.text = "тест"
    mock_context.user_data["reverso_result"] = sample_reverso_result
    
    # Test getting word
    with patch("ankinizer.reverso_agent.get_reverso_result", return_value=sample_reverso_result):
        state = await tgram.get_word(mock_update, mock_context)
        assert state == tgram.ACCEPT_OR_DECLINE
        
        # Test requesting custom translation
        mock_update.callback_query.data = tgram.AcceptContextFixTranslation.key
        state = await tgram.accept_or_decline(mock_update, mock_context)
        assert state == tgram.CUSTOM_TRANSLATION
        
        # Test custom translation
        mock_update.message.text = "проверка"
        state = await tgram.handle_custom_translation(mock_update, mock_context)
        assert state == tgram.ACCEPT_OR_DECLINE
        
        # Verify modified result
        modified_result = mock_context.user_data["reverso_result"]
        assert modified_result.en_word == "test"
        assert modified_result.ru_translations == ["проверка"]
        assert modified_result.usage_samples == sample_reverso_result.usage_samples
        
        # Test accepting modified result
        mock_update.callback_query.data = tgram.AcceptBoth.key
        state = await tgram.accept_or_decline(mock_update, mock_context)
        assert state == tgram.ConversationHandler.END
        
        # Verify Anki interaction with modified translation
        with patch("ankinizer.anki_agent.add_card_to_anki") as mock_add_card:
            await tgram.handle_accept_both(mock_update, mock_context)
            mock_add_card.assert_called_once_with(modified_result)


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


@pytest.mark.asyncio
async def test_translation_display_flow(mock_update, mock_context):
    # Test case 1: More than 5 translations
    translations_5plus = ["кот", "кошка", "котенок", "котик", "котом", "котом"]
    result_5plus = reverso_agent.ReversoResult(
        en_word="cat",
        ru_translations=translations_5plus,
        usage_samples=[]
    )
    mock_context.user_data["reverso_result"] = result_5plus
    mock_update.callback_query.data = tgram.AcceptContextFixTranslation.key
    
    state = await tgram.accept_or_decline(mock_update, mock_context)
    assert state == tgram.CUSTOM_TRANSLATION
    
    # Verify both messages were sent
    mock_update.callback_query.message.reply_markdown_v2.assert_any_call(
        "First 3 translations: `кот, кошка, котенок`"
    )
    mock_update.callback_query.message.reply_markdown_v2.assert_any_call(
        "First 5 translations: `кот, кошка, котенок, котик, котом`"
    )
    
    # Test case 2: Exactly 4 translations
    translations_4 = ["кот", "кошка", "котенок", "котик"]
    result_4 = reverso_agent.ReversoResult(
        en_word="cat",
        ru_translations=translations_4,
        usage_samples=[]
    )
    mock_context.user_data["reverso_result"] = result_4
    mock_update.callback_query.message.reset_mock()
    
    state = await tgram.accept_or_decline(mock_update, mock_context)
    assert state == tgram.CUSTOM_TRANSLATION
    
    # Verify only first 3 message was sent
    mock_update.callback_query.message.reply_markdown_v2.assert_called_once_with(
        "First 3 translations: `кот, кошка, котенок`"
    )
    
    # Test case 3: Less than 3 translations
    translations_2 = ["кот", "кошка"]
    result_2 = reverso_agent.ReversoResult(
        en_word="cat",
        ru_translations=translations_2,
        usage_samples=[]
    )
    mock_context.user_data["reverso_result"] = result_2
    mock_update.callback_query.message.reset_mock()
    
    state = await tgram.accept_or_decline(mock_update, mock_context)
    assert state == tgram.CUSTOM_TRANSLATION
    
    # Verify no translation messages were sent
    mock_update.callback_query.message.reply_markdown_v2.assert_not_called()
    
    # Verify custom translation prompt was sent in all cases
    mock_update.callback_query.message.reply_text.assert_called_with(
        "Please enter your custom translation:"
    ) 