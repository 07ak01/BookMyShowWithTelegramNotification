"""Choose a BookMyShow cinema showtime and check its seat layout.

Usage:
    python Seat_checker_by_cinemaURL.py <cinema-showtimes-url>
    python Seat_checker_by_cinemaURL.py <cinema-showtimes-url> --rows J K L
    python Seat_checker_by_cinemaURL.py <cinema-showtimes-url> --choose 3

Setup:
    pip install playwright
    python -m playwright install chromium
"""

import argparse
import asyncio
import re
from datetime import datetime

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

import Seat_checker_by_showURL as seat_checker
import telegram_notifier

SHOWS_SELECTOR = '[role="button"][aria-label^="Book "]'
SHOWS_JS = r"""
() => Array.from(document.querySelectorAll('[role="button"][aria-label^="Book "]')).map(button => {
  const row = button.parentElement?.parentElement?.parentElement;
  const metadata = row?.firstElementChild?.innerText || '';
  const marker = (button.getAttribute('color') || '').toUpperCase();
  return {
    movie: metadata.replace(/\s+/g, ' ').trim(),
    time: (button.getAttribute('aria-label') || '').replace(/^Book\s+/, ''),
    format: button.lastElementChild?.textContent?.trim() || '',
    marker: marker === '#1FAD3E' ? 'Green' : marker === '#E8A900' ? 'Amber' : marker || 'Unknown'
  };
})
"""


def print_shows(shows: list[dict]) -> None:
    print("\nAvailable showtimes:")
    for index, show in enumerate(shows, start=1):
        print(f"{index:>2}. {show['movie']} | {show['time']} | {show['format']} | {show['marker']} marker")


def choose_show(shows: list[dict], requested: int | None) -> int:
    if requested is not None:
        if not 1 <= requested <= len(shows):
            raise ValueError(f"Choose a show number from 1 to {len(shows)}.")
        return requested - 1

    while True:
        try:
            choice = int(input("\nEnter the show number to check: ").strip())
        except ValueError:
            print("Enter a number from the list.")
            continue
        if 1 <= choice <= len(shows):
            return choice - 1
        print(f"Choose a number from 1 to {len(shows)}.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Choose a BookMyShow showtime and check seat availability.")
    parser.add_argument("url", help="BookMyShow cinema showtimes URL")
    parser.add_argument("--choose", type=int, help="Select a show by its number instead of prompting")
    parser.add_argument("--rows", nargs="+", help="Rows to check; omit to report all rows")
    parser.add_argument("--timeout", type=int, default=30, help="Seconds to wait for the seat layout")
    parser.add_argument("--dump", action="store_true", help="Save seat-layout HTML and screenshot for debugging")
    parser.add_argument("--telegram-token", help="Telegram Bot Token")
    parser.add_argument("--telegram-chat-id", help="Telegram Chat ID")
    args = parser.parse_args()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=seat_checker.USER_AGENT,
            locale="en-IN",
            viewport={"width": 1400, "height": 1000},
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()

        try:
            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.locator(SHOWS_SELECTOR).first.wait_for(state="visible", timeout=60000)
            except PlaywrightTimeout:
                body = (await page.locator("body").inner_text())[:500]
                print(f"No showtimes found. The page may be blocked or the layout changed.\n{body}")
                return

            shows = await page.evaluate(SHOWS_JS)
            if not shows:
                print("No showtimes found on this cinema page.")
                return

            print_shows(shows)
            try:
                selected = choose_show(shows, args.choose)
            except ValueError as error:
                parser.error(str(error))

            selected_show = shows[selected]
            print(f"\nOpening {selected_show['movie']} at {selected_show['time']}...")
            await page.locator(SHOWS_SELECTOR).nth(selected).click(timeout=15000)
            try:
                await page.wait_for_url(re.compile(r"/seat-layout/"), timeout=30000)
            except PlaywrightTimeout:
                print(f"Showtime did not open a seat layout. Current URL: {page.url}")
                return

            seat_url = page.url
            print(f"Seat layout: {seat_url}")
            check_args = argparse.Namespace(
                rows=args.rows,
                timeout=args.timeout,
                dump=args.dump,
                telegram_token=args.telegram_token,
                telegram_chat_id=args.telegram_chat_id
            )
            print(f"\nChecking seat availability @ {datetime.now():%Y-%m-%d %H:%M:%S}", flush=True)
            current = await seat_checker.check_once(page, seat_url, check_args)
            if current is not None:
                total_free_seats = {r: seats for r, seats in current.items() if seats}
                if total_free_seats:
                    summary_str = ", ".join(f"Row {r}: {', '.join(f'{r}{s}' for s in seats)}" for r, seats in total_free_seats.items())
                    alert_msg = f"🎟️ <b>BookMyShow Seat Alert!</b>\n{summary_str}\n🔗 <a href='{seat_url}'>Show Link</a>"
                    telegram_notifier.send_telegram_notification(alert_msg, args.telegram_token, args.telegram_chat_id)
        finally:
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")