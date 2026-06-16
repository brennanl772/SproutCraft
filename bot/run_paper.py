"""Daily forward paper-trading run: update the ledger and, when something
closed, send a Telegram summary. State persists in bot/paper_state.json
(committed back by the GitHub Action)."""
from . import config
from .data import get_history
from .paper import PaperBook
from .notify import send

STATE_PATH = "bot/paper_state.json"


def main() -> None:
    book = PaperBook(STATE_PATH)
    summary, new_closed = book.update(lambda s: get_history(s, config.SIGNAL_PERIOD))
    book.save()
    print(summary)

    # Only ping the phone when a position actually closed (avoid daily noise).
    if new_closed and config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        send(summary)


if __name__ == "__main__":
    main()
