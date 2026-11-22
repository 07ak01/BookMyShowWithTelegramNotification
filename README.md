# BookMyShow Seat Checkers with Telegram bot notifier

Two Playwright-based command-line scripts for inspecting seat availability in a BookMyShow show layout:

- `Seat_checker_by_showURL.py` checks a show directly from its seat-layout URL.
- `Seat_checker_by_cinemaURL.py` lists the showtimes on a cinema page, lets you choose one, then checks its seat layout.

The scripts report seat availability; they do not reserve or purchase seats.

## Requirements

- Python 3.10 or later
- Playwright for Python
- Playwright's Chromium browser

Install the dependency and browser once:

```powershell
python -m pip install playwright
python -m playwright install chromium
```

Run commands from this folder.

## Telegram Notifications (Optional)

To receive Telegram alerts when seats become available, set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as environment variables (or pass them via `--telegram-token` and `--telegram-chat-id`).

In PowerShell (current session):

```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
```

To persist them in Windows user environment variables:

```powershell
[Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "your_bot_token", "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", "your_chat_id", "User")
```

Open a new terminal after setting persistent environment variables so they take effect.

## Check a Show URL

Pass the full BookMyShow seat-layout URL. Omit `--rows` to report all rows, or provide the row letters you want to inspect.

```powershell
python Seat_checker_by_showURL.py "https://in.bookmyshow.com/movies/HYD/seat-layout/ET00491771/PRHN/259279/20261216"

python Seat_checker_by_showURL.py "https://in.bookmyshow.com/movies/HYD/seat-layout/ET00491771/PRHN/259279/20261216" --rows J I H G F E D C B A
```

The URL can also be assembled from its parts:

```powershell
python Seat_checker_by_showURL.py --city HYD --event ET00523251 --venue ALUC --session 6331 --date 20261107 --rows J K
```

### Watch for Changes

Use `--watch` to repeat the check at the specified interval in seconds. Newly available seats are marked in the console. Use `--headed` to show Chromium while checking.

```powershell
python Seat_checker_by_showURL.py "https://in.bookmyshow.com/movies/HYD/seat-layout/ET00491771/PRHN/259279/20261216" --rows J I H G F E D C B A --watch 60 --headed
```

Stop the watcher with `Ctrl+C`. Each check prints its start time, and the availability report includes a timestamp.

## Choose a Show from a Cinema Page

Pass a BookMyShow cinema showtimes URL. The script displays the available showtimes and prompts you to choose one.

```powershell
python Seat_checker_by_cinemaURL.py "https://in.bookmyshow.com/cinemas/HYD/allu-cinemas-kokapet/buytickets/ALUC/20261124"
```

Choose a show non-interactively with `--choose` (show numbers start at 1). You can also limit the report to specific rows:

```powershell
python Seat_checker_by_cinemaURL.py "https://in.bookmyshow.com/cinemas/HYD/allu-cinemas-kokapet/buytickets/ALUC/20261124" --choose 3 --rows J K L
```

This flow opens a visible Chromium window. After a show is selected, it checks that show's seat layout and reports availability with a timestamp. The shared seat-layout checker attempts to dismiss the seat-count popup by clicking **Select Seats** directly.

## Options

`Seat_checker_by_showURL.py`:

| Option                                                | Description                                                            |
| ----------------------------------------------------- | ---------------------------------------------------------------------- |
| `--rows J K ...`                                      | Report only the specified rows; omit to report all rows.               |
| `--watch SECONDS`                                     | Repeat checks at the given interval until stopped.                     |
| `--headed`                                            | Show the Chromium window.                                              |
| `--timeout SECONDS`                                   | Maximum time to wait for the seat layout; default is 30.               |
| `--dump`                                              | Save `bms_page_dump.html` and `bms_page_dump.png` for troubleshooting. |
| `--city`, `--event`, `--venue`, `--session`, `--date` | Build a seat-layout URL instead of passing one.                        |

`Seat_checker_by_cinemaURL.py`:

| Option              | Description                                                        |
| ------------------- | ------------------------------------------------------------------ |
| `--choose NUMBER`   | Select a showtime by its displayed number without prompting.       |
| `--rows J K ...`    | Report only the specified rows; omit to report all rows.           |
| `--timeout SECONDS` | Maximum time to wait for the seat layout; default is 30.           |
| `--dump`            | Save the seat-layout page HTML and screenshot for troubleshooting. |

## Troubleshooting

- If no showtimes or seats are detected, the page may be unavailable, blocked, sold out, or have changed its layout. Try again later or use `--dump` with the show-URL checker to inspect the loaded page.
- The seat map is rendered by BookMyShow in a canvas, so changes to its page implementation can require updates to the extraction logic.
- Availability can change between checks. Confirm the final selection on BookMyShow before booking.
