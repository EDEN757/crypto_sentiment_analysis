#!/usr/bin/env python
"""
Sentiment analysis script optimized for crontab execution.

This script analyzes the sentiment of collected news articles and stores
the results in the database for later retrieval.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Ensure proper path resolution regardless of where the script is called from
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import project modules
from src.sentiment_analyzer import SentimentAnalyzer
from src.database import db_client
from src import config

def main():
    """Run sentiment analysis once and store results."""
    # Configure logging specifically for cron execution
    log_file = BASE_DIR / 'logs' / f'cron-sentiment-{datetime.now().strftime("%Y%m%d")}.log'
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
    logger.info(f"Starting scheduled sentiment analysis at {datetime.now()}")
    
    try:
        # Analyze sentiment
        analyzer = SentimentAnalyzer()
        comparison = analyzer.compare_bitcoin_vs_global_economy_sentiment()
        
        # Create a collection for sentiment analysis results if it doesn't exist
        SENTIMENT_RESULTS_COLLECTION = 'sentiment_results'
        
        # Store results in MongoDB
        result_id = db_client.db[SENTIMENT_RESULTS_COLLECTION].insert_one(comparison).inserted_id
        logger.info(f"Stored sentiment analysis results with ID: {result_id}")
        
        # Also write to a local JSON file for easy access
        data_dir = BASE_DIR / 'data'
        os.makedirs(data_dir, exist_ok=True)
        
        # Convert datetime to string for JSON serialization
        comparison_copy = comparison.copy()
        comparison_copy['timestamp'] = comparison_copy['timestamp'].isoformat()
        
        with open(data_dir / f'sentiment-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json', 'w') as f:
            json.dump(comparison_copy, f, indent=2)
        
        # Print summary to stdout/stderr for cron emails
        print("\n=== Sentiment Analysis Results ===")
        print(f"Bitcoin: {comparison['bitcoin']['combined_score']:.4f} (from {comparison['bitcoin']['article_count']} articles)")
        print(f"Global Economy: {comparison['global_economy']['combined_score']:.4f} (from {comparison['global_economy']['article_count']} articles)")
        print(f"Difference: {comparison['difference']['combined_score_diff']:.4f}")
        
        if comparison['difference']['combined_score_diff'] > 0:
            print("Result: Bitcoin sentiment is more positive than global economy sentiment")
        elif comparison['difference']['combined_score_diff'] < 0:
            print("Result: Global economy sentiment is more positive than Bitcoin sentiment")
        else:
            print("Result: Bitcoin and global economy sentiment are approximately equal")
                   
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}", exc_info=True)
        sys.exit(1)
        
    logger.info("Sentiment analysis script completed successfully")

if __name__ == "__main__":
    main() 