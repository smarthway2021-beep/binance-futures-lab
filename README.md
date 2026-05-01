# Binance Futures Lab

> Laboratorio quantitativo para paper trading e automacao em **Binance USDM Futures**
> Estrategias automatizadas, gestao de risco e painel web — 100% online via GitHub + Render

---

## Estrutura do Projeto

```
binance-futures-lab/
├── src/
│   ├── api/
│   │   └── binance_client.py   # Cliente REST Binance Futures
│   ├── core/
│   │   ├── config.py           # Configuracoes via .env
│   │   ├── paper_engine.py     # Motor de paper trading
│   │   ├── risk.py             # Gestao de risco e position sizing
│   │   └── store.py            # Persistencia de trades em CSV
│   ├── strategies/
│   │   └── trend_ma.py         # Estrategia: Tendencia com MAs + ATR
│   ├── web/
│   │   └── app.py              # Painel web FastAPI
│   └── runner.py               # Loop principal do bot
├── .env.example                # Modelo de variaveis de ambiente
├── requirements.txt            # Dependencias Python
├── render.yaml                 # Blueprint de deploy no Render
└── .github/workflows/ci.yml   # CI com GitHub Actions
```

---

## Modos de Operacao

| Modo | Descricao |
|------|----------|
| `paper` | Simulacao 100% local, sem enviar ordens reais |
| `testnet` | Envia ordens para Binance Futures Testnet |
| `live` | PRODUCAO - usar apenas apos validacao completa |

---

## Como Configurar

### 1. Clonar o repositorio
```bash
git clone https://github.com/smarthway2021-beep/binance-futures-lab.git
cd binance-futures-lab
```

### 2. Criar o arquivo .env
```bash
cp .env.example .env
# Edite o .env com suas configuracoes
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Rodar localmente
```bash
# Iniciar painel web
uvicorn src.web.app:app --reload

# Rodar o bot uma vez
python -m src.runner
```

---

## Deploy no Render (online 24/7)

1. Acesse [render.com](https://render.com) e conecte este repositorio GitHub
2. Clique em **New Blueprint** e selecione o `render.yaml`
3. Configure as variaveis de ambiente (API keys, modo, simbolos)
4. O Render cria automaticamente:
   - **Web Service**: painel FastAPI acessivel pela web
   - **Cron Job**: runner executando a cada 5 minutos

---

## Endpoints do Painel

| Endpoint | Descricao |
|----------|----------|
| `GET /` | Dashboard visual com stats e trades |
| `GET /health` | Status do servico e modo de operacao |
| `GET /api/trades` | Lista todos os trades em JSON |
| `GET /api/stats` | Estatisticas: PnL, win rate, drawdown |

---

## Estrategia: Trend MA

- **MA Rapida (9)** cruza acima da **MA Lenta (21)** -> LONG
- **MA Rapida (9)** cruza abaixo da **MA Lenta (21)** -> SHORT
- **Stop Loss**: ATR(14) x 1.5 abaixo/acima do entry
- **Take Profit**: Risk/Reward 2:1

---

## Gestao de Risco

- Risco por trade: 1% do saldo (configuravel)
- Drawdown diario maximo: 5% (para operacoes se atingido)
- Alavancagem maxima: 5x (configuravel)
- Position sizing automatico baseado em distancia do stop

---

## Roadmap

- [x] Paper trading engine
- [x] Cliente REST Binance Futures
- [x] Estrategia Trend MA com ATR
- [x] Painel web FastAPI
- [x] Deploy Render com cron job
- [ ] WebSocket market stream em tempo real
- [ ] User data stream (ordens e posicoes ao vivo)
- [ ] Estrategia de scalping/sniper entries
- [ ] Banco de dados SQLite para historico
- [ ] Alertas por Telegram/Discord
- [ ] Backtesting engine
- [ ] Modo testnet com API key real

---

## Aviso de Risco

Este projeto e um laboratorio educacional. Nao use em producao sem validacao extensiva.
Trading de futuros envolve alto risco de perda de capital.
Sempre valide em paper trading e testnet antes de qualquer operacao real.

---

MIT License - smarthway2021-beep
