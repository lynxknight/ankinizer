import os
import time
import asyncio
import dataclasses
import logging

import playwright.async_api
import reverso
import env

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class PlaywrightParams:
    headless: bool = True
    slow_mo: int = 0

def format_back_html(reverso_result: reverso.ReversoResult) -> str:
    return (''
        + " / ".join(reverso_result.ru_translations)
        + "<div><br><br></div> * "
        + "<div><br></div> * ".join(map(str, reverso_result.usage_samples))
        + ''
    )

async def add_card_to_anki(reverso_result: reverso.ReversoResult, playwright_params: PlaywrightParams | None = None) -> None:
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
        await page.get_by_role("link", name="Add").click()
        
        front_div = page.get_by_role("main").locator("div").filter(has_text="Front").locator("div").nth(1)
        await front_div.fill(reverso_result.en_word)
        await page.wait_for_timeout(300)
        
        back_div = page.get_by_role("main").locator("div").filter(has_text="Back").locator("div").nth(1)
        back_div.fill('tst')
        html = format_back_html(reverso_result)
        await back_div.evaluate("el => {" + f"el.innerHTML = '{html}'" + "; el.dispatchEvent(new Event('input', { bubbles: true })); } ")
        print('Adding back html: ', html)
        back_div.click()
        await page.wait_for_timeout(300)

        await page.get_by_role("button", name="Add").click()
        try:
            await page.get_by_text("Added").wait_for(timeout=1000)
        except playwright.async_api.TimeoutError:
            return False
        return True


async def main():
    await add_card_to_anki(
        reverso.ReversoResult(
            en_word="hack" + f'{time.time()}',
            ru_translations=["хак", "взлом"],
            usage_samples=[
                "I <b>hacked</b> the website",
            ],
        ),
        playwright_params=PlaywrightParams(headless=False, slow_mo=500),
    )

if __name__ == "__main__":
    asyncio.run(main())
