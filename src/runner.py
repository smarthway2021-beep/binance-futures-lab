"""
runner.py - Loop principal do bot
Roda a estrategia para todos os simbolos configurados
"""
from loguru import logger
from src.core.config import settings
from src.core.risk import position_size, should_stop_trading
from src.core.paper_engine import PaperEngine
from src.core.store import save_trade
from src.api.binance_client import BinanceClient
from src.strategies.trend_ma import analyze
from datetime import datetime

# Estado global do engine
_engine = PaperEngine(initial_balance=settings.paper_balance)
_daily_start_balance = settings.paper_balance


def run_once():
    global _engine, _daily_start_balance
    logger.info("=== Runner tick | modo={} simbolos={} ===".format(settings.app_mode, settings.symbols))

    # DEMO: Criar trade sintetico no primeiro tick para validar dashboard
    if not hasattr(run_once, "_first_run_done"):
        run_once._first_run_done = True
        logger.info("[DEMO] Criando trade sintetico de teste...")
        demo_trade = {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry": 95000.0,
            "exit": 96500.0,
            "size": 0.01,
            "pnl": 15.0,
            "reason": "TP",
            "closed_at": datetime.now().isoformat()
        }
        save_trade(demo_trade)
        logger.info("[DEMO] Trade sintetico criado com sucesso!")

    # Checar drawdown diario
    if should_stop_trading(_daily_start_balance, _engine.balance, settings.max_daily_drawdown):
        logger.warning("Drawdown diario atingido - pulando este tick")
        return

    client = BinanceClient()
    for symbol in settings.symbols:
        try:
            klines = client.get_klines(symbol, settings.interval, limit=100)
            if not klines:
                logger.warning("Sem candles para {}".format(symbol))
                continue
            current_price = float(klines[-1][4])
            _engine.check_exits(symbol, current_price)
            signal = analyze(klines)
            if signal is None:
                logger.debug("{}: sem sinal".format(symbol))
                continue
            size = position_size(
                balance=_engine.balance,
                risk_pct=settings.risk_per_trade,
                entry_price=signal["entry"],
                stop_price=signal["stop"],
                leverage=settings.max_leverage,
            )
            if size <= 0:
                logger.warning("{}: size calculado zerado, pulando".format(symbol))
                continue
            opened = _engine.open_position(
                symbol=symbol,
                side=signal["side"],
                entry_price=signal["entry"],
                size=size,
                stop=signal["stop"],
                tp=signal["tp"],
            )
            if opened:
                logger.info("[OK] Posicao aberta: {} {} @ {}".format(symbol, signal["side"], signal["entry"]))
        except Exception as e:
            logger.error("Erro processando {}: {}".format(symbol, e))

    for trade in _engine.trades[-10:]:
        save_trade(trade.to_dict())
    stats = _engine.get_stats()
    logger.info("Stats: {}".format(stats))
