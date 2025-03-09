#!/usr/bin/env python
"""
Data collection script optimized for crontab execution.

This script is designed to be run by cron at regular intervals (every 3 hours).
It collects both financial news articles and price data in a single execution.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Ensure proper path resolution regardless of where the script is called from
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import project modules
from src.data_collector import DataCollector
from src.database import db_client
from src import config

def main():
    """Run data collection once and exit."""
    # Create a lock file to prevent overlapping execution
    lock_file = BASE_DIR / 'data_collection.lock'
    collection_start_time = datetime.now()
    
    if lock_file.exists():
        # Check if the lock file is recent (< 30 minutes old)
        lock_time = datetime.fromtimestamp(os.path.getmtime(lock_file))
        if (collection_start_time - lock_time).total_seconds() < 1800:  # 30 minutes
            print(f"WARNING: Another data collection process appears to be running (lock file created at {lock_time}). Exiting.")
            sys.exit(0)
        else:
            # Lock file is old, probably from a crashed process
            print(f"WARNING: Found a stale lock file from {lock_time}. Continuing anyway.")
    
    # Create the lock file
    with open(lock_file, 'w') as f:
        f.write(f"{config.DATA_COLLECTION_INTERVAL_HOURS}-hour collection cycle started at {collection_start_time}")
    
    # Configure logging specifically for cron execution
    log_file = BASE_DIR / 'logs' / f'cron-collector-{collection_start_time.strftime("%Y%m%d")}.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Use both file and stderr logging for cron
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Log to stderr so it appears in cron's email
        ]
    )
    
    logger = logging.getLogger(__name__)
    interval = config.DATA_COLLECTION_INTERVAL_HOURS
    logger.info(f"Starting {interval}-hour data collection cycle at {collection_start_time}")
    logger.info(f"Using configuration with {len(config.DEFAULT_CONFIG['assets']['crypto'])} crypto assets, "
                f"{len(config.DEFAULT_CONFIG['assets']['indices'])} indices, and "
                f"{len(config.DEFAULT_CONFIG['news_queries'])} news queries")
    
    success = False
    try:
        # Collect data
        collector = DataCollector()
        results = collector.collect_and_store_all_data()
        
        # Check if we have at least some data collected successfully
        article_count = sum(count for count in results["news_articles"].values())
        price_count = sum(1 for success in results["price_data"].values() if success)
        price_total = len(results["price_data"])
        
        success = article_count > 0 or price_count > 0
        
        # Log results
        logger.info(f"=== {interval}-HOUR COLLECTION CYCLE COMPLETED ===")
        for name, count in results["news_articles"].items():
            logger.info(f"- {name} articles: {count} collected and stored")
        for name, success in results["price_data"].items():
            logger.info(f"- {name} price: {'Successfully stored' if success else 'Failed to store'}")
        logger.info(f"Total collection time: {(datetime.now() - collection_start_time).total_seconds()/60:.1f} minutes")
        logger.info(f"Next collection cycle scheduled in {interval} hours")
                   
    except Exception as e:
        logger.error(f"{interval}-hour data collection cycle failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Always remove the lock file when done
        if lock_file.exists():
            os.remove(lock_file)
    
    if success:
        logger.info("Data collection script completed successfully")
    else:
        logger.error("Data collection cycle failed to collect any data!")
        sys.exit(1)

if __name__ == "__main__":
    main()