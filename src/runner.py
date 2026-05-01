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
_open_positions = {}  # symbol -> trade info
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
    """Arredonda quantidade para o step size da Binance."""
    factor = 1.0 / step
    return math.floor(qty * factor) / factor


def _set_leverage(client, symbol):
    try:
        params = {"symbol": symbol, "leverage": settings.max_leverage}
        params["timestamp"] = int(time.time() * 1000)
        params = client._sign(params)
        client.session.post(
            client.base_url + "/fapi/v1/leverage",
            params=params, timeout=5
        )
        logger.info(f"Leverage configurado: {settings.max_leverage}x para {symbol}")
    except Exception as e:
        logger.warning(f"Nao foi possivel configurar leverage: {e}")


def _get_position(client, symbol):
    """Busca posicao aberta real na Binance."""
    try:
        data = client._get("/fapi/v2/positionRisk", {"symbol": symbol}, signed=True)
        if data and isinstance(data, list):
            for p in data:
                if p.get("symbol") == symbol:
                    amt = float(p.get("positionAmt", 0))
                    entry = float(p.get("entryPrice", 0))
                    pnl = float(p.get("unRealizedProfit", 0))
                    return {"qty": amt, "entry": entry, "unrealized_pnl": pnl}
    except Exception as e:
        logger.error(f"Erro ao buscar posicao: {e}")
    return None


def _close_position(client, symbol, qty):
    """Fecha posicao real na Binance."""
    if qty == 0:
        return None
    side = "SELL" if qty > 0 else "BUY"
    try:
        result = client.place_order(symbol, side, abs(qty))
        logger.info(f"Posicao fechada: {symbol} {side} qty={abs(qty)} | result={result}")
        return result
    except Exception as e:
        logger.error(f"Erro ao fechar posicao: {e}")
        return None


def _monitor_position(client, symbol, entry_price, side, size, strategy_name):
    """Monitora posicao aberta e fecha por TP ou SL."""
    sl_price = entry_price * (1 - SL_PCT) if side == "BUY" else entry_price * (1 + SL_PCT)
    tp_price = entry_price * (1 + TP_PCT) if side == "BUY" else entry_price * (1 - TP_PCT)
    logger.info(f"[{strategy_name}] Monitorando | entry={entry_price:.2f} SL={sl_price:.2f} TP={tp_price:.2f}")

    max_wait = 300  # max 5 minutos monitorando
    start = time.time()

    while time.time() - start < max_wait:
        try:
            pos = _get_position(client, symbol)
            if pos is None or abs(pos["qty"]) < 0.001:
                logger.info(f"[{strategy_name}] Posicao ja fechada pela Binance")
                break

            current_price = client.get_price(symbol)
            hit_tp = (side == "BUY" and current_price >= tp_price) or (side == "SELL" and current_price <= tp_price)
            hit_sl = (side == "BUY" and current_price <= sl_price) or (side == "SELL" and current_price >= sl_price)

            if hit_tp or hit_sl:
                reason = "TP" if hit_tp else "SL"
                logger.info(f"[{strategy_name}] {reason} atingido @ {current_price:.2f}")
                _close_position(client, symbol, pos["qty"])
                time.sleep(1)

                # Busca PnL real da posicao fechada
                real_pnl = pos["unrealized_pnl"]
                try:
                    income = client._get("/fapi/v1/income", {
                        "symbol": symbol,
                        "incomeType": "REALIZED_PNL",
                        "limit": 1
                    }, signed=True)
                    if income and isinstance(income, list) and len(income) > 0:
                        real_pnl = float(income[0].get("income", real_pnl))
                except Exception as ex:
                    logger.warning(f"Nao conseguiu PnL real, usando estimado: {ex}")

                trade = {
                    "symbol": symbol,
                    "side": side,
                    "entry": entry_price,
                    "exit": current_price,
                    "pnl": round(real_pnl, 4),
                    "strategy": strategy_name,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "REAL_TESTNET"
                }
                save_trade(trade)

                global _balance
                with _lock:
                    _balance += real_pnl

                logger.info(f"[{strategy_name}] Trade REAL registrado | pnl={real_pnl:.4f} | balance={_balance:.2f}")
                break

        except Exception as e:
            logger.error(f"[{strategy_name}] Erro monitoramento: {e}")

        time.sleep(3)


def run_strategy(name, signal_fn, candles, symbol, client):
    global _balance, _daily_start_balance

    # Nao abre nova posicao se ja tem uma aberta neste simbolo
    with _lock:
        if symbol in _open_positions:
            return

    try:
        signal = signal_fn(candles)
        if signal not in ("BUY", "SELL"):
            return

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

        logger.info(f"[{name}] Abrindo ordem REAL: {signal} {symbol} qty={size} @ {price:.2f}")

        # Configura alavancagem e abre ordem real
        _set_leverage(client, symbol)
        result = client.place_order(symbol, signal, size)

        if not result or result.get("status") not in ("FILLED", "NEW", "PARTIALLY_FILLED"):
            logger.error(f"[{name}] Ordem nao aceita: {result}")
            return

        fill_price = float(result.get("avgPrice", price) or price)
        logger.info(f"[{name}] Ordem REAL aberta | orderId={result.get('orderId')} avgPrice={fill_price}")

        with _lock:
            _open_positions[symbol] = {"strategy": name, "side": signal, "entry": fill_price}

        # Monitora em thread separada
        t = threading.Thread(
            target=_monitor_and_release,
            args=(client, symbol, fill_price, signal, size, name),
            daemon=True
        )
        t.start()

    except Exception as e:
        logger.error(f"[{name}] Erro em run_strategy: {e}")
        with _lock:
            _open_positions.pop(symbol, None)


def _monitor_and_release(client, symbol, entry_price, side, size, strategy_name):
    """Monitora posicao e libera o lock apos fechar."""
    try:
        _monitor_position(client, symbol, entry_price, side, size, strategy_name)
    finally:
        with _lock:
            _open_positions.pop(symbol, None)


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
        logger.info("[INIT] Historico de trades falsos limpo. Iniciando com dados REAIS.")
        _initialized = True

    logger.info(f"Bot REAL iniciado | symbol={symbol} | interval={interval_sec}s | testnet=TRUE")

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

            logger.info(f"Tick | balance={_balance:.2f} USDT | posicoes abertas={list(_open_positions.keys())}")

        except Exception as e:
            logger.error(f"Tick error: {e}")

        time.sleep(interval_sec)


def start():
    logger.info("Iniciando bot com ORDENS REAIS na Binance Testnet")
    t = threading.Thread(target=tick, daemon=True)
    t.start()


def get_engine():
    class _Engine:
        @property
        def balance(self):
            return _balance
    return _Engine()
