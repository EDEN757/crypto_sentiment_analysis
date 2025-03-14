#!/usr/bin/env python
"""
Sentiment analysis script optimized for crontab execution.

This script analyzes the sentiment of collected news articles using the FinBERT model
and stores the results in the database for later retrieval.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from bson import ObjectId

# Ensure proper path resolution regardless of where the script is called from
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import project modules
from src.sentiment_analyzer import analyze_and_store_all_sentiments
from src.database import db_client
from src import config

def main():
    """Run sentiment analysis once and store results."""
    # Create a lock file to prevent overlapping execution
    lock_file = BASE_DIR / 'sentiment_analysis.lock'
    analysis_start_time = datetime.now()
    
    if lock_file.exists():
        # Check if the lock file is recent (< 30 minutes old)
        lock_time = datetime.fromtimestamp(os.path.getmtime(lock_file))
        if (analysis_start_time - lock_time).total_seconds() < 1800:  # 30 minutes
            print(f"WARNING: Another sentiment analysis process appears to be running (lock file created at {lock_time}). Exiting.")
            sys.exit(0)
        else:
            # Lock file is old, probably from a crashed process
            print(f"WARNING: Found a stale lock file from {lock_time}. Continuing anyway.")
    
    # Create the lock file
    with open(lock_file, 'w') as f:
        f.write(f"Sentiment analysis started at {analysis_start_time}")
    
    # Configure logging specifically for cron execution
    log_file = BASE_DIR / 'logs' / f'cron-sentiment-{analysis_start_time.strftime("%Y%m%d")}.log'
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
    logger.info(f"Starting scheduled sentiment analysis at {analysis_start_time}")
    logger.info(f"Using FinBERT model: {config.SENTIMENT_MODEL}")
    
    try:
        # Analyze sentiment for all configured collections
        comparison = analyze_and_store_all_sentiments()
        
        # Also write to a local JSON file for easy access
        data_dir = BASE_DIR / 'data'
        os.makedirs(data_dir, exist_ok=True)
        
        # Convert datetime and ObjectId to string for JSON serialization
        comparison_copy = comparison.copy()
        if "timestamp" in comparison_copy:
            comparison_copy["timestamp"] = comparison_copy["timestamp"].isoformat()
        
        # Handle ObjectId serialization issue
        def handle_objectid(obj):
            if isinstance(obj, dict):
                for key, value in list(obj.items()):
                    if isinstance(value, ObjectId):
                        obj[key] = str(value)
                    elif isinstance(value, dict):
                        handle_objectid(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                handle_objectid(item)
            return obj

        comparison_copy = handle_objectid(comparison_copy)
        
        with open(data_dir / f'sentiment-{analysis_start_time.strftime("%Y%m%d-%H%M%S")}.json', 'w') as f:
            json.dump(comparison_copy, f, indent=2)
        
        # Print summary to stdout/stderr for cron emails
        print("\n=== Sentiment Analysis Results ===")
        
        # Print results for each item in the comparison
        for name, sentiment in comparison.items():
            if name == "timestamp":
                continue
                
            if isinstance(sentiment, dict) and "score" in sentiment:
                print(f"{name}: {sentiment['score']:.4f} ({sentiment.get('label', 'unknown')}) from {sentiment.get('article_count', 0)} articles")
        
        # Identify any crypto assets for specific comparison
        crypto_assets = [crypto["name"] for crypto in config.DEFAULT_CONFIG["assets"]["crypto"] 
                        if "news_collection" in crypto]
        
        # Compare first crypto asset with global economy if both exist
        if crypto_assets and "Global Economy" in comparison:
            crypto = crypto_assets[0]  # Take first crypto asset
            if crypto in comparison:
                crypto_score = comparison[crypto]["score"]
                economy_score = comparison["Global Economy"]["score"]
                diff = crypto_score - economy_score
                
                print(f"\nDifference ({crypto} - Global Economy): {diff:.4f}")
                
                if diff > 0.1:
                    result_msg = f"{crypto} sentiment is more positive than global economy"
                elif diff < -0.1:
                    result_msg = f"Global economy sentiment is more positive than {crypto}"
                else:
                    result_msg = f"{crypto} and global economy sentiment are approximately equal"
                    
                print(f"Result: {result_msg}")
        
        logger.info(f"Total sentiment analysis time: {(datetime.now() - analysis_start_time).total_seconds()/60:.1f} minutes")
                   
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Always remove the lock file when done
        if lock_file.exists():
            os.remove(lock_file)
        
    logger.info("Sentiment analysis script completed successfully")

if __name__ == "__main__":
    main()