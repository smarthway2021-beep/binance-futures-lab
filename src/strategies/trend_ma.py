"""
tend_ma.py - Estrategia de Medias Moveis (sem pandas)
Usa apenas listas Python puras para calcular EMA/SMA
"""
from loguru import logger


def _sma(values, period):
    """Simple Moving Average usando lista pura."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema(values, period):
    """Exponential Moving Average usando lista pura."""
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for price in values[period:]:
        ema = price * k + ema * (1 - k)
    return ema


def analyze(klines):
    """
    Recebe lista de klines da Binance e retorna sinal ou None.
    Cada kline: [open_time, open, high, low, close, volume, ...]
    Retorna: {"side": "LONG"|"SHORT", "entry": float, "stop": float, "tp": float}
    """
    if not klines or len(klines) < 50:
        return None

    closes = [float(k[4]) for k in klines]

    fast = _ema(closes, 9)
    slow = _ema(closes, 21)
    prev_fast = _ema(closes[:-1], 9)
    prev_slow = _ema(closes[:-1], 21)

    if None in (fast, slow, prev_fast, prev_slow):
        return None

    current_price = closes[-1]
    atr_period = 14
    highs = [float(k[2]) for k in klines[-atr_period:]]
    lows = [float(k[3]) for k in klines[-atr_period:]]
    atr = sum(h - l for h, l in zip(highs, lows)) / atr_period

    # Cruzamento LONG: fast cruzou acima de slow
    if prev_fast <= prev_slow and fast > slow:
        entry = current_price
        stop = entry - (atr * 1.5)
        tp = entry + (atr * 3.0)
        logger.info("SINAL LONG | entry={:.4f} stop={:.4f} tp={:.4f}".format(entry, stop, tp))
        return {"side": "LONG", "entry": entry, "stop": stop, "tp": tp}

    # Cruzamento SHORT: fast cruzou abaixo de slow
    if prev_fast >= prev_slow and fast < slow:
        entry = current_price
        stop = entry + (atr * 1.5)
        tp = entry - (atr * 3.0)
        logger.info("SINAL SHORT | entry={:.4f} stop={:.4f} tp={:.4f}".format(entry, stop, tp))
        return {"side": "SHORT", "entry": entry, "stop": stop, "tp": tp}

    return None
