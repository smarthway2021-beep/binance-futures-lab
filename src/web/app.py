"""
app.py - Dashboard Web do Binance Futures Lab
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

BOT_INTERVAL = int(os.getenv("BOT_INTERVAL", "60"))
BASE_URL = os.getenv("BASE_URL", "https://testnet.binancefuture.com")

_bot_status = {
    "running": False,
    "tick_count": 0,
    "last_tick": None,
    "errors": 0,
}

# Buffer circular de logs em memoria
_log_buffer = deque(maxlen=200)

def _log_sink(message):
    _log_buffer.append(str(message).strip())

logger.add(_log_sink, format="{time:HH:mm:ss} | {level} | {message}")


def _bot_loop():
    import src.runner as _runner
    _bot_status["running"] = True
    logger.info("Bot background thread iniciada | intervalo={}s".format(BOT_INTERVAL))
    _runner.start()
    while True:
        time.sleep(10)
        _bot_status["tick_count"] += 1
        _bot_status["last_tick"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_bot_loop, daemon=True)
    t.start()
    logger.info("Background bot thread iniciada com sucesso")
    yield
    logger.info("Servidor encerrando...")


app = FastAPI(title="Binance Futures Lab", lifespan=lifespan)


@app.get("/api/stats")
def api_stats():
    trades = get_trades()
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) <= 0)
    pnl = sum(t.get("pnl", 0) for t in trades)
    total = len(trades)
    win_rate = round((wins / total * 100) if total > 0 else 0, 1)
    return {
        "running": _bot_status["running"],
        "tick_count": _bot_status["tick_count"],
        "last_tick": _bot_status["last_tick"],
        "errors": _bot_status["errors"],
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "pnl": round(pnl, 2),
        "win_rate": win_rate,
    }


@app.get("/api/trades")
def api_trades():
    return get_trades()[-50:]


@app.get("/api/price")
def api_price():
    """Busca preco real atual do BTC direto da Binance Testnet."""
    try:
        symbol = settings.symbols[0] if settings.symbols else "BTCUSDT"
        url = "{}/fapi/v1/ticker/price?symbol={}".format(BASE_URL, symbol)
        resp = _requests.get(url, timeout=5)
        data = resp.json()
        price = float(data.get("price", 0))
        return {
            "symbol": symbol,
            "price": price,
            "source": "Binance Futures Testnet",
            "url": url,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/logs")
def api_logs():
    """Retorna os ultimos logs do bot em tempo real."""
    return {"logs": list(_log_buffer)[-100:]}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(content=_html_dashboard())


def _html_dashboard():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>Binance Futures Lab</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0d0d0d; color: #f0f0f0; font-family: monospace; }
  .header { background: #111; padding: 20px 30px; border-bottom: 2px solid #f0b90b; }
  .header h1 { color: #f0b90b; font-size: 24px; }
  .header small { color: #888; font-size: 12px; }
  .container { padding: 20px 30px; }
  .price-banner { background: #1a1a1a; border: 1px solid #f0b90b; border-radius: 8px;
    padding: 15px 25px; margin-bottom: 20px; display: flex; align-items: center; gap: 20px; }
  .price-banner .label { color: #888; font-size: 12px; }
  .price-banner .price { color: #00e676; font-size: 32px; font-weight: bold; }
  .price-banner .source { color: #555; font-size: 11px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-bottom: 20px; }
  .card { background: #1a1a1a; border-radius: 8px; padding: 20px; text-align: center; border: 1px solid #222; }
  .card .val { font-size: 28px; font-weight: bold; color: #f0b90b; }
  .card .lbl { font-size: 11px; color: #888; margin-top: 5px; }
  .section { background: #1a1a1a; border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid #222; }
  .section h2 { color: #f0b90b; font-size: 15px; margin-bottom: 15px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: #888; font-weight: normal; padding: 6px 10px; border-bottom: 1px solid #333; }
  td { padding: 8px 10px; border-bottom: 1px solid #1e1e1e; }
  .long { color: #00e676; } .short { color: #f44336; }
  .pnl-pos { color: #00e676; } .pnl-neg { color: #f44336; }
  .log-box { background: #0a0a0a; border-radius: 4px; padding: 12px; max-height: 350px;
    overflow-y: auto; font-size: 11px; line-height: 1.6; color: #aaa; }
  .log-box .real { color: #00e676; } .log-box .trade { color: #f0b90b; }
  .log-box .err { color: #f44336; } .log-box .stats { color: #64b5f6; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .badge-green { background: #1b3d2a; color: #00e676; }
  .status-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 20px;
    background: #1a1a1a; padding: 12px 20px; border-radius: 8px; border: 1px solid #222; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: #00e676;
    animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
</style>
</head>
<body>
<div class="header">
  <h1>Binance Futures Lab</h1>
  <small>Paper Trading | Estrategia EMA 9/21 | Testnet Binance Futures</small>
</div>
<div class="container">

  <div class="price-banner" id="priceBanner">
    <div>
      <div class="label">BTCUSDT - Preco Real Atual</div>
      <div class="price" id="livePrice">Carregando...</div>
      <div class="source" id="priceSource"></div>
    </div>
    <div style="margin-left:auto; text-align:right">
      <div class="label">Fonte</div>
      <div style="color:#f0b90b; font-size:13px">Binance Futures Testnet</div>
      <div class="source" id="priceTime"></div>
    </div>
  </div>

  <div class="status-bar" id="statusBar">
    <div class="dot"></div>
    <span id="botStatus">Bot rodando em background</span>
    <span style="color:#555">|</span>
    <span id="lastTick" style="color:#888; font-size:12px">Aguardando tick...</span>
    <span style="margin-left:auto; color:#555; font-size:11px" id="autoRefresh">Auto-refresh: 30s</span>
  </div>

  <div class="cards" id="cards">
    <div class="card"><div class="val" id="cTrades">-</div><div class="lbl">Total Trades</div></div>
    <div class="card"><div class="val" id="cPnl">-</div><div class="lbl">PnL Total (USDT)</div></div>
    <div class="card"><div class="val" id="cWins">-</div><div class="lbl">Wins</div></div>
    <div class="card"><div class="val" id="cLosses">-</div><div class="lbl">Losses</div></div>
    <div class="card"><div class="val" id="cWR">-</div><div class="lbl">Win Rate</div></div>
    <div class="card"><div class="val" id="cTicks">-</div><div class="lbl">Ticks</div></div>
    <div class="card"><div class="val" id="cErrors">-</div><div class="lbl">Erros</div></div>
  </div>

  <div class="section">
    <h2>Trades Recentes (Paper)</h2>
    <table>
      <thead><tr>
        <th>SIMBOLO</th><th>LADO</th><th>ENTRY</th><th>EXIT</th>
        <th>PNL (USDT)</th><th>MOTIVO</th><th>DATA</th>
      </tr></thead>
      <tbody id="tradesBody"><tr><td colspan="7" style="color:#555">Carregando...</td></tr></tbody>
    </table>
  </div>

  <div class="section">
    <h2>Logs em Tempo Real <span class="badge badge-green">LIVE</span></h2>
    <div class="log-box" id="logBox">Carregando logs...</div>
  </div>

</div>
<script>
async function loadPrice() {
  try {
    const r = await fetch('/api/price');
    const d = await r.json();
    if (d.price) {
      document.getElementById('livePrice').textContent = '$' + d.price.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
      document.getElementById('priceSource').textContent = 'URL: ' + d.url;
      document.getElementById('priceTime').textContent = d.timestamp;
    }
  } catch(e) { document.getElementById('livePrice').textContent = 'Erro ao buscar preco'; }
}

async function loadStats() {
  const r = await fetch('/api/stats');
  const d = await r.json();
  document.getElementById('cTrades').textContent = d.total_trades;
  const pnl = d.pnl;
  const pnlEl = document.getElementById('cPnl');
  pnlEl.textContent = (pnl >= 0 ? '+' : '') + pnl.toFixed(2);
  pnlEl.className = 'val ' + (pnl >= 0 ? 'pnl-pos' : 'pnl-neg');
  document.getElementById('cWins').textContent = d.wins;
  document.getElementById('cLosses').textContent = d.losses;
  document.getElementById('cWR').textContent = d.win_rate + '%';
  document.getElementById('cTicks').textContent = d.tick_count;
  document.getElementById('cErrors').textContent = d.errors;
  if (d.last_tick) document.getElementById('lastTick').textContent = 'Ultimo tick: ' + d.last_tick;
}

async function loadTrades() {
  const r = await fetch('/api/trades');
  const trades = await r.json();
  const tbody = document.getElementById('tradesBody');
  if (!trades.length) { tbody.innerHTML = '<tr><td colspan="7" style="color:#555">Nenhum trade ainda</td></tr>'; return; }
  tbody.innerHTML = trades.slice().reverse().map(t => {
    const pnl = t.pnl || 0;
    return '<tr>' +
      '<td><b>' + (t.symbol||'-') + '</b></td>' +
      '<td class="' + (t.side==='LONG'?'long':'short') + '">' + (t.side||'-') + '</td>' +
      '<td>' + parseFloat(t.entry||0).toFixed(4) + '</td>' +
      '<td>' + parseFloat(t.exit||0).toFixed(4) + '</td>' +
      '<td class="' + (pnl>=0?'pnl-pos':'pnl-neg') + '">' + (pnl>=0?'+':'') + parseFloat(pnl).toFixed(4) + '</td>' +
      '<td>' + (t.reason||'-') + '</td>' +
      '<td style="font-size:11px; color:#666">' + (t.closed_at||'-') + '</td>' +
    '</tr>';
  }).join('');
}

async function loadLogs() {
  const r = await fetch('/api/logs');
  const d = await r.json();
  const box = document.getElementById('logBox');
  if (!d.logs || !d.logs.length) { box.textContent = 'Aguardando logs...'; return; }
  box.innerHTML = d.logs.slice().reverse().map(l => {
    let cls = '';
    if (l.includes('[REAL]')) cls = 'real';
    else if (l.includes('[TRADE') || l.includes('[SINAL]')) cls = 'trade';
    else if (l.includes('ERROR') || l.includes('Erro')) cls = 'err';
    else if (l.includes('[STATS]')) cls = 'stats';
    return '<div class="' + cls + '">' + l.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div>';
  }).join('');
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
