import requests
from bs4 import BeautifulSoup
import re
from typing import Dict
from datetime import datetime

class StockChecker:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
    
    def check_stock(self, product_url: str, product_id: str, retailer: str) -> Dict:
        retailer_lower = retailer.lower()
        if retailer_lower == "asos":
            return self._scrape_asos(product_url, product_id)
        elif retailer_lower == "vinted":
            return self._scrape_vinted(product_url)
        else:
            return self._scrape_generic(product_url)
    
    def _scrape_asos(self, product_url: str, product_id: str) -> Dict:
        try:
            response = requests.get(product_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return self._error_response("Failed to fetch")
            html = response.text.lower()
            if "out of stock" in html:
                return {"status": "out_of_stock", "level": 0, "text": "Out of stock", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
            if "low stock" in html or "selling fast" in html:
                return {"status": "low_stock", "level": None, "text": "Low stock", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
            return {"status": "in_stock", "level": None, "text": "In stock", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
        except Exception as e:
            return self._error_response(str(e))
    
    def _scrape_vinted(self, product_url: str) -> Dict:
        try:
            response = requests.get(product_url, headers=self.headers, timeout=10)
            html = response.text.lower()
            if "sold" in html:
                return {"status": "out_of_stock", "level": 0, "text": "Sold", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
            return {"status": "in_stock", "level": 1, "text": "Available", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
        except Exception as e:
            return self._error_response(str(e))
    
    def _scrape_generic(self, product_url: str) -> Dict:
        try:
            response = requests.get(product_url, headers=self.headers, timeout=10)
            html = response.text.lower()
            if "out of stock" in html or "sold out" in html:
                return {"status": "out_of_stock", "level": 0, "text": "Out of stock", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
            if "low stock" in html or "selling fast" in html:
                return {"status": "low_stock", "level": None, "text": "Low stock", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
            return {"status": "in_stock", "level": None, "text": "In stock", "timestamp": datetime.utcnow().isoformat(), "method": "scrape"}
        except Exception as e:
            return self._error_response(str(e))
    
    def _error_response(self, error: str) -> Dict:
        return {"status": "unknown", "level": None, "text": f"Error: {error}", "timestamp": datetime.utcnow().isoformat(), "method": "error"}

def get_stock_checker():
    return StockChecker()
