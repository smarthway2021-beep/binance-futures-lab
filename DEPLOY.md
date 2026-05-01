# 🚀 Guia de Deploy - Binance Futures Lab

## ✅ O Que Foi Implementado

Bot de trading automatizado para Binance Futures com:

### 📊 Funcionalidades
- **Dados REAIS da Binance API** via WebSocket
- **5 Estratégias de Trading:**
  1. Média Móvel (MA Crossover)
  2. RSI (Relative Strength Index)
  3. Breakout (Rompimento de níveis)
  4. Tendência (Trend Following)
  5. Scalping RSI (operações rápidas)
- **Análise a cada 10 segundos** (não 60s)
- **Multi-símbolos:** BTC, ETH, SOL
- **Gestão de Risco:** Stop loss, take profit, trailing stop
- **Paper Trading:** Simula trades SEM capital real
- **Logs completos** de todas as operações

### 🏗️ Arquitetura
```
src/
├── runner.py          # Executor principal
├── core/
│   ├── config.py      # Configurações
│   └── binance_client.py  # Cliente Binance
├── api/
│   └── binance_client.py  # API REST + WebSocket
├── strategies/
│   ├── trend_ma.py    # Médias móveis
│   ├── breakout.py    # Rompimentos
│   └── scalping_rsi.py  # Scalping
└── store/
    └── save_trade.py  # Armazena trades
```

---

## 🔧 Como Fazer Deploy

### Opção 1: Render (RECOMENDADO)

**Custo:** $7/mês para Background Worker

#### Passo a Passo:

1. **Acesse:** https://dashboard.render.com
2. **Clique:** New → Background Worker
3. **Conecte:** Selecione o repositório `binance-futures-lab`
4. **Configure:**
   - **Name:** binance-futures-lab
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python src/runner.py`

5. **⚠️ IMPORTANTE - Adicione as Variáveis de Ambiente:**

```bash
# APIs da Binance (VOCÊ DEVE FORNECER AS SUAS)
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_SECRET_KEY=sua_secret_key_aqui

# Modo de operação
APP_MODE=paper  # Manter como 'paper' para não fazer trades reais

# URLs (Produção - para dados REAIS)
BASE_URL=https://fapi.binance.com
WS_BASE_URL=wss://fstream.binance.com

# Símbolos
SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT

# Intervalo
INTERVAL=5m

# Gestão de Risco
RISK_PER_TRADE=0.01
MAX_DAILY_DRAWDOWN=0.05
MAX_LEVERAGE=5

# Paper Trading
PAPER_BALANCE=10000.0

# Logs
LOG_LEVEL=INFO
```

6. **Deploy:** Clique em "Deploy Background Worker"

---

### Opção 2: Railway

1. Acesse: https://railway.app
2. New Project → Deploy from GitHub
3. Selecione: binance-futures-lab
4. Configure as mesmas variáveis acima

---

### Opção 3: PythonAnywhere (Limitado)

⚠️ **NÃO recomendado** - plano free não tem always-on tasks

---

## 🔑 Como Obter as APIs da Binance

### Para DADOS REAIS (sem trading):

1. Acesse: https://www.binance.com/en/my/settings/api-management
2. Crie uma **Nova API Key**
3. **Permissões:**
   - ✅ Enable Reading (LEITURA APENAS)
   - ❌ Enable Spot & Margin Trading (DESABILITADO)
   - ❌ Enable Futures (DESABILITADO)
4. Copie:
   - API Key
   - Secret Key
5. **Restrições de IP:** Configure seu IP ou deixe irrestrito (menos seguro)

---

## 📊 Como Verificar Se Está Funcionando

### Logs no Render:
1. Dashboard → binance-futures-lab → Logs
2. Você verá:
```
✅ WebSocket conectado: BTCUSDT
📊 Preço BTCUSDT: 65432.10 USDT
🎯 Sinal: RSI - COMPRA em ETHUSDT @ 3245.67
📈 Trade simulado: +2.5% de lucro
```

### Verificar Trades:
- Os trades ficam salvos em `paper_trades.json`
- No futuro: painel web para visualizar

---

## ⚠️ SEGURANÇA

**NUNCA:**
- ❌ Commitar arquivo `.env` no GitHub
- ❌ Compartilhar suas API Keys
- ❌ Dar permissão de TRADING nas APIs se for só ver dados

**SEMPRE:**
- ✅ Usar variáveis de ambiente na plataforma de deploy
- ✅ Manter `APP_MODE=paper` para não fazer trades reais
- ✅ Revogar APIs antigas quando criar novas

---

## 📈 Próximos Passos

- [ ] Painel web para visualizar trades em tempo real
- [ ] Backtesting com dados históricos
- [ ] Mais estratégias (MACD, Bollinger Bands)
- [ ] Notificações (Telegram, Discord)
- [ ] Modo LIVE trading (com muito cuidado!)

---

## 🆘 Problemas Comuns

**"API Key inválida"**
- Verifique se copiou corretamente
- Confirme que a API tem permissão de leitura

**"WebSocket desconectado"**
- Normal, reconecta automaticamente

**"Nenhum trade executado"**
- Estratégias são conservadoras
- Pode levar tempo até encontrar um sinal

---

**Criado por:** CEO MARCOS  
**Data:** 01/05/2026  
**Status:** ✅ Pronto para deploy com dados REAIS da Binance
