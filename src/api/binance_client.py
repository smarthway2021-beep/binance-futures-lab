"""
binance_client.py - Cliente REST para Binance USDM Futures
Suporta testnet e producao via configuracao
"""
import hashlib
import hmac
import time
from typing import List, Optional
import requests
from loguru import logger
from src.core.config import settings


class BinanceClient:
    def __init__(self):
        self.base_url = settings.base_url
        self.api_key = settings.api_key
        self.api_secret = settings.api_secret
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        sig = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = sig
        return params

    def _get(self, path: str, params: dict = None, signed: bool = False) -> dict:
        if params is None:
            params = {}
        if signed:
            params = self._sign(params)
        url = f"{self.base_url}{path}"
        try:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"GET {path} erro: {e}")
            return {}

    def _post(self, path: str, params: dict = None) -> dict:
        if params is None:
            params = {}
        params = self._sign(params)
        url = f"{self.base_url}{path}"
        try:
            r = self.session.post(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"POST {path} erro: {e}")
            return {}

    def ping(self) -> bool:
        result = self._get("/fapi/v1/ping")
        return result == {}

    def get_server_time(self) -> int:
        data = self._get("/fapi/v1/time")
        return data.get("serverTime", 0)

    def get_exchange_info(self) -> dict:
        return self._get("/fapi/v1/exchangeInfo")

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[list]:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        data = self._get("/fapi/v1/klines", params)
        if isinstance(data, list):
            return data
        return []

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        data = self._get("/fapi/v1/ticker/price", {"symbol": symbol})
        try:
            return float(data["price"])
        except Exception:
            return None

    def get_account(self) -> dict:
        return self._get("/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if price:
            params["price"] = price
            params["timeInForce"] = time_in_force
        if stop_price:
            params["stopPrice"] = stop_price
        return self._post("/fapi/v1/order", params)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        params = {"symbol": symbol, "orderId": order_id}
        params = self._sign(params)
        url = f"{self.base_url}/fapi/v1/order"
        try:
            r = self.session.delete(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"DELETE order erro: {e}")
            return {}

    def get_open_positions(self) -> List[dict]:
        data = self._get("/fapi/v2/positionRisk", signed=True)
        if isinstance(data, list):
            return [p for p in data if float(p.get("positionAmt", 0)) != 0]
        return []


client = BinanceClient()
