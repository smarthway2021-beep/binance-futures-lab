"""
runner.py - Loop principal do bot
Roda a estrategia de Medias Moveis no testnet da Binance Futures
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

    # Checar drawdown diario
    if should_stop_trading(_daily_start_balance, _engine.balance, settings.max_daily_drawdown):
        logger.warning("Drawdown diario atingido - pulando este tick")
        return

    client = BinanceClient()
    for symbol in settings.symbols:
        try:
            # Buscar candles reais do testnet Binance
            klines = client.get_klines(symbol, settings.interval, limit=100)
            if not klines:
                logger.warning("Sem candles para {}".format(symbol))
                continue

            # Preco real atual do mercado
            current_price = float(klines[-1][4])
            logger.info("[REAL] {} preco atual = ${:.2f} (fonte: Binance Testnet)".format(symbol, current_price))

            # Checar saidas de posicoes abertas
            _engine.check_exits(symbol, current_price)

            # Gerar sinal via estrategia EMA 9/21
            signal = analyze(klines)
            if signal is None:
                logger.info("{}: sem sinal de entrada neste tick".format(symbol))
                continue

            logger.info("[SINAL] {} {} | entry={:.2f} stop={:.2f} tp={:.2f}".format(
                symbol, signal["side"], signal["entry"], signal["stop"], signal["tp"]))

            # Calcular tamanho da posicao
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

            # Abrir posicao no paper engine (simulado com preco real)
            opened = _engine.open_position(
                symbol=symbol,
                side=signal["side"],
                entry_price=signal["entry"],
                size=size,
                stop=signal["stop"],
                tp=signal["tp"],
            )
            if opened:
                logger.info("[TRADE ABERTO] {} {} @ {:.2f} | size={:.4f}".format(
                    symbol, signal["side"], signal["entry"], size))

        except Exception as e:
            logger.error("Erro processando {}: {}".format(symbol, e))
            import traceback
            logger.error(traceback.format_exc())

    # Salvar trades fechados
    for trade in _engine.trades[-10:]:
        save_trade(trade.to_dict())

    stats = _engine.get_stats()
    logger.info("[STATS] balance={:.2f} trades={} wins={} pnl={:.2f}".format(
        _engine.balance, stats.get("total_trades", 0),
        stats.get("wins", 0), stats.get("pnl", 0.0)))
