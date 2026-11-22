"""Telegram notification module for BookMyShow seat checkers."""

import os
import urllib.request
import json
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        """Allow running without python-dotenv installed."""
        return False

load_dotenv()


def send_telegram_notification(message: str, token: str | None = None, chat_id: str | None = None) -> None:
    """Send a notification message via Telegram Bot API.
    
    Reads credentials from parameters, or falls back to environment variables:
    - TELEGRAM_BOT_TOKEN
    - TELEGRAM_CHAT_ID
    """
    bot_token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat:
        print("⚠️ Telegram notification skipped: TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID are not set.")
        return  # Silently skip if not configured

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Define the payload
    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        # Convert payload to a JSON string and encode to bytes
        data = json.dumps(payload).encode("utf-8")
        
        # Initialize request with necessary JSON Content-Type headers
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if not result.get("ok"):
                print(f"❌ Failed to send Telegram notification: {result}")
            else:
                print("✅ Telegram notification sent successfully!")
                
    except Exception as e:
        print(f"💥 Error sending Telegram notification: {e}")
