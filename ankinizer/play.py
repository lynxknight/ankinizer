import asyncio
from playwright.async_api import async_playwright, expect

from ankinizer import reverso_agent


def format_back_html(reverso_result: reverso_agent.ReversoResult) -> str:
    return (
        " / ".join(reverso_result.ru_translations)
        + "<br><br> * "
        + "<br> * ".join(map(str, reverso_result.usage_samples))
    )

async def run(reverso_result: reverso_agent.ReversoResult,) -> None:
    browser = await playwright.chromium.launch(headless=False, slow_mo=500)
    context = await browser.new_context()
    page = await context.new_page()
    
    await page.goto("https://ankiweb.net/about")
    await page.get_by_role("link", name="Log In").click()
    await page.get_by_role("textbox", name="Email").click()
    await page.get_by_role("textbox", name="Email").fill("clanfrl@yandex.ru")
    await page.get_by_role("textbox", name="Password").click()
    await page.get_by_role("textbox", name="Password").fill("S6Z-TWt-QGx-8Gc")
    await page.get_by_role("button", name="Log In").click()
    await page.get_by_role("button", name="English words").click()
    await page.get_by_role("link", name="Add").click()
    
    front_div = page.get_by_role("main").locator("div").filter(has_text="Front").locator("div").nth(1)
    await front_div.fill("hack")
    await front_div.evaluate("el => el.innerHTML = 'F<b>ron</b>tttt'")
    await front_div.click()
    await page.wait_for_timeout(300)
    
    back_div = page.get_by_role("main").locator("div").filter(has_text="Back").locator("div").nth(1)
    await back_div.evaluate("el => el.innerHTML = 'B<b>ac</b>kkkk'")
    await back_div.click()
    await page.wait_for_timeout(300)

    await page.get_by_role("button", name="Add").click()

    # Keep the browser open for a while to observe the result
    await page.wait_for_timeout(5000)

    await context.close()
    await browser.close()


async def main():
    async with async_playwright() as playwright:
        await run(playwright)


if __name__ == "__main__":
    asyncio.run(main())
