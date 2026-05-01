"""
trend_ma.py - Estrategia de Tendencia com Medias Moveis

Logica:
  - MA rapida cruza acima da MA lenta -> sinal LONG
  - MA rapida cruza abaixo da MA lenta -> sinal SHORT
  - Stop: ATR * multiplicador abaixo/acima do entry
  - TP: risk/reward 2:1
"""
from typing import List, Optional, Tuple
import pandas as pd
from loguru import logger

# Parametros default da estrategia
MA_FAST = 9
MA_SLOW = 21
ATR_PERIOD = 14
ATR_MULT = 1.5
RR_RATIO = 2.0  # risk/reward


def compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 0.0
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
    atr = sum(tr_list[-period:]) / period
    return atr


def analyze(
    klines: List[list],
    ma_fast: int = MA_FAST,
    ma_slow: int = MA_SLOW,
    atr_period: int = ATR_PERIOD,
    atr_mult: float = ATR_MULT,
    rr_ratio: float = RR_RATIO,
) -> Optional[dict]:
    """
    Analisa candles e retorna sinal de entrada ou None.

    Args:
        klines: Lista de candles [open_time, open, high, low, close, volume, ...]

    Returns:
        dict com {side, entry, stop, tp} ou None
    """
    if len(klines) < ma_slow + atr_period + 2:
        logger.debug("Candles insuficientes para analise")
        return None

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]

    # Calcular MAs
    ma_f_prev = sum(closes[-(ma_fast + 1):-1]) / ma_fast
    ma_f_curr = sum(closes[-ma_fast:]) / ma_fast
    ma_s_prev = sum(closes[-(ma_slow + 1):-1]) / ma_slow
    ma_s_curr = sum(closes[-ma_slow:]) / ma_slow

    # ATR para stop
    atr = compute_atr(highs, lows, closes, atr_period)
    if atr == 0:
        return None

    entry = closes[-1]
    side = None

    # Crossover LONG
    if ma_f_prev <= ma_s_prev and ma_f_curr > ma_s_curr:
        side = "LONG"
        stop = entry - atr * atr_mult
        tp = entry + (entry - stop) * rr_ratio

    # Crossover SHORT
    elif ma_f_prev >= ma_s_prev and ma_f_curr < ma_s_curr:
        side = "SHORT"
        stop = entry + atr * atr_mult
        tp = entry - (stop - entry) * rr_ratio

    if side is None:
        return None

    signal = {
        "side": side,
        "entry": round(entry, 6),
        "stop": round(stop, 6),
        "tp": round(tp, 6),
        "atr": round(atr, 6),
        "ma_fast": round(ma_f_curr, 6),
        "ma_slow": round(ma_s_curr, 6),
    }
    logger.info(f"SINAL {side} | entry={entry:.4f} stop={stop:.4f} tp={tp:.4f} atr={atr:.4f}")
    return signal
