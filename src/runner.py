import os
import time
import threading
from loguru import logger
from src.core.config import settings
from src.core.store import save_trade
from src.api.binance_client import BinanceClient
from src.strategies import trend_ma, breakout, scalping_rsi
from datetime import datetime

# Simple balance tracker (paper trading)
_balance = settings.paper_balance
_daily_start_balance = settings.paper_balance
_lock = threading.Lock()

STRATEGIES = [
    ("EMA_RSI", trend_ma.check_signal),
    ("Breakout", breakout.check_signal),
    ("Scalping_RSI", scalping_rsi.check_signal),
]

RISK_PCT = 0.01


def get_balance():
    return _balance


def _to_candle_dicts(raw_klines):
    result = []
    for k in raw_klines:
        try:
            result.append({
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        except (IndexError, TypeError, ValueError):
            pass
    return result


def run_strategy(name, signal_fn, candles, symbol):
    global _balance, _daily_start_balance
    try:
        signal = signal_fn(candles)
        if signal not in ("BUY", "SELL"):
            return

        price = candles[-1]["close"]
        if price <= 0:
            return

        with _lock:
            bal = _balance

        risk_amount = bal * RISK_PCT
        stop_distance = price * 0.005
        size = (risk_amount * settings.max_leverage) / stop_distance
        if size <= 0:
            return

        if bal < _daily_start_balance * 0.95:
            logger.warning(f"[{name}] Daily drawdown limit reached")
            return

        logger.info(f"[{name}] Signal: {signal} | price={price:.2f} | size={size:.6f}")

        exit_price = price * (1.003 if signal == "BUY" else 0.997)
        pnl = (exit_price - price) * size if signal == "BUY" else (price - exit_price) * size

        with _lock:
            _balance += pnl

        trade = {
            "symbol": symbol,
            "side": signal,
            "entry": price,
            "exit": exit_price,
            "pnl": round(pnl, 4),
            "strategy": name,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        save_trade(trade)
        logger.info(f"[{name}] Trade saved | pnl={pnl:.4f} | balance={_balance:.2f}")

    except Exception as e:
        logger.error(f"[{name}] Error: {e}")


def tick():
    global _daily_start_balance
    symbol = settings.symbols[0]
    try:
        interval_sec = int(os.environ.get("BOT_INTERVAL", "30"))
    except ValueError:
        interval_sec = 30

    client = BinanceClient()
    logger.info(f"Bot tick loop started | symbol={symbol} | interval={interval_sec}s")

    while True:
        try:
            raw = client.get_klines(symbol, "1m", limit=50)
            if not raw or len(raw) < 25:
                logger.warning("Not enough candles, waiting...")
                time.sleep(interval_sec)
                continue

            candles = _to_candle_dicts(raw)
            if len(candles) < 25:
                logger.warning("Not enough valid candles after parsing")
                time.sleep(interval_sec)
                continue

            threads = []
            for name, fn in STRATEGIES:
                t = threading.Thread(target=run_strategy, args=(name, fn, candles, symbol), daemon=True)
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=10)

            logger.info(f"Tick done | balance={_balance:.2f} USDT")

        except Exception as e:
            logger.error(f"Tick error: {e}")

        time.sleep(interval_sec)


def start():
    logger.info("Starting bot | strategies: EMA_RSI, Breakout, Scalping_RSI")
    t = threading.Thread(target=tick, daemon=True)
    t.start()


def get_engine():
    """Returns a simple object with balance attribute for compatibility."""
    class _FakeEngine:
        @property
        def balance(self):
            return _balance
    return _FakeEngine()
