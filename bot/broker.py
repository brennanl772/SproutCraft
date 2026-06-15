"""Broker abstraction: a fully-working PaperBroker (no network, no money) and a
CoinbaseBroker for live spot trading via the official Advanced Trade SDK.

The bot logic talks only to this interface, so paper and live behave identically
except for where the orders actually go.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Order:
    product: str
    side: str           # "BUY" / "SELL"
    qty: float
    price: float
    kind: str           # "MARKET" / "STOP" / "LIMIT"
    ts: dt.datetime


class PaperBroker:
    """Simulated spot account. Cash + one position per product. No leverage."""

    def __init__(self, cash_usd: float = 50.0):
        self.cash = cash_usd
        self.positions: dict[str, float] = {}      # product -> base qty
        self.entry_price: dict[str, float] = {}
        self.orders: list[Order] = []

    # --- account ---
    def cash_usd(self) -> float:
        return self.cash

    def position_qty(self, product: str) -> float:
        return self.positions.get(product, 0.0)

    # --- execution (spot, cash-settled) ---
    def market_buy(self, product: str, qty: float, price: float, ts) -> Order:
        cost = qty * price
        cost = min(cost, self.cash)               # never spend more than we have
        qty = cost / price
        self.cash -= cost
        self.positions[product] = self.positions.get(product, 0.0) + qty
        self.entry_price[product] = price
        o = Order(product, "BUY", qty, price, "MARKET", ts)
        self.orders.append(o)
        return o

    def market_sell(self, product: str, price: float, ts, kind: str = "MARKET") -> Order:
        qty = self.positions.get(product, 0.0)
        self.cash += qty * price
        self.positions[product] = 0.0
        o = Order(product, "SELL", qty, price, kind, ts)
        self.orders.append(o)
        return o

    def equity(self, marks: dict[str, float]) -> float:
        v = self.cash
        for p, q in self.positions.items():
            v += q * marks.get(p, self.entry_price.get(p, 0.0))
        return v


class AlpacaBroker:
    """Live/paper trading via Alpaca REST (trades BOTH SPY stock and BTC/USD crypto).

    Free paper keys: alpaca.markets -> Paper Trading -> API Keys. Set
    APCA_API_KEY_ID / APCA_API_SECRET_KEY in the environment.

    NOTE: validate with PAPER keys before ever using live keys. Stock orders use
    a native bracket (entry + take-profit + stop) so the 1:2 and the
    below-support stop are enforced by the exchange.
    """

    TF = {"ONE_HOUR": "1Hour", "ONE_DAY": "1Day", "FIFTEEN_MINUTE": "15Min"}

    def __init__(self, key_id: str, secret: str, paper: bool = True):
        import urllib.request  # noqa: F401  (used via helper below)
        self.key_id = key_id
        self.secret = secret
        self.trade_base = ("https://paper-api.alpaca.markets" if paper
                           else "https://api.alpaca.markets")
        self.data_base = "https://data.alpaca.markets"

    # --- low-level REST helper ---
    def _req(self, url: str, method: str = "GET", body: dict | None = None):
        import json
        import urllib.request
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    @staticmethod
    def _is_crypto(symbol: str) -> bool:
        return "/" in symbol

    # --- account ---
    def cash_usd(self) -> float:
        return float(self._req(f"{self.trade_base}/v2/account")["cash"])

    def position_qty(self, symbol: str) -> float:
        try:
            sym = symbol.replace("/", "")
            return float(self._req(f"{self.trade_base}/v2/positions/{sym}")["qty"])
        except Exception:
            return 0.0

    # --- data (stock vs crypto endpoints) ---
    def get_candles(self, symbol: str, granularity: str, limit: int = 300):
        import urllib.parse
        tf = self.TF[granularity]
        if self._is_crypto(symbol):
            url = (f"{self.data_base}/v1beta3/crypto/us/bars?"
                   + urllib.parse.urlencode({"symbols": symbol, "timeframe": tf, "limit": limit}))
            bars = self._req(url)["bars"][symbol]
        else:
            url = (f"{self.data_base}/v2/stocks/{symbol}/bars?"
                   + urllib.parse.urlencode({"timeframe": tf, "limit": limit, "feed": "iex"}))
            bars = self._req(url)["bars"]
        df = pd.DataFrame(bars).rename(columns={"o": "open", "h": "high", "l": "low",
                                                "c": "close", "v": "volume"})
        df["date"] = pd.to_datetime(df["t"])
        return df.set_index("date").sort_index()[["open", "high", "low", "close", "volume"]].astype(float)

    # --- orders ---
    def market_buy_bracket(self, symbol: str, qty: float, stop: float, target: float):
        """Stock: one native bracket order. Crypto: market buy (stop/target managed
        by the runner since Alpaca crypto doesn't support bracket orders)."""
        if self._is_crypto(symbol):
            return self._req(f"{self.trade_base}/v2/orders", "POST", {
                "symbol": symbol, "qty": str(qty), "side": "buy",
                "type": "market", "time_in_force": "gtc"})
        return self._req(f"{self.trade_base}/v2/orders", "POST", {
            "symbol": symbol, "qty": str(qty), "side": "buy", "type": "market",
            "time_in_force": "day", "order_class": "bracket",
            "take_profit": {"limit_price": round(target, 2)},
            "stop_loss": {"stop_price": round(stop, 2)}})

    def sell_market(self, symbol: str, qty: float):
        return self._req(f"{self.trade_base}/v2/orders", "POST", {
            "symbol": symbol, "qty": str(qty), "side": "sell",
            "type": "market", "time_in_force": "gtc" if self._is_crypto(symbol) else "day"})


class CoinbaseBroker:
    """Live spot trading via coinbase-advanced-py (`pip install coinbase-advanced-py`).

    NOTE: this path trades real money. Validate it with tiny size before trusting
    it. It refuses to construct without trade-only-capable credentials.
    """

    GRAN_MAP = {"ONE_HOUR": 3600, "ONE_DAY": 86400, "FIFTEEN_MINUTE": 900,
                "FIVE_MINUTE": 300}

    def __init__(self, key_name: str, private_key: str):
        try:
            from coinbase.rest import RESTClient
        except ImportError as e:
            raise RuntimeError(
                "Live mode needs the Coinbase SDK: pip install coinbase-advanced-py"
            ) from e
        self.client = RESTClient(api_key=key_name, api_secret=private_key)

    def cash_usd(self) -> float:
        accts = self.client.get_accounts()["accounts"]
        for a in accts:
            if a["currency"] == "USD":
                return float(a["available_balance"]["value"])
        return 0.0

    def position_qty(self, product: str) -> float:
        base = product.split("-")[0]
        for a in self.client.get_accounts()["accounts"]:
            if a["currency"] == base:
                return float(a["available_balance"]["value"])
        return 0.0

    def get_candles(self, product: str, granularity: str, limit: int = 300) -> pd.DataFrame:
        secs = self.GRAN_MAP[granularity]
        end = int(dt.datetime.now(dt.timezone.utc).timestamp())
        start = end - secs * limit
        resp = self.client.get_candles(product_id=product, start=str(start),
                                       end=str(end), granularity=granularity)
        rows = resp["candles"]
        df = pd.DataFrame(rows)
        for c in ("open", "high", "low", "close", "volume"):
            df[c] = df[c].astype(float)
        df["date"] = pd.to_datetime(df["start"].astype(int), unit="s")
        return df.set_index("date").sort_index()[["open", "high", "low", "close", "volume"]]

    def market_buy(self, product: str, quote_usd: float):
        import uuid
        return self.client.market_order_buy(
            client_order_id=str(uuid.uuid4()), product_id=product,
            quote_size=f"{quote_usd:.2f}")

    def place_bracket_sell(self, product: str, base_qty: float, stop: float, target: float):
        """Stop-loss + take-profit on the held position (managed by the runner)."""
        import uuid
        tp = self.client.limit_order_gtc_sell(
            client_order_id=str(uuid.uuid4()), product_id=product,
            base_size=f"{base_qty}", limit_price=f"{target}")
        sl = self.client.stop_limit_order_gtc_sell(
            client_order_id=str(uuid.uuid4()), product_id=product,
            base_size=f"{base_qty}", stop_price=f"{stop}",
            limit_price=f"{stop * 0.997:.6f}", stop_direction="STOP_DIRECTION_STOP_DOWN")
        return tp, sl
