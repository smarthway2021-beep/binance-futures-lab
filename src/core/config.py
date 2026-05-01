"""
config.py - Configuracoes centrais do bot
Le variaveis de ambiente do arquivo .env
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.app_mode = os.getenv("APP_MODE", "paper")
        self.api_key = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_API_SECRET", "")
        self.base_url = os.getenv("BASE_URL", "https://demo-fapi.binance.com")
        self.ws_base_url = os.getenv("WS_BASE_URL", "wss://fstream.binancefuture.com")
        self.symbols_raw = os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT")
        self.interval = os.getenv("INTERVAL", "5m")
        self.risk_per_trade = float(os.getenv("RISK_PER_TRADE", "0.01"))
        self.max_daily_drawdown = float(os.getenv("MAX_DAILY_DRAWDOWN", "0.05"))
        self.max_leverage = int(os.getenv("MAX_LEVERAGE", "5"))
        self.paper_balance = float(os.getenv("PAPER_BALANCE", "10000.0"))
        self.web_host = os.getenv("WEB_HOST", "0.0.0.0")
        self.web_port = int(os.getenv("WEB_PORT", "8000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    @property
    def symbols(self) -> List[str]:
        return [s.strip() for s in self.symbols_raw.split(",") if s.strip()]

    @property
    def is_paper(self) -> bool:
        return self.app_mode == "paper"

    @property
    def is_testnet(self) -> bool:
        return self.app_mode == "testnet"

    @property
    def is_live(self) -> bool:
        return self.app_mode == "live"


settings = Settings()
