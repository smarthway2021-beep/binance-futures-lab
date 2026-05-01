"""
risk.py - Gestao de risco e calculo de tamanho de posicao
"""
from loguru import logger


def position_size(
    balance: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
    leverage: int = 1,
) -> float:
    """
    Calcula o tamanho da posicao em unidades do ativo.

    Args:
        balance: Saldo disponivel em USDT
        risk_pct: Fracao do saldo a arriscar (ex: 0.01 = 1%)
        entry_price: Preco de entrada
        stop_price: Preco do stop loss
        leverage: Alavancagem aplicada

    Returns:
        Quantidade do ativo a comprar/vender
    """
    if entry_price <= 0 or stop_price <= 0:
        logger.warning("Precos invalidos para calculo de position size")
        return 0.0

    risk_amount = balance * risk_pct
    price_diff = abs(entry_price - stop_price)

    if price_diff == 0:
        logger.warning("Entry e stop no mesmo preco - impossivel calcular size")
        return 0.0

    size = (risk_amount * leverage) / price_diff
    logger.debug(
        f"Position size: balance={balance} risk={risk_pct} "
        f"entry={entry_price} stop={stop_price} lev={leverage} -> size={size:.6f}"
    )
    return round(size, 6)


def daily_drawdown(starting_balance: float, current_balance: float) -> float:
    """
    Calcula o drawdown diario como fracao do saldo inicial.
    """
    if starting_balance <= 0:
        return 0.0
    return (starting_balance - current_balance) / starting_balance


def should_stop_trading(
    starting_balance: float,
    current_balance: float,
    max_drawdown: float,
) -> bool:
    """
    Retorna True se o drawdown diario excedeu o limite maximo.
    """
    dd = daily_drawdown(starting_balance, current_balance)
    if dd >= max_drawdown:
        logger.warning(
            f"Drawdown diario {dd:.2%} atingiu limite {max_drawdown:.2%} - parando operacoes"
        )
        return True
    return False
