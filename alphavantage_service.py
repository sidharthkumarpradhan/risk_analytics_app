import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_analytics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlphaVantageService:
    """Service for fetching data from AlphaVantage API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ALPHAVANTAGE_API_KEY', 'ERBZK88O5KLSPYPL')
        self.base_url = 'https://www.alphavantage.co/query'
        
        logger.info(f"Initializing AlphaVantage service with API key: {self.api_key[:8]}...")
        
        if not self.api_key:
            logger.warning("No AlphaVantage API key provided - using default key")
        
    def get_daily_prices(self, symbol: str, output_size: str = 'full') -> List[Dict]:
        """Fetch daily price data from AlphaVantage"""
        logger.info(f"Fetching daily prices for {symbol} with output_size={output_size}")
        
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': output_size,
            'apikey': self.api_key
        }
        
        try:
            logger.debug(f"Making API request to {self.base_url}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'Error Message' in data:
                logger.error(f"AlphaVantage API Error for {symbol}: {data['Error Message']}")
                raise ValueError(f"AlphaVantage API Error: {data['Error Message']}")
            
            if 'Note' in data:
                logger.warning(f"AlphaVantage API rate limit hit for {symbol}")
                raise ValueError("AlphaVantage API rate limit reached. Please try again later.")
            
            if 'Time Series (Daily)' not in data:
                logger.error(f"Invalid response format for {symbol} - no time series data")
                raise ValueError("Invalid response format or no data available")
            
            time_series = data['Time Series (Daily)']
            prices = []
            
            for date_str, price_data in time_series.items():
                prices.append({
                    'date': datetime.strptime(date_str, '%Y-%m-%d'),
                    'open': float(price_data['1. open']),
                    'high': float(price_data['2. high']),
                    'low': float(price_data['3. low']),
                    'close': float(price_data['4. close']),
                    'volume': int(price_data['5. volume'])
                })
            
            # Sort by date ascending
            prices.sort(key=lambda x: x['date'])
            logger.info(f"Successfully fetched {len(prices)} price records for {symbol}")
            return prices
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to AlphaVantage API: {str(e)}")
        except ValueError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected error fetching data: {str(e)}")
    
    def get_recent_prices(self, symbol: str, days: int = 780) -> List[Dict]:
        """Get recent price data for specified number of days"""
        prices = self.get_daily_prices(symbol, 'full')
        
        if not prices:
            return []
        
        # Filter to recent data
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_prices = [p for p in prices if p['date'] >= cutoff_date]
        
        return recent_prices
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists in AlphaVantage"""
        try:
            prices = self.get_daily_prices(symbol, 'compact')
            return len(prices) > 0
        except:
            return False