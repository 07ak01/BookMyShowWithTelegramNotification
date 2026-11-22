"""Check BookMyShow seat availability for specific rows of a show.

Usage examples:
    python Seat_checker_by_showURL.py https://in.bookmyshow.com/movies/HYD/seat-layout/ET00523251/ALUC/6323/20261105
    python Seat_checker_by_showURL.py https://in.bookmyshow.com/movies/hyderabad/seat-layout/ET00523251/ALUC/6331/20261107 --rows J I H G F E D C B A
    python Seat_checker_by_showURL.py --city HYD --event ET00523251 --venue ALUC --session 6323 --date 20261105 --rows J K
    python Seat_checker_by_showURL.py <url> --rows H J --watch 60 --headed

Setup:
    pip install playwright
    python -m playwright install chromium
"""

import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

import telegram_notifier

BASE_URL = "https://in.bookmyshow.com/movies/{city}/seat-layout/{event}/{venue}/{session}/{date}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# BMS draws the seat map on a react-konva canvas, so we read the Konva scene graph.
# Seat groups have ids like "Seat-D-9-31-03" (internal area/row, not the visible letter),
# so each seat is matched to the row-label column by y-position.
# Sold seats are filled grey (#E5E5E5); available/bestseller seats are filled white.
EXTRACT_SEATS_JS = r"""
() => {
  const content = document.querySelector('.konvajs-content');
  if (!content) return [];
  const isStage = o => o && typeof o === 'object' && typeof o.getClassName === 'function'
                       && o.getClassName() === 'Stage';
  let stage = null;
  for (let el = content; el && !stage; el = el.parentElement) {
    const fk = Object.keys(el).find(k => k.startsWith('__reactFiber'));
    for (let f = fk && el[fk]; f && !stage; f = f.return) {
      if (isStage(f.stateNode)) stage = f.stateNode;
      else if (f.ref && isStage(f.ref.current)) stage = f.ref.current;
      for (let h = f.memoizedState; h && !stage && typeof h === 'object'; h = h.next) {
        const v = h.memoizedState;
        if (isStage(v)) stage = v; else if (v && isStage(v.current)) stage = v.current;
      }
    }
  }
  if (!stage) return [];

  const seatGroups = stage.find(n => n.getClassName() === 'Group' && /^Seat-/.test(n.id()));
  const rowLabels = stage.find('Text')
    .filter(t => /^[A-Z]{1,3}$/.test(t.text()) && !/^Seat-/.test((t.getParent() || {attrs: {}}).attrs.id || ''))
    .map(t => ({ row: t.text(), y: t.getAbsolutePosition().y }));

  const out = [];
  for (const g of seatGroups) {
    const text = g.findOne('Text');
    const rect = g.findOne('Rect');
    if (!text || !rect || !/^\d+$/.test(text.text())) continue;
    const y = text.getAbsolutePosition().y;
    let best = null;
    for (const r of rowLabels) {
      const d = Math.abs(r.y - y);
      if (d < 8 && (!best || d < best.d)) best = { row: r.row, d };
    }
    const fill = String(rect.fill() || '').toUpperCase();
    const stroke = String(rect.stroke() || '').toUpperCase();
    const isSold = fill.includes('E5E5E5') || fill.includes('D9D9D9') || fill.includes('CCCCCC');
    const status = isSold ? 'sold' : 'available';
    out.push({ row: best ? best.row : '?', seat: String(parseInt(text.text(), 10)), status, id: g.id(),
               stroke: String(rect.stroke() || '').toUpperCase() });
  }
  return out;
}
"""

BLOCK_MARKERS = re.compile(r"(access denied|attention required|just a moment|verify you are human|captcha)", re.I)


def build_url(args: argparse.Namespace) -> str:
    if args.url:
        return args.url
    missing = [n for n in ("city", "event", "venue", "session", "date") if not getattr(args, n)]
    if missing:
        sys.exit(f"Provide a URL or all of: --{' --'.join(missing)}")
    return BASE_URL.format(city=args.city, event=args.event, venue=args.venue,
                           session=args.session, date=args.date)


async def dismiss_popups(page) -> None:
    # Continue directly from the quantity dialog without selecting a seat count.
    try:
        await page.locator('button[aria-label="Select Seats"], button:has-text("Tickets"), div:has-text("Select Seats")').first.click(timeout=3000)
        await page.wait_for_timeout(1000)
    except PlaywrightTimeout:
        pass
    for text in ("Accept", "I Agree", "Continue", "Select Seats", "Proceed"):
        btn = page.get_by_role("button", name=re.compile(rf"^\s*{text}\s*$", re.I))
        try:
            if await btn.count() and await btn.first.is_visible():
                await btn.first.click(timeout=2000)
                await page.wait_for_timeout(500)
        except PlaywrightTimeout:
            pass


async def read_layout(page, timeout_s: int) -> list[dict]:
    seats: list[dict] = []
    for _ in range(timeout_s):
        await dismiss_popups(page)
        seats = await page.evaluate(EXTRACT_SEATS_JS)
        if seats:
            # One extra pass lets late-rendering rows settle.
            await page.wait_for_timeout(1500)
            return await page.evaluate(EXTRACT_SEATS_JS)
        await page.wait_for_timeout(1000)
    return seats


# Regular free seats have a green border; bestseller seats use a yellow one.
REGULAR_STROKE = "#1FAD3E"


def seat_sort_key(seat: str) -> int:
    return int(seat) if seat.isdigit() else 0


def print_bestsellers(seats: list[dict], rows: list[str]) -> None:
    wanted = set(rows)
    by_row: dict[str, list[str]] = {r: [] for r in rows}
    for s in seats:
        if s["row"] in wanted and s["status"] == "available" and s.get("stroke") not in ("", REGULAR_STROKE):
            by_row[s["row"]].append(s["seat"])
    found = {r: sorted(set(v), key=seat_sort_key) for r, v in by_row.items() if v}
    print(f"\n--- Bestseller seats free @ {datetime.now():%Y-%m-%d %H:%M:%S} ---")
    if not found:
        print("None")
    for row, free in found.items():
        print(f"Row {row}: {len(free)} bestseller -> {', '.join(f'{row}{s}' for s in free)}")


def summarize(seats: list[dict], rows: list[str]) -> dict[str, list[str]]:
    wanted = {r.upper() for r in rows}
    available: dict[str, list[str]] = {r.upper(): [] for r in rows}
    for s in seats:
        if s["row"] in wanted and s["status"] == "available":
            available[s["row"]].append(s["seat"])
    for r in available:
        available[r] = sorted(set(available[r]), key=seat_sort_key)
    return available


def print_report(available: dict[str, list[str]], all_rows: set[str], unknown_count: int) -> None:
    print(f"\n--- Seat availability @ {datetime.now():%Y-%m-%d %H:%M:%S} ---")
    for row, seats in available.items():
        if row not in all_rows:
            print(f"Row {row}: not found in layout")
        elif seats:
            print(f"Row {row}: {len(seats)} available -> {', '.join(f'{row}{s}' for s in seats)}")
        else:
            print(f"Row {row}: no available seats")
    if unknown_count:
        print(f"(note: {unknown_count} seat(s) had an unrecognised status; run with --dump to inspect)")


def print_row_counts(available: dict[str, list[str]], seats: list[dict]) -> None:
    print(f"\n--- Seats per row @ {datetime.now():%Y-%m-%d %H:%M:%S} ---")
    total_free = 0
    print(f"{'ROW':>3} | {'FREE':>4} | {'TOTAL':>5} | AVAILABLE SEATS")
    print("----+------+-------+----------------")
    for row, free in available.items():
        total = sum(1 for s in seats if s["row"] == row)
        total_free += len(free)
        seat_ids = ", ".join(f"{row}{number}" for number in free) or "-"
        print(f"{row:>3} | {len(free):>4} | {total:>5} | {seat_ids}")
    print("----+------+-------+----------------")
    print(f"{'ALL':>3} | {total_free:>4} | {len(seats):>5} |")


async def check_once(page, url: str, args: argparse.Namespace) -> dict[str, list[str]] | None:
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    seats = await read_layout(page, args.timeout)

    if args.dump:
        Path("bms_page_dump.html").write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path="bms_page_dump.png", full_page=True)
        print("Saved bms_page_dump.html and bms_page_dump.png")

    if not seats:
        title = await page.title()
        if BLOCK_MARKERS.search(title) or BLOCK_MARKERS.search(await page.inner_text("body")):
            print("Blocked by bot protection. Retry with --headed and solve any challenge in the browser.")
        else:
            print(f"No seat layout found (page title: {title!r}). Show may be sold out/closed, "
                  "or the layout markup changed; run with --dump to inspect.")
        return None

    all_rows = {s["row"] for s in seats}
    if not args.rows:
        # dict.fromkeys keeps layout order (front to back) while de-duplicating.
        layout_rows = list(dict.fromkeys(s["row"] for s in seats))
        print_bestsellers(seats, layout_rows)
        available = summarize(seats, layout_rows)
        print_row_counts(available, seats)
        return available

    rows = [r.upper() for r in args.rows]
    unknown = sum(1 for s in seats if s["row"] in rows and s["status"].startswith("unknown"))
    print_bestsellers(seats, rows)
    available = summarize(seats, rows)
    print_report(available, all_rows, unknown)
    return available


async def main() -> None:
    parser = argparse.ArgumentParser(description="Check BookMyShow seat availability for given rows.")
    parser.add_argument("url", nargs="?", help="BookMyShow seat-layout URL")
    parser.add_argument("--city", help="City code, e.g. HYD")
    parser.add_argument("--event", help="Event code, e.g. ET00523251")
    parser.add_argument("--venue", help="Venue/cinema code, e.g. ALUC")
    parser.add_argument("--session", help="Showtime/session id, e.g. 6323")
    parser.add_argument("--date", help="Show date as YYYYMMDD")
    parser.add_argument("--rows", nargs="+",
                        help="Row letters to check, e.g. J K L (omit to show seat counts for every row)")
    parser.add_argument("--watch", type=int, default=0, metavar="SECONDS",
                        help="Re-check every N seconds until stopped (Ctrl+C)")
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    parser.add_argument("--timeout", type=int, default=30, help="Seconds to wait for the layout")
    parser.add_argument("--dump", action="store_true", help="Save page HTML and screenshot for debugging")
    parser.add_argument("--telegram-token", help="Telegram Bot Token")
    parser.add_argument("--telegram-chat-id", help="Telegram Chat ID")
    args = parser.parse_args()

    url = build_url(args)
    print(f"Checking {url}")
    print(f"Rows: {', '.join(r.upper() for r in args.rows) if args.rows else 'all'}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not args.headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT, locale="en-IN", viewport={"width": 1400, "height": 1000}
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()

        try:
            previous = None
            while True:
                print(f"\nChecking seat availability @ {datetime.now():%Y-%m-%d %H:%M:%S}", flush=True)
                current = await check_once(page, url, args)
                if current is not None:
                    # Check if any seats are available across wanted rows
                    total_free_seats = {r: seats for r, seats in current.items() if seats}
                    if total_free_seats:
                        summary_str = ", ".join(f"Row {r}: {', '.join(f'{r}{s}' for s in seats)}" for r, seats in total_free_seats.items())
                        alert_msg = f"🎟️ <b>BookMyShow Seat Alert!</b>\n{summary_str}\n🔗 <a href='{url}'>Show Link</a>"
                        telegram_notifier.send_telegram_notification(alert_msg, args.telegram_token, args.telegram_chat_id)

                    if previous is not None:
                        newly_free = {r: sorted(set(current[r]) - set(previous.get(r, [])), key=seat_sort_key)
                                      for r in current}
                        for r, seats in newly_free.items():
                            if seats:
                                print(f"NEW in row {r}: {', '.join(f'{r}{s}' for s in seats)}\a")
                                new_msg = f"🚨 <b>New Seats Freed Up!</b>\nRow {r}: {', '.join(f'{r}{s}' for s in seats)}\n🔗 <a href='{url}'>Show Link</a>"
                                telegram_notifier.send_telegram_notification(new_msg, args.telegram_token, args.telegram_chat_id)

                previous = current if current is not None else previous
                if args.watch <= 0:
                    break
                await asyncio.sleep(args.watch)
        except KeyboardInterrupt:
            pass
        finally:
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
