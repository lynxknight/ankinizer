import asyncio
import dataclasses
import logging
import typing
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError

import reverso

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class PlaywrightParams:
    headless: bool = True
    slow_mo: int = 0

def replace_em_tags(text: str) -> str:
    """Replace <em> tags with <b> tags in the given text."""
    return text.replace("<em>", "<b>").replace("</em>", "</b>")

def clean_html(text: str) -> str:
    """Clean HTML by removing span and a tags while preserving their content."""
    soup = BeautifulSoup(text, 'html.parser')
    # Remove span tags but keep their content
    for span in soup.find_all('span'):
        span.unwrap()
    # Remove a tags but keep their content
    for a in soup.find_all('a'):
        a.unwrap()
    return str(soup).strip()

def parse_translations(html: str) -> typing.List[str]:
    """Parse translations from HTML content."""
    soup = BeautifulSoup(html, 'html.parser')
    translations = []
    for element in soup.select('#translations-content .translation .display-term'):
        translations.append(element.text.strip())
    return translations

def parse_examples(html: str) -> typing.List[typing.Dict[str, str]]:
    """Parse examples from HTML content."""
    soup = BeautifulSoup(html, 'html.parser')
    examples = []
    for element in soup.select('#examples-content .example'):
        en_text = element.select_one('.src .text')
        ru_text = element.select_one('.trg .text')
        if en_text and ru_text:
            examples.append({
                'en': clean_html(str(en_text)),
                'ru': clean_html(str(ru_text))
            })
    return examples

async def get_reverso_result(word: str, playwright_params: PlaywrightParams | None = None) -> reverso.ReversoResult:
    """Get translation and examples from Reverso Context using Playwright.
    
    Args:
        word: English word to translate
        playwright_params: Optional parameters for Playwright browser
        
    Returns:
        ReversoResult object with translations and examples
    """
    if playwright_params is None:
        playwright_params = PlaywrightParams()
        logger.info(f"Playwright params: {playwright_params}")
        
    async with async_playwright() as p:
        # Configure browser to look more like a real user
        browser = await p.chromium.launch(
            headless=playwright_params.headless,
            slow_mo=playwright_params.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
            ]
        )
        
        # Create a context with realistic viewport and user agent
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='en-GB',
            timezone_id='Europe/London',
            geolocation={'latitude': 51.5074, 'longitude': -0.1278},
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'en-GB,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        # Create a new page and set up realistic behavior
        page = await context.new_page()
        await page.set_extra_http_headers({
            'DNT': '1',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
        })
        
        # Add random mouse movements and delays to simulate human behavior
        await page.mouse.move(100, 100)
        await asyncio.sleep(0.5)
        await page.mouse.move(200, 200)
        await asyncio.sleep(0.5)
        
        # Navigate to Reverso Context
        url = f"https://context.reverso.net/translation/english-russian/{word}"
        logger.info(f"Navigating to {url}")
        await page.goto(url, wait_until='networkidle')
        
        # Wait for translations and examples to load
        try:
            await page.wait_for_selector("#translations-content", timeout=10000)
        except TimeoutError:
            await page.screenshot(path="screenshot.png")
            logger.error("Timeout waiting for translations content")
            raise
        await page.wait_for_selector("#examples-content", timeout=10000)
        
        # Get page content
        content = await page.content()
        
        await context.close()
        await browser.close()
        
        # Parse translations and examples using BeautifulSoup
        translations = parse_translations(content)
        examples = parse_examples(content)
        
        # Create ReversoResult object with <em> tags replaced by <b> tags
        return reverso.ReversoResult(
            en_word=word,
            ru_translations=translations,
            usage_samples=[
                reverso.ReversoTranslationSample(
                    en=replace_em_tags(e['en']),
                    ru=replace_em_tags(e['ru'])
                ) for e in examples[:3]
            ]
        )

async def main():
    result = await get_reverso_result(
        "serendipity",
        playwright_params=PlaywrightParams(headless=False, slow_mo=500)
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
