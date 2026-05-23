"""app.py - Dashboard Web do Binance Futures Lab
Endpoints: / dashboard | /api/stats | /api/trades | /api/price | /api/logs
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
import threading
import time
import os
import requests as _requests
from collections import deque

from src.core.config import settings
from src.core.store import get_trades

BASE_URL = os.getenv("BASE_URL", "https://testnet.binancefuture.com")

# Estado global
_bot_status = {
    "running": False,
    "tick_count": 0,
    "last_tick": None,
    "errors": 0,
}

# Buffer circular de logs em memória
_log_buffer = deque(maxlen=200)

def _log_sink(message):
    _log_buffer.append(str(message).strip())

logger.add(_log_sink, format="{time:HH:mm:ss} | {level} | {message}")

def _bot_loop():
    import src.runner as _runner
    _bot_status["running"] = True
    logger.info("Bot background thread iniciada | intervalo={}".format(settings.BOT_INTERVAL))
    _runner.start()
    while True:
        time.sleep(10)
        _bot_status["tick_count"] += 1
        _bot_status["last_tick"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_bot_loop, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse(content=_html_dashboard())

@app.get("/api/stats")
def api_stats():
    trades = get_trades()
    total = len(trades)
    wins = len([t for t in trades if t.pnl > 0])
    losses = len([t for t in trades if t.pnl < 0])
    pnl_total = sum(t.pnl for t in trades)
    win_rate = round(100 * wins / total, 1) if total > 0 else 0
    return JSONResponse({
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "pnl": round(pnl_total, 2),
        "win_rate": win_rate,
        "ticks": _bot_status["tick_count"],
        "errors": _bot_status["errors"],
        "status": "running" if _bot_status["running"] else "stopped",
        "last_tick": _bot_status["last_tick"] or ""
    })

@app.get("/api/trades")
def api_trades():
    trades = get_trades()
    return JSONResponse([{
        "symbol": t.symbol,
        "side": t.side,
        "entry": round(t.entry_price, 2),
        "exit": round(t.exit_price, 2) if t.exit_price else None,
        "pnl": round(t.pnl, 2),
        "reason": t.exit_reason or "",
        "timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for t in trades[-50:]])

@app.get("/api/price")
def api_price(symbol: str = "BTCUSDT"):
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/price?symbol={symbol}"
        r = _requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        return JSONResponse({"symbol": symbol, "price": float(data["price"])})
    except Exception as e:
        logger.error(f"Erro ao buscar preço: {e}")
        return JSONResponse({"symbol": symbol, "price": 0, "error": str(e)})

@app.get("/api/logs")
def api_logs():
    return JSONResponse({"logs": list(_log_buffer)})

def _html_dashboard():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Binance Futures Lab - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #2d3748;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: white;
            border-radius: 12px;
            padding: 20px 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        h1 {
            font-size: 24px;
            color: #2d3748;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .price-banner {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .status-bar {
            background: white;
            border-radius: 12px;
            padding: 15px 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
        }
        .pulse {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #48bb78;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        .card-title {
            font-size: 12px;
            text-transform: uppercase;
            color: #718096;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }
        .card-value {
            font-size: 28px;
            font-weight: 700;
            color: #2d3748;
        }
        .positive { color: #48bb78; }
        .negative { color: #f56565; }
        .section {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .section-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 15px;
            color: #2d3748;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        thead {
            background: #f7fafc;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            font-size: 12px;
            text-transform: uppercase;
            color: #718096;
            font-weight: 600;
        }
        tbody tr:hover {
            background: #f7fafc;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-long { background: #c6f6d5; color: #22543d; }
        .badge-short { background: #fed7d7; color: #742a2a; }
        .logbox {
            background: #1a202c;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 400px;
            overflow-y: auto;
            line-height: 1.6;
        }
        .log-real { color: #90cdf4; }
        .log-trade { color: #9ae6b4; }
        .log-error { color: #fc8181; }
        .log-stats { color: #fbd38d; }
        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            font-size: 14px;
            opacity: 0.9;
        }
        @media (max-width: 768px) {
            .metrics { grid-template-columns: repeat(2, 1fr); }
            header { flex-direction: column; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
                Binance Futures Lab
            </h1>
            <div class="price-banner" id="priceBanner">BTC/USDT: $--,---</div>
        </header>

        <div class="status-bar">
            <div class="status-indicator">
                <div class="pulse"></div>
                <span>Bot Rodando</span>
            </div>
            <div id="lastUpdate" style="color: #718096; font-size: 14px;">Último tick: --</div>
        </div>

        <div class="metrics">
            <div class="card">
                <div class="card-title">Total Trades</div>
                <div class="card-value" id="totalTrades">0</div>
            </div>
            <div class="card">
                <div class="card-title">PnL Total</div>
                <div class="card-value" id="pnlTotal">$0.00</div>
            </div>
            <div class="card">
                <div class="card-title">Wins</div>
                <div class="card-value positive" id="wins">0</div>
            </div>
            <div class="card">
                <div class="card-title">Losses</div>
                <div class="card-value negative" id="losses">0</div>
            </div>
            <div class="card">
                <div class="card-title">Win Rate</div>
                <div class="card-value" id="winRate">0%</div>
            </div>
            <div class="card">
                <div class="card-title">Ticks</div>
                <div class="card-value" id="ticks">0</div>
            </div>
            <div class="card">
                <div class="card-title">Erros</div>
                <div class="card-value" id="errors">0</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📊 Trades Recentes</div>
            <div style="overflow-x: auto;">
                <table id="tradesTable">
                    <thead>
                        <tr>
                            <th>Símbolo</th>
                            <th>Lado</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>PnL</th>
                            <th>Motivo</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody id="tradesBody">
                        <tr><td colspan="7" style="text-align:center; color: #a0aec0;">Aguardando trades...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📝 System Logs</div>
            <div class="logbox" id="logbox">Aguardando logs...</div>
        </div>

        <div class="footer">
            <p>Binance Futures Lab v1.0 | Paper Trading Mode | Desenvolvido com Python + FastAPI</p>
        </div>
    </div>

    <script>
        async function loadPrice() {
            try {
                const r = await fetch('/api/price');
                const d = await r.json();
                if (d.price > 0) {
                    document.getElementById('priceBanner').textContent = 
                        `${d.symbol}: $${d.price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                }
            } catch (e) { console.error('Erro ao buscar preço:', e); }
        }

        async function loadStats() {
            try {
                const r = await fetch('/api/stats');
                const d = await r.json();
                document.getElementById('totalTrades').textContent = d.total_trades;
                document.getElementById('wins').textContent = d.wins;
                document.getElementById('losses').textContent = d.losses;
                document.getElementById('winRate').textContent = d.win_rate + '%';
                document.getElementById('ticks').textContent = d.ticks;
                document.getElementById('errors').textContent = d.errors;
                document.getElementById('lastUpdate').textContent = 'Último tick: ' + (d.last_tick || '--');
                
                const pnl = d.pnl;
                const pnlEl = document.getElementById('pnlTotal');
                pnlEl.textContent = '$' + pnl.toFixed(2);
                pnlEl.className = 'card-value ' + (pnl >= 0 ? 'positive' : 'negative');
            } catch (e) { console.error('Erro ao buscar stats:', e); }
        }

        async function loadTrades() {
            try {
                const r = await fetch('/api/trades');
                const trades = await r.json();
                const tbody = document.getElementById('tradesBody');
                if (!trades || trades.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color: #a0aec0;">Nenhum trade realizado ainda</td></tr>';
                    return;
                }
                tbody.innerHTML = trades.reverse().map(t => {
                    const badgeClass = t.side === 'LONG' ? 'badge-long' : 'badge-short';
                    const pnlClass = t.pnl >= 0 ? 'positive' : 'negative';
                    return `<tr>
                        <td><strong>${t.symbol}</strong></td>
                        <td><span class="badge ${badgeClass}">${t.side}</span></td>
                        <td>$${t.entry.toFixed(2)}</td>
                        <td>${t.exit ? '$' + t.exit.toFixed(2) : '--'}</td>
                        <td class="${pnlClass}"><strong>$${t.pnl.toFixed(2)}</strong></td>
                        <td>${t.reason || '--'}</td>
                        <td style="color: #718096; font-size: 12px;">${t.timestamp}</td>
                    </tr>`;
                }).join('');
            } catch (e) { console.error('Erro ao buscar trades:', e); }
        }

        async function loadLogs() {
            try {
                const r = await fetch('/api/logs');
                const d = await r.json();
                const box = document.getElementById('logbox');
                if (!d.logs || d.logs.length === 0) { 
                    box.textContent = 'Aguardando logs...'; 
                    return; 
                }
                box.innerHTML = d.logs.slice().reverse().map(l => {
                    let cls = '';
                    if (l.includes('[REAL]')) cls = 'real';
                    else if (l.includes('[TRADE]') || l.includes('[SINAL]')) cls = 'trade';
                    else if (l.includes('ERROR') || l.includes('Erro')) cls = 'error';
                    else if (l.includes('[STATS]')) cls = 'stats';
                    return `<div class="log-${cls}">${l.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>`;
                }).join('');
            } catch (e) { console.error('Erro ao buscar logs:', e); }
        }

        async function refresh() {
            await Promise.all([loadPrice(), loadStats(), loadTrades(), loadLogs()]);
        }

        refresh();
        setInterval(refresh, 10000);
    </script>
</body>
</html>
    """
