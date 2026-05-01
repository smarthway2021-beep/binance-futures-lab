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


def check_signal(candles):
    """
    EMA 9/21 + RSI strategy.
    BUY when fast EMA > slow EMA and RSI < 70.
    SELL when fast EMA < slow EMA and RSI > 30.
    """
    if len(candles) < 25:
        return None

    closes = [c['close'] for c in candles]
    current_price = closes[-1]

    ema_fast = _ema(closes, 9)
    ema_slow = _ema(closes, 21)
    rsi = _rsi(closes)

    if ema_fast is None or ema_slow is None:
        return None

    diff_pct = abs(ema_fast - ema_slow) / ema_slow * 100

    if ema_fast > ema_slow and rsi < 70:
        logger.info(f"EMA_RSI BUY | price={current_price:.2f} rsi={rsi:.1f} diff={diff_pct:.3f}%")
        return 'BUY'
    if ema_fast < ema_slow and rsi > 30:
        logger.info(f"EMA_RSI SELL | price={current_price:.2f} rsi={rsi:.1f} diff={diff_pct:.3f}%")
        return 'SELL'
    return None
