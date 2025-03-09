"""Data collector module for fetching financial news and price data.

This module provides functions to collect financial news articles from NewsAPI
and price data for Bitcoin and S&P 500 from Yahoo Finance.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from newsapi import NewsApiClient
import yfinance as yf
import pandas as pd

from . import config
from .database import db_client

logger = logging.getLogger(__name__)

class DataCollector:
    """Class for collecting financial data from various sources."""
    
    def __init__(self):
        """Initialize the data collector with API clients."""
        self.news_api = NewsApiClient(api_key=config.NEWS_API_KEY)
        logger.info("Data collector initialized")
    
    def collect_bitcoin_news(self) -> List[Dict[str, Any]]:
        """Collect Bitcoin news articles from NewsAPI.
        
        Returns:
            List of news articles
        """
        try:
            logger.info("Collecting Bitcoin news articles")
            
            # Get news from the last 24 hours (NewsAPI free tier limitation)
            response = self.news_api.get_everything(
                q=config.BITCOIN_QUERY,
                language='en',
                sort_by='publishedAt',
                page_size=100,  # Maximum allowed by NewsAPI
                from_param=(datetime.utcnow() - timedelta(days=1)).date().isoformat()
            )
            
            articles = response.get('articles', [])
            logger.info(f"Collected {len(articles)} Bitcoin news articles")
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to collect Bitcoin news: {str(e)}")
            return []
    
    def collect_global_economy_news(self) -> List[Dict[str, Any]]:
        """Collect global economy news articles from NewsAPI.
        
        Returns:
            List of news articles
        """
        try:
            logger.info("Collecting global economy news articles")
            
            # Get news from the last 24 hours (NewsAPI free tier limitation)
            response = self.news_api.get_everything(
                q=config.GLOBAL_ECONOMY_QUERY,
                language='en',
                sort_by='publishedAt',
                page_size=100,  # Maximum allowed by NewsAPI
                from_param=(datetime.utcnow() - timedelta(days=1)).date().isoformat()
            )
            
            articles = response.get('articles', [])
            logger.info(f"Collected {len(articles)} global economy news articles")
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to collect global economy news: {str(e)}")
            return []
    
    def collect_bitcoin_price(self) -> Optional[Dict[str, Any]]:
        """Collect Bitcoin price data from Yahoo Finance.
        
        Returns:
            Bitcoin price data or None if collection fails
        """
        try:
            logger.info("Collecting Bitcoin price data")
            
            # Get Bitcoin-USD data
            btc = yf.Ticker("BTC-USD")
            # Get more detailed price history with datetime index
            hist = btc.history(period="1d", interval="1h")
            
            if hist.empty:
                logger.warning("No Bitcoin price data available")
                return None
            
            # Get the latest price data
            latest = hist.iloc[-1]
            # Get the datetime index for the latest price
            latest_datetime = hist.index[-1].to_pydatetime()
            
            price_data = {
                "symbol": "BTC-USD",
                "timestamp": latest_datetime,  # Use the actual price timestamp
                "collection_time": datetime.utcnow(),  # When we collected it
                "price": latest["Close"],
                "open": latest["Open"],
                "high": latest["High"],
                "low": latest["Low"],
                "volume": latest["Volume"],
                "raw_data": latest.to_dict()
            }
            
            logger.info(f"Collected Bitcoin price: ${price_data['price']:.2f} from {latest_datetime}")
            
            return price_data
            
        except Exception as e:
            logger.error(f"Failed to collect Bitcoin price data: {str(e)}")
            return None
    
    def collect_sp500_price(self) -> Optional[Dict[str, Any]]:
        """Collect S&P 500 index price data from Yahoo Finance.
        
        Returns:
            S&P 500 price data or None if collection fails
        """
        try:
            logger.info("Collecting S&P 500 price data")
            
            # Get S&P 500 data
            sp500 = yf.Ticker("^GSPC")
            # Get more detailed price history with datetime index
            hist = sp500.history(period="1d", interval="1h")
            
            if hist.empty:
                logger.warning("No S&P 500 price data available")
                return None
            
            # Get the latest price data
            latest = hist.iloc[-1]
            # Get the datetime index for the latest price
            latest_datetime = hist.index[-1].to_pydatetime()
            
            price_data = {
                "symbol": "^GSPC",
                "timestamp": latest_datetime,  # Use the actual price timestamp
                "collection_time": datetime.utcnow(),  # When we collected it
                "price": latest["Close"],
                "open": latest["Open"],
                "high": latest["High"],
                "low": latest["Low"],
                "volume": latest["Volume"],
                "raw_data": latest.to_dict()
            }
            
            logger.info(f"Collected S&P 500 price: ${price_data['price']:.2f} from {latest_datetime}")
            
            return price_data
            
        except Exception as e:
            logger.error(f"Failed to collect S&P 500 price data: {str(e)}")
            return None
    
    def collect_and_store_all_data(self) -> Tuple[int, int, bool, bool]:
        """Collect and store all financial data.
        
        This method collects both news articles and price data in a single execution.
        It is designed to be run every 3 hours via crontab to ensure regular data collection.
        Even if one type of data collection fails, it will still attempt to collect the others.
        
        Returns:
            Tuple of (bitcoin_articles_count, global_economy_articles_count, 
                      bitcoin_price_stored, sp500_price_stored)
        """
        logger.info(f"Starting 3-hour data collection cycle at {datetime.now()}")
        
        # Track collection status and results
        collection_results = {
            "bitcoin_articles": 0,
            "global_economy_articles": 0,
            "bitcoin_price": False,
            "sp500_price": False
        }
        
        # 1. Collect and store Bitcoin news
        try:
            logger.info("--- COLLECTING BITCOIN NEWS ---")
            bitcoin_articles = self.collect_bitcoin_news()
            collection_results["bitcoin_articles"] = db_client.insert_articles(
                config.BITCOIN_ARTICLES_COLLECTION, bitcoin_articles
            )
        except Exception as e:
            logger.error(f"Bitcoin news collection failed: {str(e)}", exc_info=True)
        
        # 2. Collect and store global economy news
        try:
            logger.info("--- COLLECTING GLOBAL ECONOMY NEWS ---")
            global_economy_articles = self.collect_global_economy_news()
            collection_results["global_economy_articles"] = db_client.insert_articles(
                config.GLOBAL_ECONOMY_ARTICLES_COLLECTION, global_economy_articles
            )
        except Exception as e:
            logger.error(f"Global economy news collection failed: {str(e)}", exc_info=True)
        
        # 3. Collect and store Bitcoin price
        try:
            logger.info("--- COLLECTING BITCOIN PRICE ---")
            bitcoin_price = self.collect_bitcoin_price()
            if bitcoin_price:
                collection_results["bitcoin_price"] = db_client.insert_price_data(
                    config.BITCOIN_PRICE_COLLECTION, bitcoin_price
                )
        except Exception as e:
            logger.error(f"Bitcoin price collection failed: {str(e)}", exc_info=True)
        
        # 4. Collect and store S&P 500 price
        try:
            logger.info("--- COLLECTING S&P 500 PRICE ---")
            sp500_price = self.collect_sp500_price()
            if sp500_price:
                collection_results["sp500_price"] = db_client.insert_price_data(
                    config.SP500_COLLECTION, sp500_price
                )
        except Exception as e:
            logger.error(f"S&P 500 price collection failed: {str(e)}", exc_info=True)
        
        # Log summary of collection results
        logger.info("=== DATA COLLECTION SUMMARY ===")
        logger.info(f"- Bitcoin articles: {collection_results['bitcoin_articles']} collected")
        logger.info(f"- Global economy articles: {collection_results['global_economy_articles']} collected")
        logger.info(f"- Bitcoin price: {'Collected and stored' if collection_results['bitcoin_price'] else 'Failed'}")
        logger.info(f"- S&P 500 price: {'Collected and stored' if collection_results['sp500_price'] else 'Failed'}")
        logger.info(f"Next collection scheduled in 3 hours")
        
        return (
            collection_results["bitcoin_articles"],
            collection_results["global_economy_articles"],
            collection_results["bitcoin_price"],
            collection_results["sp500_price"]
        )

def run_collector():
    """Run the data collector once."""
    collector = DataCollector()
    result = collector.collect_and_store_all_data()
    
    logger.info(f"Data collection complete: "
                f"Bitcoin articles: {result[0]}, "
                f"Global economy articles: {result[1]}, "
                f"Bitcoin price: {'Stored' if result[2] else 'Failed'}, "
                f"S&P 500 price: {'Stored' if result[3] else 'Failed'}")

def run_collector_scheduled():
    """Run the data collector on a schedule."""
    interval_seconds = config.DATA_COLLECTION_INTERVAL_HOURS * 3600
    
    logger.info(f"Starting scheduled data collection every {config.DATA_COLLECTION_INTERVAL_HOURS} hours")
    
    # Initial run
    run_collector()
    
    # Schedule runs
    try:
        while True:
            logger.info(f"Waiting {interval_seconds} seconds until next data collection")
            time.sleep(interval_seconds)
            run_collector()
    except KeyboardInterrupt:
        logger.info("Data collection stopped by user")
        db_client.close()

if __name__ == "__main__":
    print("WARNING: Running in continuous mode is not recommended for servers.")
    print("Consider using crontab with 'python run_collector.py' instead.")
    print("Run 'python setup_crontab.py' to configure crontab.")
    print("Continue with continuous mode? (y/n)")
    response = input().strip().lower()
    if response == 'y':
        run_collector_scheduled()
    else:
        print("Exiting. Use 'python setup_crontab.py' to configure crontab.")
