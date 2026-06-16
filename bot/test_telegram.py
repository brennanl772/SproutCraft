"""Send a one-off test message to verify the Telegram wiring.

Run via the 'Telegram Test' GitHub Action (Actions tab -> Run workflow) once
you've added the TELEGRAM_TOKEN and TELEGRAM_CHAT_ID secrets.
"""
from . import config
from .notify import send


def main() -> None:
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        raise SystemExit(
            "Missing secrets. Add TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in "
            "Settings -> Secrets and variables -> Actions."
        )
    send("✅ <b>SproutCraft signal bot connected.</b>\n"
         "You'll get trade alerts here. (This is just a test message.)")
    print("Test message sent — check your Telegram.")


if __name__ == "__main__":
    main()
