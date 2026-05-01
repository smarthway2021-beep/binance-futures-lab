"""
trend_ma.py - Estrategia Multi-Sinal: EMA crossover + RSI + Price Action
Gera sinais mais frequentes para validacao do sistema
"""
from loguru import logger


def _ema(values, period):
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for price in values[period:]:
        ema = price * k + ema * (1 - k)
    return ema


def _rsi(values, period=14):
    if len(values) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = values[-i] - values[-i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze(klines):
    """
    Estrategia combinada: EMA 9/21 crossover + RSI confirmacao
    Retorna sinal ou None
    """
    if not klines or len(klines) < 30:
        return None

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]

    ema_fast = _ema(closes, 9)
    ema_slow = _ema(closes, 21)
    ema_fast_prev = _ema(closes[:-1], 9)
    ema_slow_prev = _ema(closes[:-1], 21)

    if None in (ema_fast, ema_slow, ema_fast_prev, ema_slow_prev):
        return None

    rsi = _rsi(closes)
    current_price = closes[-1]

    # ATR para stop/tp
    atr_period = 10
    atr = sum(highs[-atr_period:][i] - lows[-atr_period:][i]
              for i in range(atr_period)) / atr_period
    if atr == 0:
        atr = current_price * 0.005

    diff_pct = abs(ema_fast - ema_slow) / ema_slow * 100

    # LONG: EMA fast acima de slow + RSI nao sobrecomprado
    if ema_fast > ema_slow and rsi < 70:
        entry = current_price
        stop = entry - (atr * 1.5)
        tp = entry + (atr * 2.5)
        logger.info("SINAL LONG | entry={:.2f} stop={:.2f} tp={:.2f} rsi={:.1f} diff={:.3f}%".format(
            entry, stop, tp, rsi, diff_pct))
        return {"side": "LONG", "entry": entry, "stop": stop, "tp": tp}

    # SHORT: EMA fast abaixo de slow + RSI nao sobrevendido
    if ema_fast < ema_slow and rsi > 30:
        entry = current_price
        stop = entry + (atr * 1.5)
        tp = entry - (atr * 2.5)
        logger.info("SINAL SHORT | entry={:.2f} stop={:.2f} tp={:.2f} rsi={:.1f} diff={:.3f}%".format(
            entry, stop, tp, rsi, diff_pct))
        return {"side": "SHORT", "entry": entry, "stop": stop, "tp": tp}

    logger.info("Sem sinal | ema_fast={:.2f} ema_slow={:.2f} rsi={:.1f}".format(
        ema_fast, ema_slow, rsi))
    return None
