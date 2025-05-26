import pytest
from ankinizer.anki_agent import format_front_html, format_back_html
from ankinizer.reverso_agent import ReversoResult, ReversoTranslationSample

def test_format_front_html():
    # Test with a simple case
    result = ReversoResult(
        en_word="test",
        ru_translations=["тест"],
        usage_samples=[
            ReversoTranslationSample(
                en="This is a <b>test</b> sentence.",
                ru="Это тестовое предложение."
            ),
            ReversoTranslationSample(
                en="Another <b>test</b> example.",
                ru="Другой пример теста."
            )
        ]
    )
    expected = (
        "test"
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join([
            "This is a <b>test</b> sentence.",
            "Another <b>test</b> example."
        ])
    )
    assert format_front_html(result) == expected

    # Test with special characters
    result = ReversoResult(
        en_word="test'word",
        ru_translations=["тест'слово"],
        usage_samples=[
            ReversoTranslationSample(
                en="This is a <b>test'word</b> with 'quotes'.",
                ru="Это тест'слово с 'кавычками'."
            ),
            ReversoTranslationSample(
                en="Another <b>test'word</b> example.",
                ru="Другой пример тест'слова."
            )
        ]
    )
    expected = (
        "test'word"
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join([
            "This is a <b>test'word</b> with 'quotes'.",
            "Another <b>test'word</b> example."
        ])
    )
    assert format_front_html(result) == expected

def test_format_back_html():
    # Test with a simple case
    result = ReversoResult(
        en_word="test",
        ru_translations=["тест", "проверка"],
        usage_samples=[
            ReversoTranslationSample(
                en="This is a <b>test</b> sentence.",
                ru="Это тестовое предложение."
            ),
            ReversoTranslationSample(
                en="Another <b>test</b> example.",
                ru="Другой пример теста."
            )
        ]
    )
    expected = (
        "тест / проверка"
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join([
            "This is a <b>test</b> sentence. -> Это тестовое предложение.",
            "Another <b>test</b> example. -> Другой пример теста."
        ])
    )
    assert format_back_html(result) == expected

    # Test with special characters
    result = ReversoResult(
        en_word="test'word",
        ru_translations=["тест'слово", "проверка'слова"],
        usage_samples=[
            ReversoTranslationSample(
                en="This is a <b>test'word</b> with 'quotes'.",
                ru="Это тест'слово с 'кавычками'."
            ),
            ReversoTranslationSample(
                en="Another <b>test'word</b> example.",
                ru="Другой пример тест'слова."
            )
        ]
    )
    expected = (
        "тест'слово / проверка'слова"
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join([
            "This is a <b>test'word</b> with 'quotes'. -> Это тест'слово с 'кавычками'.",
            "Another <b>test'word</b> example. -> Другой пример тест'слова."
        ])
    )
    assert format_back_html(result) == expected

def test_format_html_integration():
    # Test both front and back formatting together
    result = ReversoResult(
        en_word="serendipity",
        ru_translations=["серендипность", "интуитивная прозорливость"],
        usage_samples=[
            ReversoTranslationSample(
                en="Process art in its employment of <b>serendipity</b> has a marked correspondence with Dada.",
                ru="Процесс-арт в его отношении к <b>серендипности</b> имеет ярко выраженные пересечения с дадаизмом."
            ),
            ReversoTranslationSample(
                en="I wish I knew what he meant by \"<b>serendipity</b>\".",
                ru="Хотелось бы мне знать, что он имел в виду под \"<b>интуитивной прозорливостью</b>\"."
            )
        ]
    )
    
    # Test front formatting
    front_expected = (
        "serendipity"
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join([
            "Process art in its employment of <b>serendipity</b> has a marked correspondence with Dada.",
            "I wish I knew what he meant by \"<b>serendipity</b>\"."
        ])
    )
    assert format_front_html(result) == front_expected
    
    # Test back formatting
    back_expected = (
        "серендипность / интуитивная прозорливость"
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join([
            "Process art in its employment of <b>serendipity</b> has a marked correspondence with Dada. -> Процесс-арт в его отношении к <b>серендипности</b> имеет ярко выраженные пересечения с дадаизмом.",
            "I wish I knew what he meant by \"<b>serendipity</b>\". -> Хотелось бы мне знать, что он имел в виду под \"<b>интуитивной прозорливостью</b>\"."
        ])
    )
    assert format_back_html(result) == back_expected 