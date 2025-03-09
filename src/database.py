"""Database module for MongoDB operations.

This module provides functions for connecting to MongoDB and performing
database operations such as inserting, updating, and querying data.
"""

import pymongo
from pymongo.errors import ConnectionFailure, PyMongoError
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional

from . import config

logger = logging.getLogger(__name__)

class MongoDBClient:
    """MongoDB client for database operations."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one database connection."""
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the MongoDB connection."""
        try:
            self.client = pymongo.MongoClient(config.MONGODB_CONNECTION_STRING)
            self.db = self.client[config.MONGODB_DATABASE_NAME]
            
            # Test the connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {config.MONGODB_DATABASE_NAME}")
            
            # Create indices for collections
            self._create_indices()
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            raise
    
    def _create_indices(self):
        """Create indices for faster queries."""
        try:
            # Bitcoin articles collection - index on published_at and source
            self.db[config.BITCOIN_ARTICLES_COLLECTION].create_index(
                [("published_at", pymongo.DESCENDING), ("source.name", pymongo.ASCENDING)],
                background=True
            )
            
            # Global economy articles collection - index on published_at and source
            self.db[config.GLOBAL_ECONOMY_ARTICLES_COLLECTION].create_index(
                [("published_at", pymongo.DESCENDING), ("source.name", pymongo.ASCENDING)],
                background=True
            )
            
            # Bitcoin price collection - index on timestamp
            self.db[config.BITCOIN_PRICE_COLLECTION].create_index(
                [("timestamp", pymongo.DESCENDING)],
                background=True
            )
            
            # SP500 collection - index on timestamp
            self.db[config.SP500_COLLECTION].create_index(
                [("timestamp", pymongo.DESCENDING)],
                background=True
            )
            
            logger.info("Created database indices")
        except PyMongoError as e:
            logger.error(f"Failed to create indices: {str(e)}")
    
    def insert_articles(self, collection_name: str, articles: List[Dict[str, Any]]) -> int:
        """Insert articles into the specified collection.
        
        Args:
            collection_name: The name of the collection to insert into
            articles: List of article documents to insert
            
        Returns:
            Number of articles inserted
        """
        if not articles:
            logger.warning(f"No articles to insert into {collection_name}")
            return 0
        
        try:
            # Add timestamp for when the document was stored
            for article in articles:
                # Add collection timestamp
                article['stored_at'] = datetime.utcnow()
                
                # Convert published_at to datetime if it's a string
                if isinstance(article.get('publishedAt'), str):
                    try:
                        # Handle different date formats
                        published_date_str = article.pop('publishedAt')
                        if 'Z' in published_date_str:
                            # ISO format with Z
                            article['published_at'] = datetime.fromisoformat(
                                published_date_str.replace('Z', '+00:00')
                            )
                        elif 'T' in published_date_str:
                            # ISO format without Z
                            article['published_at'] = datetime.fromisoformat(published_date_str)
                        else:
                            # Try general format
                            article['published_at'] = datetime.strptime(
                                published_date_str, "%Y-%m-%d %H:%M:%S"
                            )
                        
                        # Log if there's a significant difference between published and stored times
                        time_diff = (article['stored_at'] - article['published_at']).total_seconds() / 3600
                        if time_diff > 48:  # More than 48 hours
                            logger.warning(
                                f"Article published {time_diff:.1f} hours before collection: "
                                f"{article.get('title', 'No title')}"
                            )
                            
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse article date: {e}. Using current time.")
                        article['published_at'] = article['stored_at']
                
                # Handle case where no publishedAt exists
                if 'published_at' not in article:
                    if 'publishedAt' in article:  # Just in case the earlier pop failed
                        article['published_at'] = article.pop('publishedAt')
                    else:
                        article['published_at'] = article['stored_at']
            
            # Ensure no duplicate articles by title and source
            # Use bulk operations for efficiency
            operations = []
            inserted_count = 0
            
            for article in articles:
                # Create a filter to find potential duplicates
                filter_doc = {
                    "title": article["title"],
                    "source.name": article["source"]["name"] if "source" in article and "name" in article["source"] else None
                }
                
                # Create an update operation with upsert=True
                operations.append(
                    pymongo.UpdateOne(
                        filter_doc,
                        {"$setOnInsert": article},
                        upsert=True
                    )
                )
            
            # Execute the bulk operation
            if operations:
                result = self.db[collection_name].bulk_write(operations)
                inserted_count = result.upserted_count
                logger.info(f"Inserted {inserted_count} new articles into {collection_name}")
            
            return inserted_count
            
        except PyMongoError as e:
            logger.error(f"Failed to insert articles into {collection_name}: {str(e)}")
            return 0
    
    def insert_price_data(self, collection_name: str, price_data: Dict[str, Any]) -> bool:
        """Insert price data into the specified collection.
        
        Args:
            collection_name: The name of the collection to insert into
            price_data: Price data document to insert
            
        Returns:
            True if insertion was successful, False otherwise
        """
        if not price_data:
            logger.warning(f"No price data to insert into {collection_name}")
            return False
        
        try:
            # Ensure timestamp exists
            if 'timestamp' not in price_data:
                logger.warning("No timestamp in price data, using current time")
                price_data['timestamp'] = datetime.utcnow()
                
            # Add collection timestamp if not present
            if 'collection_time' not in price_data:
                price_data['collection_time'] = datetime.utcnow()
                
            # Make timestamp timezone-aware if it's not
            if price_data['timestamp'].tzinfo is None:
                logger.debug("Converting naive timestamp to UTC")
                # Assume the timestamp is in UTC if not specified
                price_data['timestamp'] = price_data['timestamp'].replace(tzinfo=None)
            
            # Check if we already have price data for this exact timestamp
            existing = self.db[collection_name].find_one({
                "symbol": price_data["symbol"],
                "timestamp": price_data["timestamp"]
            })
            
            if existing:
                logger.info(f"Price data for {price_data['symbol']} at {price_data['timestamp']} already exists")
                return True
            
            # Insert the price data
            result = self.db[collection_name].insert_one(price_data)
            logger.info(f"Inserted price data for {price_data['symbol']} from {price_data['timestamp']} "
                        f"into {collection_name} with ID: {result.inserted_id}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Failed to insert price data into {collection_name}: {str(e)}")
            return False
    
    def get_latest_articles(self, collection_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the latest articles from the specified collection.
        
        Args:
            collection_name: The name of the collection to query
            limit: Maximum number of articles to return
            
        Returns:
            List of article documents
        """
        try:
            articles = list(self.db[collection_name]
                           .find({})
                           .sort("published_at", pymongo.DESCENDING)
                           .limit(limit))
            logger.info(f"Retrieved {len(articles)} latest articles from {collection_name}")
            return articles
            
        except PyMongoError as e:
            logger.error(f"Failed to get latest articles from {collection_name}: {str(e)}")
            return []
    
    def get_price_data(self, collection_name: str, 
                     start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get price data from the specified collection within a date range.
        
        Args:
            collection_name: The name of the collection to query
            start_date: Start date for the query (inclusive)
            end_date: End date for the query (inclusive)
            
        Returns:
            List of price data documents
        """
        query = {}
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = start_date
            if end_date:
                query['timestamp']['$lte'] = end_date
        
        try:
            price_data = list(self.db[collection_name]
                             .find(query)
                             .sort("timestamp", pymongo.ASCENDING))
            logger.info(f"Retrieved {len(price_data)} price data points from {collection_name}")
            return price_data
            
        except PyMongoError as e:
            logger.error(f"Failed to get price data from {collection_name}: {str(e)}")
            return []
    
    def close(self):
        """Close the MongoDB connection."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")

# Create a singleton instance
db_client = MongoDBClient()
