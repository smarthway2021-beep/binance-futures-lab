import os
import time
import threading
import math
from loguru import logger
from src.core.config import settings
from src.core.store import save_trade, clear_trades
from src.api.binance_client import BinanceClient
from src.strategies import trend_ma, breakout, scalping_rsi
from datetime import datetime

_lock = threading.Lock()
_balance = settings.paper_balance
_daily_start_balance = settings.paper_balance
_initialized = False

STRATEGIES = [
    ("EMA_RSI", trend_ma.check_signal),
    ("Breakout", breakout.check_signal),
    ("Scalping_RSI", scalping_rsi.check_signal),
]

RISK_PCT = 0.01   # 1% do saldo por trade
SL_PCT = 0.005    # 0.5% stop loss
TP_PCT = 0.010    # 1.0% take profit


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


def _round_qty(qty, step=0.001):
    factor = 1.0 / step
    return math.floor(qty * factor) / factor


def run_strategy(name, signal_fn, candles, symbol, client):
    global _balance, _daily_start_balance
    
    try:
        signal = signal_fn(candles)
        if signal not in ("BUY", "SELL"):
            return

        # Busca pre\u00e7o REAL da Binance API de produ\u00e7\u00e3o
        price = client.get_price(symbol)
        if price <= 0:
            return

        risk_amount = _balance * RISK_PCT
        stop_distance = price * SL_PCT
        size = _round_qty((risk_amount * settings.max_leverage) / stop_distance)
        if size <= 0:
            logger.warning(f"[{name}] Tamanho invalido: {size}")
            return

        if _balance < _daily_start_balance * 0.95:
            logger.warning(f"[{name}] Drawdown diario atingido")
            return

        logger.info(f"[{name}] Sinal SIMULADO: {signal} {symbol} qty={size} @ {price:.2f} (pre\u00e7o REAL)")

        # SIMULA\u00c7\u00c3O: calcula exit e PnL baseado em TP/SL
        sl_price = price * (1 - SL_PCT) if signal == "BUY" else price * (1 + SL_PCT)
        tp_price = price * (1 + TP_PCT) if signal == "BUY" else price * (1 - TP_PCT)
        
        # Simula que atingiu TP (vamos assumir sempre TP para simplificar)
        exit_price = tp_price
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
            "reason": "TP",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "SIMULADO_PRECOS_REAIS"
        }
        save_trade(trade)
        logger.info(f"[{name}] Trade SIMULADO registrado | pnl={pnl:.4f} | balance={_balance:.2f}")

    except Exception as e:
        logger.error(f"[{name}] Erro em run_strategy: {e}")


def tick():
    global _daily_start_balance, _initialized
    symbol = settings.symbols[0]
    try:
        interval_sec = int(os.environ.get("BOT_INTERVAL", "30"))
    except ValueError:
        interval_sec = 30

    client = BinanceClient()

    if not _initialized:
        clear_trades()
        logger.info("[INIT] Historico limpo. Iniciando com DADOS REAIS da Binance (API de produ\u00e7\u00e3o).")
        _initialized = True

    logger.info(f"Bot SIMULADO iniciado | API REAL | symbol={symbol} | interval={interval_sec}s")

    while True:
        try:
            raw = client.get_klines(symbol, "1m", limit=50)
            if not raw or len(raw) < 25:
                logger.warning("Candles insuficientes")
                time.sleep(interval_sec)
                continue

            candles = _to_candle_dicts(raw)
            if len(candles) < 25:
                time.sleep(interval_sec)
                continue

            threads = []
            for name, fn in STRATEGIES:
                t = threading.Thread(target=run_strategy, args=(name, fn, candles, symbol, client), daemon=True)
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=10)

            logger.info(f"Tick | balance={_balance:.2f} USDT")

        except Exception as e:
            logger.error(f"Tick error: {e}")

        time.sleep(interval_sec)


def start():
    logger.info("Iniciando bot SIMULADO com pre\u00e7os REAIS da Binance API de produ\u00e7\u00e3o")
    t = threading.Thread(target=tick, daemon=True)
    t.start()


def get_engine():
    class _Engine:
        @property
        def balance(self):
            return _balance
    return _Engine()
