def check_signal(candles):
    """
    Breakout Strategy:
    Buy when price breaks above the highest high of last 20 candles.
    Sell when price breaks below the lowest low of last 20 candles.
    """
    if len(candles) < 21:
        return None

    recent = candles[-21:-1]
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    current_close = candles[-1]['close']

    highest = max(highs)
    lowest = min(lows)

    if current_close > highest:
        return 'BUY'
    elif current_close < lowest:
        return 'SELL'
    return None
