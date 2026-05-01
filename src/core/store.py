import json
import os
from loguru import logger

_TRADES_FILE = "/tmp/trades.json"
_trades_cache = []


def _load_from_disk():
    global _trades_cache
    if os.path.exists(_TRADES_FILE):
        try:
            with open(_TRADES_FILE, "r") as f:
                _trades_cache = json.load(f)
        except Exception as e:
            logger.error("Erro ao carregar trades: {}".format(e))
            _trades_cache = []
    return _trades_cache


def _save_to_disk():
    try:
        with open(_TRADES_FILE, "w") as f:
            json.dump(_trades_cache, f, indent=2, default=str)
    except Exception as e:
        logger.error("Erro ao salvar trades: {}".format(e))


def save_trade(trade_dict: dict):
    """Salva um trade real no cache e no disco."""
    global _trades_cache
    if not _trades_cache:
        _load_from_disk()
    _trades_cache.append(trade_dict)
    _save_to_disk()
    logger.info("[STORE] Trade salvo: {} {} pnl={}".format(
        trade_dict.get("symbol", "-"),
        trade_dict.get("side", "-"),
        trade_dict.get("pnl", "-")
    ))


def get_trades() -> list:
    global _trades_cache
    if not _trades_cache:
        _load_from_disk()
    return list(_trades_cache)


def clear_trades():
    """Limpa todos os trades (reseta historico)."""
    global _trades_cache
    _trades_cache = []
    _save_to_disk()
    logger.info("[STORE] Historico de trades limpo.")
