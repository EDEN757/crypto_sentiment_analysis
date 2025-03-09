"""Configuration module for the Financial Sentiment Analysis Dashboard.

This module loads environment variables and provides configuration settings
for the application.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pathlib import Path
import json

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# API Keys
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
if not NEWS_API_KEY:
    raise ValueError("NEWS_API_KEY environment variable is required")

# MongoDB Configuration
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING')
if not MONGODB_CONNECTION_STRING:
    raise ValueError("MONGODB_CONNECTION_STRING environment variable is required")

MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'financial_sentiment')

# Collection names
BITCOIN_ARTICLES_COLLECTION = 'bitcoin_articles'
GLOBAL_ECONOMY_ARTICLES_COLLECTION = 'global_economy_articles'
BITCOIN_PRICE_COLLECTION = 'bitcoin_price'
SP500_COLLECTION = 'sp500'
SENTIMENT_RESULTS_COLLECTION = 'sentiment_results'

# Data collection settings
DEFAULT_CONFIG = {
    "assets": {
        "crypto": [
            {
                "name": "Bitcoin",
                "symbol": "BTC-USD", 
                "collection": "bitcoin_price",
                "query": "bitcoin OR btc",
                "news_collection": "bitcoin_articles"
            }
        ],
        "indices": [
            {
                "name": "S&P 500",
                "symbol": "^GSPC",
                "collection": "sp500"
            }
        ]
    },
    "news_queries": [
        {
            "name": "Global Economy",
            "query": "global economy OR economic outlook OR financial markets",
            "collection": "global_economy_articles"
        }
    ],
    "collection_interval_hours": int(os.getenv('DATA_COLLECTION_INTERVAL_HOURS', 3)),
    "sentiment_model": "ProsusAI/finbert"
}

# Try to load config from file if it exists
CONFIG_FILE = BASE_DIR / 'config' / 'app_config.json'
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)
            # Merge user config with defaults
            DEFAULT_CONFIG.update(user_config)
    except Exception as e:
        print(f"Error loading config file: {e}. Using default configuration.")

# Extract commonly used values for backward compatibility
BITCOIN_QUERY = next((asset["query"] for asset in DEFAULT_CONFIG["assets"]["crypto"] 
                      if asset["name"] == "Bitcoin"), "bitcoin OR btc")
GLOBAL_ECONOMY_QUERY = next((news["query"] for news in DEFAULT_CONFIG["news_queries"] 
                            if news["name"] == "Global Economy"), 
                           "global economy OR economic outlook OR financial markets")
DATA_COLLECTION_INTERVAL_HOURS = DEFAULT_CONFIG["collection_interval_hours"]
SENTIMENT_MODEL = DEFAULT_CONFIG["sentiment_model"]

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = BASE_DIR / 'logs' / 'app.log'

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure logging
def setup_logging():
    """Set up logging configuration."""
    log_level = getattr(logging, LOG_LEVEL.upper())
    
    # Create handlers
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10485760, backupCount=5
    )
    console_handler = logging.StreamHandler()
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Initialize logger
logger = setup_logging()