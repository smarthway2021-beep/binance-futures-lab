"""
app.py - Painel Web com FastAPI + Bot em Background Thread
O bot roda automaticamente em loop dentro do proprio web service.
Isto permite rodar 100% no free tier do Render sem precisar de Cron Job.
"""
import os
import time
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
from src.core.store import load_trades
from src.core.config import settings

# Intervalo em segundos entre cada execucao do bot (default 5 min)
BOT_INTERVAL = int(os.getenv("BOT_INTERVAL_SECONDS", "300"))

_bot_status = {
    "running": False,
    "last_tick": None,
    "tick_count": 0,
    "errors": 0,
}


def _bot_loop():
    """Loop do bot rodando em background thread."""
    from src.runner import run_once
    _bot_status["running"] = True
    logger.info(f"Bot background thread iniciada | intervalo={BOT_INTERVAL}s")
    while True:
        try:
            logger.info(f"=== Tick #{_bot_status['tick_count'] + 1} ===")
            run_once()
            _bot_status["tick_count"] += 1
            _bot_status["last_tick"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        except Exception as e:
            _bot_status["errors"] += 1
            logger.error(f"Erro no bot loop: {e}")
        time.sleep(BOT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia background thread quando o servidor sobe."""
    t = threading.Thread(target=_bot_loop, daemon=True)
    t.start()
    logger.info("Background bot thread iniciada com sucesso")
    yield
    logger.info("Servidor encerrando...")


app = FastAPI(title="Binance Futures Lab", version="2.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": settings.app_mode,
        "symbols": settings.symbols,
        "bot_interval_seconds": BOT_INTERVAL,
        "bot_ticks": _bot_status["tick_count"],
        "bot_errors": _bot_status["errors"],
        "last_tick": _bot_status["last_tick"],
    }


@app.get("/api/trades")
def get_trades():
    trades = load_trades()
    return JSONResponse(content={"total": len(trades), "trades": trades})


@app.get("/api/stats")
def get_stats():
    trades = load_trades()
    if not trades:
        return {"total_trades": 0, "total_pnl": 0, "wins": 0, "losses": 0, "win_rate": 0}
    total_pnl = sum(float(t.get("pnl", 0)) for t in trades)
    wins = sum(1 for t in trades if float(t.get("pnl", 0)) > 0)
    losses = len(trades) - wins
    return {
        "total_trades": len(trades),
        "total_pnl": round(total_pnl, 4),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades) * 100, 2),
        "bot_ticks": _bot_status["tick_count"],
        "bot_errors": _bot_status["errors"],
        "last_tick": _bot_status["last_tick"],
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html lang='pt-br'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Binance Futures Lab</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: Arial, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
            h1 { color: #f0b90b; margin-bottom: 20px; font-size: 1.8em; }
            h2 { color: #f0b90b; margin-bottom: 12px; font-size: 1.2em; }
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
            .stats-grid { display: flex; flex-wrap: wrap; gap: 15px; }
            .stat { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 15px 20px; text-align: center; min-width: 120px; }
            .stat .value { font-size: 1.8em; font-weight: bold; color: #f0b90b; }
            .stat .label { font-size: 0.8em; color: #8b949e; margin-top: 4px; }
            .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }
            .badge-green { background: #1a4731; color: #3fb950; }
            .badge-yellow { background: #3d2e00; color: #f0b90b; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }
            th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #21262d; }
            th { color: #8b949e; font-weight: normal; text-transform: uppercase; font-size: 0.75em; }
            .positive { color: #3fb950; font-weight: bold; }
            .negative { color: #f85149; font-weight: bold; }
            button { background: #f0b90b; color: #000; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 0.85em; font-weight: bold; }
            button:hover { background: #d4a017; }
            .status-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
            .dot { width: 10px; height: 10px; border-radius: 50%; background: #3fb950; animation: pulse 2s infinite; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        </style>
    </head>
    <body>
        <h1>Binance Futures Lab</h1>
        <div class='card'>
            <div class='status-bar'>
                <div class='dot'></div>
                <span>Bot rodando em background</span>
                <span id='mode-badge'></span>
            </div>
            <div class='stats-grid' id='stats'>Carregando...</div>
        </div>
        <div class='card'>
            <h2>Trades Recentes <button onclick='loadAll()'>Atualizar</button></h2>
            <table>
                <thead><tr><th>Simbolo</th><th>Lado</th><th>Entry</th><th>Exit</th><th>PnL (USDT)</th><th>Motivo</th><th>Data</th></tr></thead>
                <tbody id='trades-body'><tr><td colspan='7' style='text-align:center;color:#8b949e'>Nenhum trade ainda...</td></tr></tbody>
            </table>
        </div>
        <script>
            async function loadStats() {
                const r = await fetch('/api/stats');
                const d = await r.json();
                document.getElementById('stats').innerHTML = `
                    <div class='stat'><div class='value'>${d.total_trades}</div><div class='label'>Total Trades</div></div>
                    <div class='stat'><div class='value ${d.total_pnl >= 0 ? "positive" : "negative"}'>${(d.total_pnl||0).toFixed(2)}</div><div class='label'>PnL Total</div></div>
                    <div class='stat'><div class='value positive'>${d.wins}</div><div class='label'>Wins</div></div>
                    <div class='stat'><div class='value negative'>${d.losses}</div><div class='label'>Losses</div></div>
                    <div class='stat'><div class='value'>${d.win_rate||0}%</div><div class='label'>Win Rate</div></div>
                    <div class='stat'><div class='value'>${d.bot_ticks||0}</div><div class='label'>Ticks</div></div>
                    <div class='stat'><div class='value ${(d.bot_errors||0) > 0 ? "negative" : "positive"}'>${d.bot_errors||0}</div><div class='label'>Erros</div></div>
                `;
                document.getElementById('mode-badge').innerHTML = `<span class='badge badge-yellow'>${d.last_tick ? 'Ultimo tick: ' + d.last_tick : 'Aguardando 1o tick...'}</span>`;
            }
            async function loadTrades() {
                const r = await fetch('/api/trades');
                const d = await r.json();
                const tbody = document.getElementById('trades-body');
                if (!d.trades || d.trades.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#8b949e">Nenhum trade ainda...</td></tr>';
                    return;
                }
                tbody.innerHTML = d.trades.slice(-30).reverse().map(t => `
                    <tr>
                        <td><strong>${t.symbol}</strong></td>
                        <td><span class='${t.side === "LONG" ? "positive" : "negative"}'>${t.side}</span></td>
                        <td>${parseFloat(t.entry||0).toFixed(4)}</td>
                        <td>${parseFloat(t.exit||0).toFixed(4)}</td>
                        <td class='${parseFloat(t.pnl||0) >= 0 ? "positive" : "negative"}'>${parseFloat(t.pnl||0).toFixed(4)}</td>
                        <td>${t.reason}</td>
                        <td style='font-size:0.8em;color:#8b949e'>${t.closed_at}</td>
                    </tr>
                `).join('');
            }
            async function loadAll() { await loadStats(); await loadTrades(); }
            loadAll();
            setInterval(loadAll, 30000);
        </script>
    </body>
    </html>
    """
