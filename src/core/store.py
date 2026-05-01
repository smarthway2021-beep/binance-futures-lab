"""
store.py - Persistencia de trades em CSV
"""
import csv
import os
from typing import List
from loguru import logger

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")

HEADERS = ["symbol", "side", "entry", "exit", "size", "pnl", "reason", "closed_at"]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_trade(trade: dict):
    _ensure_dir()
    file_exists = os.path.isfile(TRADES_FILE)
    with open(TRADES_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        if not file_exists:
            writer.writeheader()
        row = {k: trade.get(k, "") for k in HEADERS}
        writer.writerow(row)
    logger.debug(f"Trade salvo: {trade}")


def load_trades() -> List[dict]:
    _ensure_dir()
    if not os.path.isfile(TRADES_FILE):
        return []
    with open(TRADES_FILE, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def clear_trades():
    if os.path.isfile(TRADES_FILE):
        os.remove(TRADES_FILE)
        logger.info("Historico de trades limpo")
