# Get the signal bot running (≈5 minutes, all from your phone)

The code is done and tested. Only **two** things are tied to your accounts and
must be done by you. Follow these taps.

## 1. Make your Telegram bot
1. Open **Telegram** → search **@BotFather** → send `/newbot` → follow prompts.
2. Copy the **token** it gives you (e.g. `123456789:ABCdef...`).
3. Search **@userinfobot** → it replies with your numeric **Id** (your chat id).
4. Open your new bot and send it any message (e.g. "hi") so it may DM you.

## 2. Add the secrets on GitHub
Repo → **Settings → Secrets and variables → Actions → New repository secret**.
Add these two (a third is optional):

| Secret name | Value |
|---|---|
| `TELEGRAM_TOKEN` | the BotFather token |
| `TELEGRAM_CHAT_ID` | the Id from @userinfobot |
| `OPENAI_API_KEY` | *(optional)* your OpenAI key for AI commentary |

## 3. Test the wiring (one tap)
Repo → **Actions → Telegram Test → Run workflow**.
Within ~30s you should get a "✅ bot connected" message in Telegram.

## 4. Use it
- **Actions → Backtest → Run workflow** → read the real historical stats in the
  run summary *before trusting it*.
- **Actions → Stock Signals → Run workflow** → a live scan (messages you only if
  something triggers today).
- **Actions → Paper Trading → Run workflow** → start the hypothetical-money
  tracker. Watch it for a few weeks before risking anything real.

## Want the daily auto-runs?
GitHub only runs scheduled jobs from the **default branch**. Merge this branch to
your default branch (or change the default branch) and the daily Signals + Paper
jobs fire on their own. Until then, the **Run workflow** buttons above work fine.

---
⚠️ This is a mechanical strategy with optional AI commentary. It is **not**
financial advice and **not** guaranteed to profit — it has losing trades and
drawdowns. Paper-trade it first and only risk money you can afford to lose.
