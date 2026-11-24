# BookMyShow Seat Checkers with Telegram Notifier

Two command-line scripts for checking seat availability on BookMyShow, with optional Telegram notifications when seats open up:

- `Seat_checker_by_cinemaURL.py` — lists all showtimes on a cinema page, lets you pick one, and checks its seats.
- `Seat_checker_by_showURL.py` — checks a specific show directly using its seat-layout URL (and can watch it repeatedly).

> **Note:** These scripts only **check and report** seat availability. They do not reserve or purchase tickets.

---

## Getting Started (For Beginners)

If you are new to GitHub or Python, follow these steps in order.

### Step 1: Install Python

1. Download **Python 3.10 or later** from [python.org/downloads](https://www.python.org/downloads/).
2. Run the installer.
   - **Windows users:** Make sure to check the box **"Add Python to PATH"** at the bottom of the installer before clicking **Install Now**.
3. Open **PowerShell** (Windows) or **Terminal** (Mac/Linux) and verify Python is installed:

   ```powershell
   python --version
   ```

   You should see something like `Python 3.12.x`.

### Step 2: Download This Project from GitHub

You can download the code in either of two ways:

- **Option A — Download ZIP (no Git required):**
  1. Click the green **`<> Code`** button at the top of this GitHub page.
  2. Click **Download ZIP**.
  3. Extract (unzip) the downloaded folder to somewhere easy to find, like your Desktop or Documents.
  4. Open **PowerShell** (or Terminal) inside that extracted folder:
     - *Windows tip:* Open the extracted folder in File Explorer, click the address bar, type `powershell`, and press **Enter**.

- **Option B — Clone with Git:**
  ```powershell
  git clone https://github.com/07ak01/BookMyShowWithTelegramNotification.git
  cd BookMyShowWithTelegramNotification
  ```

### Step 3: Download Visual Studio Code & Open the Project

1. Download and install **Visual Studio Code** from [code.visualstudio.com](https://code.visualstudio.com/).
2. Open **VS Code**.
3. Open the project folder:
   - Click **File** → **Open Folder...** in the top menu.
   - Browse to the folder you extracted or cloned in Step 2, select it, and click **Select Folder**.
   - *(If asked "Do you trust the authors of the files in this folder?", click **Yes, I trust the authors**.)*
4. Open the built-in terminal in VS Code by clicking **Terminal** → **New Terminal** in the top menu (or pressing `` Ctrl+` ``).

### Step 4: Install Dependencies

Run these two commands in your terminal (from inside the project folder) to install Playwright and its Chromium browser:

```powershell
python -m pip install playwright
python -m playwright install chromium
```

*(You only need to do this once.)*

---

## How to Use

### Option 1: Check a Cinema Page (Easiest)

Copy the BookMyShow cinema showtimes URL from your browser and run:

```powershell
python Seat_checker_by_cinemaURL.py "https://in.bookmyshow.com/cinemas/HYD/allu-cinemas-kokapet/buytickets/ALUC/20261124"
```

The script will open a Chromium window, list the available showtimes, and ask you to type the number of the show you want to check.

You can also skip the prompt with `--choose` (show numbers start at 1) and filter specific rows with `--rows`:

```powershell
python Seat_checker_by_cinemaURL.py "https://in.bookmyshow.com/cinemas/HYD/allu-cinemas-kokapet/buytickets/ALUC/20261124" --choose 3 --rows J K L
```

### Option 2: Check a Specific Show URL

If you already have the seat-layout URL for a show, pass it directly:

```powershell
python Seat_checker_by_showURL.py "https://in.bookmyshow.com/movies/HYD/seat-layout/ET00491771/PRHN/259279/20261216"
```

To check only specific rows, add `--rows`:

```powershell
python Seat_checker_by_showURL.py "https://in.bookmyshow.com/movies/HYD/seat-layout/ET00491771/PRHN/259279/20261216" --rows J I H G F E D C B A
```

You can also build the URL from its individual parts:

```powershell
python Seat_checker_by_showURL.py --city HYD --event ET00523251 --venue ALUC --session 6331 --date 20261107 --rows J K
```

#### Watch Continuously for Changes

Add `--watch <seconds>` to repeat the check automatically. Add `--headed` if you want to see the browser window while it runs:

```powershell
python Seat_checker_by_showURL.py "https://in.bookmyshow.com/movies/HYD/seat-layout/ET00491771/PRHN/259279/20261216" --rows J I H G F E D C B A --watch 60 --headed
```

Press `Ctrl+C` in the terminal at any time to stop watching.

---

## Telegram Notifications (Optional)

You can get a Telegram message whenever seats are available.

1. **Create a Telegram bot:** Open Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`, and follow the prompts to get your **Bot Token**.
2. **Get your Chat ID:** Message [@userinfobot](https://t.me/userinfobot) on Telegram to see your **Chat ID**.
3. **Provide your credentials** using any of these methods:
   - **Command-line flags:** Pass `--telegram-token "your_bot_token" --telegram-chat-id "your_chat_id"` when running either script.
   - **PowerShell (current terminal session only):**
     ```powershell
     $env:TELEGRAM_BOT_TOKEN="your_bot_token"
     $env:TELEGRAM_CHAT_ID="your_chat_id"
     ```
   - **Windows (saved permanently):**
     ```powershell
     [Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "your_bot_token", "User")
     [Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", "your_chat_id", "User")
     ```
     *(Open a new terminal window after running these so the saved variables take effect.)*

---

## Command-Line Options

`Seat_checker_by_showURL.py`:

| Option                                                | Description                                                            |
| ----------------------------------------------------- | ---------------------------------------------------------------------- |
| `--rows J K ...`                                      | Report only the specified rows; omit to report all rows.               |
| `--watch SECONDS`                                     | Repeat checks at the given interval until stopped.                     |
| `--headed`                                            | Show the Chromium window.                                              |
| `--timeout SECONDS`                                   | Maximum time to wait for the seat layout; default is 30.               |
| `--dump`                                              | Save `bms_page_dump.html` and `bms_page_dump.png` for troubleshooting. |
| `--city`, `--event`, `--venue`, `--session`, `--date` | Build a seat-layout URL instead of passing one.                        |
| `--telegram-token`, `--telegram-chat-id`              | Telegram credentials (overrides environment variables).                |

`Seat_checker_by_cinemaURL.py`:

| Option                                   | Description                                                        |
| ---------------------------------------- | ------------------------------------------------------------------ |
| `--choose NUMBER`                        | Select a showtime by its displayed number without prompting.       |
| `--rows J K ...`                         | Report only the specified rows; omit to report all rows.           |
| `--timeout SECONDS`                      | Maximum time to wait for the seat layout; default is 30.           |
| `--dump`                                 | Save the seat-layout page HTML and screenshot for troubleshooting. |
| `--telegram-token`, `--telegram-chat-id` | Telegram credentials (overrides environment variables).            |

---

## Troubleshooting

- **`python` is not recognized:** Python was not added to your system PATH during installation. Re-run the Python installer and check **"Add Python to PATH"**, or try using `py` instead of `python`.
- **Browser fails to launch:** Make sure you ran `python -m playwright install chromium` after installing Playwright.
- **No showtimes or seats detected:** The page may be unavailable, blocked, sold out, or BookMyShow may have changed its layout. Try again later, or run with `--dump` to save a screenshot and HTML file for inspection.
- **Seat availability changed:** Availability can change between checks—always confirm on BookMyShow before booking.
