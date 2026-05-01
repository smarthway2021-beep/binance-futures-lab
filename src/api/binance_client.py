"""
binance_client.py - Cliente HTTP para Binance Futures Testnet
URL base configuravel via variavel de ambiente BASE_URL
"""
import os
import time
import hmac
import hashlib
import requests
from loguru import logger

# URL base do testnet - sempre usa a var de ambiente
BASE_URL = os.getenv("BASE_URL", "https://testnet.binancefuture.com")
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

logger.info("BinanceClient inicializado | BASE_URL={}".format(BASE_URL))


class BinanceClient:

    def __init__(self):
        self.base_url = BASE_URL
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/json"
        })

    def _sign(self, params: dict) -> dict:
        query = "&".join(["{}={}".format(k, v) for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _get(self, path: str, params: dict = None, signed: bool = False):
        url = self.base_url + path
        params = params or {}
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params = self._sign(params)
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("GET {} erro: {}".format(path, e))
            return None

    def _post(self, path: str, params: dict = None):
        url = self.base_url + path
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params = self._sign(params)
        try:
            resp = self.session.post(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("POST {} erro: {}".format(path, e))
            return None

    def get_klines(self, symbol: str, interval: str, limit: int = 100):
        """Busca candles (klines) do mercado."""
        logger.info("[API] get_klines {} {} limit={} | url={}/fapi/v1/klines".format(
            symbol, interval, limit, self.base_url))
        data = self._get("/fapi/v1/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
        if data:
            logger.info("[API] {} candles recebidos para {} (ultimo close=${:.2f})".format(
                len(data), symbol, float(data[-1][4])))
        return data

    def get_price(self, symbol: str) -> float:
        """Busca preco atual de um simbolo."""
        data = self._get("/fapi/v1/ticker/price", {"symbol": symbol})
        if data:
            return float(data.get("price", 0))
        return 0.0

    def get_account(self):
        """Busca saldo da conta testnet."""
        return self._get("/fapi/v2/account", signed=True)

    def place_order(self, symbol: str, side: str, quantity: float,
                    order_type: str = "MARKET"):
        """Envia ordem de mercado."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        logger.info("[ORDER] {} {} qty={} @ {}".format(symbol, side, quantity, order_type))
        return self._post("/fapi/v1/order", params)
