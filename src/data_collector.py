"""Data collector module for fetching financial news and price data.

This module provides functions to collect financial news articles from NewsAPI
and price data for financial assets from Yahoo Finance.
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
    
    def collect_news_for_query(self, query: str, collection_name: str) -> List[Dict[str, Any]]:
        """Collect news articles for a specific query from NewsAPI.
        
        Args:
            query: The search query string
            collection_name: The name of the collection for storing articles
            
        Returns:
            List of news articles
        """
        try:
            logger.info(f"Collecting news articles for query: '{query}'")
            
            # Get news from the last 24 hours (NewsAPI free tier limitation)
            response = self.news_api.get_everything(
                q=query,
                language='en',
                sort_by='publishedAt',
                page_size=100,  # Maximum allowed by NewsAPI
                from_param=(datetime.utcnow() - timedelta(days=1)).date().isoformat()
            )
            
            articles = response.get('articles', [])
            logger.info(f"Collected {len(articles)} articles for query: '{query}'")
            
            # Store articles in the database
            inserted_count = db_client.insert_articles(collection_name, articles)
            logger.info(f"Stored {inserted_count} new articles in {collection_name}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to collect news for query '{query}': {str(e)}")
            return []
    
    def collect_price_data(self, symbol: str, collection_name: str) -> Optional[Dict[str, Any]]:
        """Collect price data for a financial asset from Yahoo Finance.
        
        Args:
            symbol: The Yahoo Finance symbol
            collection_name: The name of the collection for storing price data
            
        Returns:
            Price data or None if collection fails
        """
        try:
            logger.info(f"Collecting price data for {symbol}")
            
            # Get price data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1h")
            
            if hist.empty:
                logger.warning(f"No price data available for {symbol}")
                return None
            
            # Get the latest price data
            latest = hist.iloc[-1]
            # Get the datetime index for the latest price
            latest_datetime = hist.index[-1].to_pydatetime()
            
            price_data = {
                "symbol": symbol,
                "timestamp": latest_datetime,  # Use the actual price timestamp
                "collection_time": datetime.utcnow(),  # When we collected it
                "price": latest["Close"],
                "open": latest["Open"],
                "high": latest["High"],
                "low": latest["Low"],
                "volume": latest["Volume"],
                "raw_data": latest.to_dict()
            }
            
            logger.info(f"Collected {symbol} price: ${price_data['price']:.2f} from {latest_datetime}")
            
            # Store price data in the database
            success = db_client.insert_price_data(collection_name, price_data)
            if success:
                logger.info(f"Stored price data for {symbol} in {collection_name}")
            
            return price_data if success else None
            
        except Exception as e:
            logger.error(f"Failed to collect price data for {symbol}: {str(e)}")
            return None
    
    def collect_and_store_all_data(self) -> Dict[str, Any]:
        """Collect and store all financial data based on configuration.
        
        This method collects both news articles and price data in a single execution
        based on the assets and news sources defined in the configuration.
        
        Returns:
            Dictionary with collection results
        """
        interval = config.DATA_COLLECTION_INTERVAL_HOURS
        logger.info(f"Starting {interval}-hour data collection cycle at {datetime.now()}")
        
        # Initialize collection results
        results = {
            "news_articles": {},
            "price_data": {}
        }
        
        # 1. Collect and store news for each configured query
        for news_config in config.DEFAULT_CONFIG["news_queries"]:
            try:
                logger.info(f"--- COLLECTING {news_config['name']} NEWS ---")
                query = news_config["query"]
                collection = news_config["collection"]
                articles = self.collect_news_for_query(query, collection)
                results["news_articles"][news_config["name"]] = len(articles)
            except Exception as e:
                logger.error(f"{news_config['name']} news collection failed: {str(e)}", exc_info=True)
                results["news_articles"][news_config["name"]] = 0
        
        # 2. Collect and store news and price data for crypto assets
        for crypto in config.DEFAULT_CONFIG["assets"]["crypto"]:
            try:
                # Collect news
                if "query" in crypto and "news_collection" in crypto:
                    logger.info(f"--- COLLECTING {crypto['name']} NEWS ---")
                    query = crypto["query"]
                    collection = crypto["news_collection"]
                    articles = self.collect_news_for_query(query, collection)
                    results["news_articles"][crypto["name"]] = len(articles)
                
                # Collect price data
                logger.info(f"--- COLLECTING {crypto['name']} PRICE ---")
                symbol = crypto["symbol"]
                collection = crypto["collection"]
                price_data = self.collect_price_data(symbol, collection)
                results["price_data"][crypto["name"]] = price_data is not None
            except Exception as e:
                logger.error(f"{crypto['name']} data collection failed: {str(e)}", exc_info=True)
                if crypto["name"] not in results["news_articles"]:
                    results["news_articles"][crypto["name"]] = 0
                results["price_data"][crypto["name"]] = False
        
        # 3. Collect and store price data for indices
        for index in config.DEFAULT_CONFIG["assets"]["indices"]:
            try:
                logger.info(f"--- COLLECTING {index['name']} PRICE ---")
                symbol = index["symbol"]
                collection = index["collection"]
                price_data = self.collect_price_data(symbol, collection)
                results["price_data"][index["name"]] = price_data is not None
            except Exception as e:
                logger.error(f"{index['name']} price collection failed: {str(e)}", exc_info=True)
                results["price_data"][index["name"]] = False
        
        # Log summary
        logger.info("=== DATA COLLECTION SUMMARY ===")
        for name, count in results["news_articles"].items():
            logger.info(f"- {name} articles: {count} collected")
        for name, success in results["price_data"].items():
            logger.info(f"- {name} price: {'Collected and stored' if success else 'Failed'}")
        logger.info(f"Next collection scheduled in {interval} hours")
        
        return results

def run_collector():
    """Run the data collector once."""
    collector = DataCollector()
    results = collector.collect_and_store_all_data()
    
    # Log completion
    article_count = sum(count for count in results["news_articles"].values())
    price_count = sum(1 for success in results["price_data"].values() if success)
    price_total = len(results["price_data"])
    
    logger.info(f"Data collection complete: "
                f"Articles: {article_count}, "
                f"Price data: {price_count}/{price_total}")
    
    return results

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