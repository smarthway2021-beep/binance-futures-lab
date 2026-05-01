def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = closes[-period - 1 + i] - closes[-period - 2 + i]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def check_signal(candles):
    """
    Scalping RSI Strategy:
    BUY when RSI crosses below 30 (oversold).
    SELL when RSI crosses above 70 (overbought).
    """
    if len(candles) < 20:
        return None

    closes = [c['close'] for c in candles]
    rsi = calc_rsi(closes)
    if rsi is None:
        return None

    if rsi < 30:
        return 'BUY'
    elif rsi > 70:
        return 'SELL'
    return None
