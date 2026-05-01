"""
paper_engine.py - Motor de simulacao de ordens (paper trading)
"""
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


class Position:
    def __init__(self, symbol: str, side: str, entry_price: float, size: float, stop: float, tp: float):
        self.symbol = symbol
        self.side = side  # LONG ou SHORT
        self.entry_price = entry_price
        self.size = size
        self.stop = stop
        self.tp = tp
        self.opened_at = datetime.utcnow()
        self.pnl = 0.0

    def update_pnl(self, current_price: float):
        if self.side == "LONG":
            self.pnl = (current_price - self.entry_price) * self.size
        else:
            self.pnl = (self.entry_price - current_price) * self.size

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": self.entry_price,
            "size": self.size,
            "stop": self.stop,
            "tp": self.tp,
            "pnl": round(self.pnl, 4),
            "opened_at": self.opened_at.isoformat(),
        }


class Trade:
    def __init__(self, symbol: str, side: str, entry: float, exit_price: float,
                 size: float, pnl: float, reason: str):
        self.symbol = symbol
        self.side = side
        self.entry = entry
        self.exit_price = exit_price
        self.size = size
        self.pnl = pnl
        self.reason = reason
        self.closed_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry": self.entry,
            "exit": self.exit_price,
            "size": self.size,
            "pnl": round(self.pnl, 4),
            "reason": self.reason,
            "closed_at": self.closed_at.isoformat(),
        }


class PaperEngine:
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []

    def open_position(self, symbol: str, side: str, entry_price: float,
                      size: float, stop: float, tp: float) -> bool:
        if symbol in self.positions:
            logger.warning(f"Posicao ja aberta para {symbol}")
            return False
        cost = entry_price * size
        if cost > self.balance:
            logger.warning(f"Saldo insuficiente para abrir posicao em {symbol}")
            return False
        self.positions[symbol] = Position(symbol, side, entry_price, size, stop, tp)
        logger.info(f"[PAPER] ABRIU {side} {symbol} @ {entry_price} size={size} stop={stop} tp={tp}")
        return True

    def check_exits(self, symbol: str, current_price: float):
        if symbol not in self.positions:
            return
        pos = self.positions[symbol]
        pos.update_pnl(current_price)
        reason = None
        if pos.side == "LONG":
            if current_price <= pos.stop:
                reason = "STOP"
            elif current_price >= pos.tp:
                reason = "TP"
        else:
            if current_price >= pos.stop:
                reason = "STOP"
            elif current_price <= pos.tp:
                reason = "TP"
        if reason:
            self._close_position(symbol, current_price, reason)

    def _close_position(self, symbol: str, exit_price: float, reason: str):
        pos = self.positions.pop(symbol)
        pos.update_pnl(exit_price)
        self.balance += pos.pnl
        trade = Trade(symbol, pos.side, pos.entry_price, exit_price, pos.size, pos.pnl, reason)
        self.trades.append(trade)
        logger.info(f"[PAPER] FECHOU {pos.side} {symbol} @ {exit_price} PnL={pos.pnl:.4f} [{reason}]")

    def get_stats(self) -> dict:
        total_pnl = sum(t.pnl for t in self.trades)
        wins = sum(1 for t in self.trades if t.pnl > 0)
        losses = sum(1 for t in self.trades if t.pnl <= 0)
        return {
            "balance": round(self.balance, 2),
            "initial_balance": self.initial_balance,
            "total_pnl": round(total_pnl, 4),
            "total_trades": len(self.trades),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(self.trades) * 100, 2) if self.trades else 0,
            "open_positions": len(self.positions),
        }
