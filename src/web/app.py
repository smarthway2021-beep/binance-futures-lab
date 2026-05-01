"""
app.py - Painel Web com FastAPI
Expoe endpoints para monitorar o bot em tempo real
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from src.core.store import load_trades
from src.core.config import settings
import os

app = FastAPI(title="Binance Futures Lab", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "mode": settings.app_mode, "symbols": settings.symbols}


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
            body { font-family: Arial, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
            h1 { color: #f0b90b; }
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 10px 0; }
            .stat { display: inline-block; margin: 10px 20px; text-align: center; }
            .stat .value { font-size: 2em; font-weight: bold; color: #f0b90b; }
            .stat .label { font-size: 0.9em; color: #8b949e; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #30363d; }
            th { color: #f0b90b; }
            .positive { color: #3fb950; }
            .negative { color: #f85149; }
            button { background: #f0b90b; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 1em; }
        </style>
    </head>
    <body>
        <h1>Binance Futures Lab - Painel</h1>
        <div class='card'>
            <h2>Status</h2>
            <div id='stats'>Carregando...</div>
        </div>
        <div class='card'>
            <h2>Trades Recentes <button onclick='loadTrades()'>Atualizar</button></h2>
            <table id='trades-table'>
                <thead><tr><th>Simbolo</th><th>Lado</th><th>Entry</th><th>Exit</th><th>PnL</th><th>Motivo</th><th>Data</th></tr></thead>
                <tbody id='trades-body'></tbody>
            </table>
        </div>
        <script>
            async function loadStats() {
                const r = await fetch('/api/stats');
                const d = await r.json();
                document.getElementById('stats').innerHTML = `
                    <div class='stat'><div class='value'>${d.total_trades}</div><div class='label'>Total Trades</div></div>
                    <div class='stat'><div class='value ${d.total_pnl >= 0 ? "positive" : "negative"}'>${d.total_pnl.toFixed(2)}</div><div class='label'>PnL Total (USDT)</div></div>
                    <div class='stat'><div class='value positive'>${d.wins}</div><div class='label'>Wins</div></div>
                    <div class='stat'><div class='value negative'>${d.losses}</div><div class='label'>Losses</div></div>
                    <div class='stat'><div class='value'>${d.win_rate}%</div><div class='label'>Win Rate</div></div>
                `;
            }
            async function loadTrades() {
                const r = await fetch('/api/trades');
                const d = await r.json();
                const tbody = document.getElementById('trades-body');
                tbody.innerHTML = d.trades.slice(-20).reverse().map(t => `
                    <tr>
                        <td>${t.symbol}</td>
                        <td>${t.side}</td>
                        <td>${parseFloat(t.entry).toFixed(4)}</td>
                        <td>${parseFloat(t.exit).toFixed(4)}</td>
                        <td class='${parseFloat(t.pnl) >= 0 ? "positive" : "negative"}'>${parseFloat(t.pnl).toFixed(4)}</td>
                        <td>${t.reason}</td>
                        <td>${t.closed_at}</td>
                    </tr>
                `).join('');
            }
            loadStats();
            loadTrades();
            setInterval(() => { loadStats(); loadTrades(); }, 30000);
        </script>
    </body>
    </html>
    """
