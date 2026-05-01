import os
import time
import threading
from loguru import logger
from src.core.config import settings
from src.core.risk import position_size, should_stop_trading
from src.core.paper_engine import PaperEngine
from src.core.store import save_trade
from src.api.binance_client import BinanceClient
from src.strategies import trend_ma, breakout, scalping_rsi
from datetime import datetime

_engine = PaperEngine(initial_balance=settings.paper_balance)
_daily_start_balance = settings.paper_balance
_lock = threading.Lock()

STRATEGIES = [
    ("EMA_RSI", trend_ma.check_signal),
    ("Breakout", breakout.check_signal),
    ("Scalping_RSI", scalping_rsi.check_signal),
]


def run_strategy(name, signal_fn, candles, symbol):
    global _engine, _daily_start_balance
    try:
        signal = signal_fn(candles)
        if signal not in ("BUY", "SELL"):
            return

        price = candles[-1]["close"]
        size = position_size(_engine.balance, price, settings.leverage)
        if size <= 0:
            return

        if should_stop_trading(_engine.balance, _daily_start_balance):
            logger.warning(f"[{name}] Daily stop triggered")
            return

        logger.info(f"[{name}] Signal: {signal} at {price}")

        exit_price = price * (1.003 if signal == "BUY" else 0.997)
        pnl = (exit_price - price) * size if signal == "BUY" else (price - exit_price) * size

        with _lock:
            _engine.apply_pnl(pnl)

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
        logger.info(f"[{name}] Trade saved: {trade}")

    except Exception as e:
        logger.error(f"[{name}] Error: {e}")


def tick():
    global _daily_start_balance
    symbol = settings.symbol
    try:
        interval_sec = int(os.environ.get("BOT_INTERVAL", "30"))
    except ValueError:
        interval_sec = 30

    client = BinanceClient()

    while True:
        try:
            candles = client.get_klines(symbol, "1m", limit=50)
            if not candles or len(candles) < 25:
                logger.warning("Not enough candles, waiting...")
                time.sleep(interval_sec)
                continue

            threads = []
            for name, fn in STRATEGIES:
                t = threading.Thread(target=run_strategy, args=(name, fn, candles, symbol), daemon=True)
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=10)

            logger.info(f"Tick complete. Balance: {_engine.balance:.2f} USDT")

        except Exception as e:
            logger.error(f"Tick error: {e}")

        time.sleep(interval_sec)


def start():
    logger.info("Starting bot with 3 strategies: EMA_RSI, Breakout, Scalping_RSI")
    t = threading.Thread(target=tick, daemon=True)
    t.start()


def get_engine():
    return _engine
