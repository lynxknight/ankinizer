import os
import time
import asyncio
import dataclasses
import logging

import playwright.async_api
import reverso_agent
import env

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class PlaywrightParams:
    headless: bool = True
    slow_mo: int = 0

def format_back_html(reverso_result: reverso_agent.ReversoResult) -> str:
    return (''
        + " / ".join(reverso_result.ru_translations)
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join(map(str, reverso_result.usage_samples))
        + ''
    )

async def add_card_to_anki(reverso_result: reverso_agent.ReversoResult, playwright_params: PlaywrightParams | None = None) -> None:
    if playwright_params is None:
        playwright_params = PlaywrightParams()
    async with playwright.async_api.async_playwright() as p:
        browser = await p.chromium.launch(headless=playwright_params.headless, slow_mo=playwright_params.slow_mo)
        context = await browser.new_context()
        page = await context.new_page()
        
        logger.info("Navigating to AnkiWeb")
        await page.goto("https://ankiweb.net/about")
        await page.get_by_role("link", name="Log In").click()
        await page.get_by_role("textbox", name="Email").click()
        await page.get_by_role("textbox", name="Email").fill(os.environ["ANKI_USERNAME"])
        await page.get_by_role("textbox", name="Password").click()
        await page.get_by_role("textbox", name="Password").fill(os.environ["ANKI_PASSWORD"])
        await page.get_by_role("button", name="Log In").click()
        logger.info("Logging in...")
        
        try:
            await page.get_by_role("button", name="English words").wait_for(timeout=5000)
        except playwright.async_api.TimeoutError:
            logger.error("Failed to login")
            return False
            
        logger.info("Logged in, navigating to deck")
        await page.get_by_role("button", name="English words").click()
        logger.info("Navigated to deck")
        await page.get_by_role("link", name="Add").click()
        logger.info("Navigated to add card")
        
        logger.info("Waiting for front div")
        try:
            front_div = page.get_by_role("main").locator("div").filter(has_text="Front").locator("div").nth(1)
        except playwright.async_api.TimeoutError:
            logger.error("Failed to find front div")
            page.screenshot("screenshot.png")
            raise
        await front_div.fill(reverso_result.en_word)
        await page.wait_for_timeout(300)
        logger.info("front div filled, going for back div")
        
        back_div = page.get_by_role("main").locator("div").filter(has_text="Back").locator("div").nth(1)
        await back_div.fill('tst')
        logger.info("tst fill happened, applying real formatting")
        html = format_back_html(reverso_result)
        # Properly escape the HTML content for JavaScript
        escaped_html = html.replace("'", "\\'").replace("\n", "\\n")
        logger.info(f"Back html {escaped_html=}")
        await back_div.evaluate(f"el => {{ el.innerHTML = '{escaped_html}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
        await back_div.click()
        logger.info(f"Back html evaluated")
        await page.wait_for_timeout(300)
        logger.info("Adding card")
        await page.get_by_role("button", name="Add").click()
        try:
            await page.get_by_text("Added").wait_for(timeout=1000)
        except playwright.async_api.TimeoutError:
            logger.error("Failed to add card")
            return False
        logger.info("Card added")
        return True


async def main():
    env.setup_env()
    await add_card_to_anki(
        reverso_agent.ReversoResult(
            en_word="serendipity" + f'{time.time()}',
            ru_translations=["серендипность", "интуитивная прозорливость", "удача", "милость"],
            usage_samples="""Process art in its employment of <b>serendipity</b> has a marked correspondence with Dada. -> Процесс-арт в его отношении к <b>серендипности</b> имеет ярко выраженные пересечения с дадаизмом.

          I wish I knew what he meant by "<b>serendipity</b>". -> Хотелось бы мне знать, что он имел в виду под "<b>интуитивной прозорливостью</b>".

          That my child is back in her mother's arms... is <b>serendipity</b> and grace. -> То, что моя дочь возвратилась в материнские объятия это <b>удача</b> и милость.""".split('\n')
        ),
        playwright_params=PlaywrightParams(headless=False, slow_mo=500),
    )

if __name__ == "__main__":
    asyncio.run(main())
