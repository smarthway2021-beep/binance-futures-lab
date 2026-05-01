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

# Estado global do engine (em producao use DB ou cache)
_engine = PaperEngine(initial_balance=settings.paper_balance)
_daily_start_balance = settings.paper_balance


def run_once():
    global _engine, _daily_start_balance

    logger.info(f"=== Runner tick | modo={settings.app_mode} simbolos={settings.symbols} ===")

        # DEMO: Criar trade sintético para validar dashboard
    if not hasattr(run_once, "_first_run_done"):        logger.info("[DEMO] Criando trade sint
            run_once._first_run_done = Trueético de teste...")
        from src.core.store import save_trade
        from datetime import datetime
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
        logger.info("[DEMO] Trade sintético criado com sucesso!")


    # Checar drawdown diario
    if should_stop_trading(_daily_start_balance, _engine.balance, settings.max_daily_drawdown):
        logger.warning("Drawdown diario atingido - pulando este tick")
        return

    client = BinanceClient()

    for symbol in settings.symbols:
        try:
            # Buscar candles
            klines = client.get_klines(symbol, settings.interval, limit=100)
            if not klines:
                logger.warning(f"Sem candles para {symbol}")
                continue

            # Preco atual
            current_price = float(klines[-1][4])

            # Checar saidas de posicoes abertas
            _engine.check_exits(symbol, current_price)

            # Gerar sinal
            signal = analyze(klines)
            if signal is None:
                logger.debug(f"{symbol}: sem sinal")
                continue

            # Calcular tamanho da posicao
            size = position_size(
                balance=_engine.balance,
                risk_pct=settings.risk_per_trade,
                entry_price=signal["entry"],
                stop_price=signal["stop"],
                leverage=settings.max_leverage,
            )
            if size <= 0:
                logger.warning(f"{symbol}: size calculado zerado, pulando")
                continue

            # Abrir posicao no paper engine
            opened = _engine.open_position(
                symbol=symbol,
                side=signal["side"],
                entry_price=signal["entry"],
                size=size,
                stop=signal["stop"],
                tp=signal["tp"],
            )

            if opened:
                logger.info(f"[OK] Posicao aberta: {symbol} {signal['side']} @ {signal['entry']}")

        except Exception as e:
            logger.error(f"Erro processando {symbol}: {e}")

    # Salvar trades fechados neste tick
    for trade in _engine.trades[-10:]:
        save_trade(trade.to_dict())

    stats = _engine.get_stats()
    logger.info(f"Stats: {stats}")


if __name__ == "__main__":
    run_once()
