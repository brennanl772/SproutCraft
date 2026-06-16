"""Optional ChatGPT (OpenAI) layer.

Turns a mechanical Signal into a short, human-readable rationale. It NEVER
changes the entry/stop/target — those come from the deterministic rules in
strategy.py. If OPENAI_API_KEY is unset (or the call fails), callers fall
back to the rule-based reason string.
"""
import os

from .strategy import Signal

SYSTEM_PROMPT = (
    "You are a trading assistant that explains mechanical stock signals. "
    "A fixed-rule system (EMA crossover with an ATR-based stop and target) "
    "produced the signal below. Explain it in 2-3 plain sentences a beginner "
    "can follow, then add one short risk caution. Do NOT invent or change any "
    "price levels. Do NOT predict the future or promise profit. Be concise."
)


def explain(sig: Signal, model: str | None = None) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    facts = (
        f"Symbol: {sig.symbol}\n"
        f"Side: {sig.side}\n"
        f"Trigger: {sig.reason}\n"
        f"Entry ~{sig.entry}, stop {sig.stop_loss}, target {sig.take_profit}, "
        f"risk/reward 1:{sig.risk_reward}."
    )
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": facts},
            ],
            max_tokens=180,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # never let the brain block an alert
        print(f"[warn] OpenAI explain failed: {exc}")
        return None
