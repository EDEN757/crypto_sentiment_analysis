"""Sentiment analyzer module for financial news.

This module provides functions for analyzing sentiment in financial news articles
using NLP techniques and the FinBERT model.
"""

import logging
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from typing import Dict, Any, List, Optional
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from pathlib import Path
import os
import json

from . import config
from .database import db_client

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Class for analyzing sentiment in financial news articles."""
    
    def __init__(self, model_name: str = None):
        """Initialize the sentiment analyzer with NLP models.
        
        Args:
            model_name: The name of the FinBERT model to use (default from config)
        """
        # Download required NLTK resources
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer")
            nltk.download('punkt', quiet=True)
            
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK stopwords")
            nltk.download('stopwords', quiet=True)
        
        # Set up FinBERT model
        model_name = model_name or config.SENTIMENT_MODEL
        
        # Create models directory if it doesn't exist
        models_dir = Path(config.BASE_DIR) / 'models'
        os.makedirs(models_dir, exist_ok=True)
        
        # Load the FinBERT model and tokenizer
        logger.info(f"Loading FinBERT model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        # Set up device (GPU if available, otherwise CPU)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        self.model.to(self.device)
        
        # Set up stopwords
        self.stop_words = set(stopwords.words('english'))
        
        logger.info("Sentiment analyzer initialized with FinBERT model")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for sentiment analysis.
        
        Args:
            text: The text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
            
        # Clean up text (remove excessive whitespace, etc.)
        text = ' '.join(text.split())
        
        return text
    
    def analyze_sentiment_finbert(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using FinBERT.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with sentiment scores in range 0-1
        """
        if not text or len(text) < 10:  # Require at least 10 chars
            return {
                'score': 0.5,  # Neutral
                'label': 'neutral'
            }
        
        # Preprocess text
        preprocessed_text = self._preprocess_text(text)
        if not preprocessed_text:
            return {
                'score': 0.5,  # Neutral 
                'label': 'neutral'
            }
        
        # Split into sentences and analyze each (FinBERT has token limits)
        sentences = sent_tokenize(preprocessed_text)
        scores = []
        
        # Process each sentence
        for sentence in sentences:
            # Skip very short sentences
            if len(sentence) < 5:
                continue
            
            try:
                # Tokenize the sentence
                inputs = self.tokenizer(sentence, return_tensors="pt", truncation=True, 
                                       max_length=512, padding=True)
                inputs = {key: val.to(self.device) for key, val in inputs.items()}
                
                # Get predictions
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
                    
                # Map FinBERT output (negative, neutral, positive) to score
                # FinBERT returns [negative, neutral, positive] probabilities
                # We map this to a 0-1 score (0=negative, 0.5=neutral, 1=positive)
                score = probs[2] * 1.0 + probs[1] * 0.5 + probs[0] * 0.0
                scores.append(score)
                
            except Exception as e:
                logger.warning(f"Error processing sentence: {str(e)}")
                continue
        
        # Calculate average score
        if not scores:
            return {
                'score': 0.5,  # Neutral
                'label': 'neutral'
            }
        
        avg_score = sum(scores) / len(scores)
        
        # Determine label based on score
        if avg_score < 0.4:
            label = 'negative'
        elif avg_score > 0.6:
            label = 'positive'
        else:
            label = 'neutral'
        
        return {
            'score': avg_score,
            'label': label
        }
    
    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment for a news article.
        
        Args:
            article: The news article to analyze
            
        Returns:
            Article with sentiment scores added
        """
        # Create a copy of the article to avoid modifying the original
        result = article.copy()
        
        # Combine title and content for analysis
        title = article.get('title', '')
        content = article.get('content', '')
        description = article.get('description', '')
        
        full_text = f"{title} {description} {content}"
        
        # Analyze sentiment
        sentiment = self.analyze_sentiment_finbert(full_text)
        
        # Add sentiment scores to result
        result['sentiment'] = sentiment
        
        # If the article has an _id field, use it to update the article in the database
        if '_id' in article:
            try:
                collection_name = article.get('_collection', config.BITCOIN_ARTICLES_COLLECTION)
                db_client.update_article_sentiment(collection_name, article['_id'], sentiment)
                logger.debug(f"Updated sentiment for article {article['_id']} in {collection_name}")
            except Exception as e:
                logger.warning(f"Failed to update article sentiment in database: {str(e)}")
        
        return result
    
    def analyze_articles_from_collection(self, collection_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Analyze sentiment for articles in a collection.
        
        Args:
            collection_name: The name of the collection to analyze
            limit: Maximum number of articles to analyze
            
        Returns:
            List of articles with sentiment scores
        """
        logger.info(f"Analyzing sentiment for articles in {collection_name}")
        
        # Get the latest articles without sentiment analysis
        articles = db_client.get_articles_without_sentiment(collection_name, limit)
        
        # Add collection info to each article
        for article in articles:
            article['_collection'] = collection_name
        
        # Analyze sentiment for each article
        results = []
        for article in articles:
            analyzed = self.analyze_article(article)
            results.append(analyzed)
        
        logger.info(f"Analyzed sentiment for {len(results)} articles from {collection_name}")
        
        return results
    
    def get_average_sentiment(self, collection_name: str, days: int = 1) -> Dict[str, float]:
        """Get average sentiment scores for articles in a collection.
        
        Args:
            collection_name: The name of the collection to analyze
            days: Number of days to look back for articles
            
        Returns:
            Dictionary with average sentiment scores
        """
        # Get articles with sentiment from the past N days
        articles = db_client.get_articles_with_sentiment(collection_name, days)
        
        if not articles:
            return {
                'score': 0.5,  # Neutral
                'article_count': 0
            }
        
        # Calculate average score
        score_sum = sum(a['sentiment']['score'] for a in articles if 'sentiment' in a)
        count = len([a for a in articles if 'sentiment' in a])
        
        if count == 0:
            return {
                'score': 0.5,  # Neutral
                'article_count': 0
            }
        
        avg_score = score_sum / count
        
        # Determine label based on score
        if avg_score < 0.4:
            label = 'negative'
        elif avg_score > 0.6:
            label = 'positive'
        else:
            label = 'neutral'
        
        return {
            'score': avg_score,
            'label': label,
            'article_count': count
        }
    
    def compare_crypto_vs_economy_sentiment(self) -> Dict[str, Any]:
        """Compare sentiment between crypto and global economy news.
        
        Returns:
            Dictionary with comparative sentiment analysis
        """
        logger.info("Comparing crypto vs global economy sentiment")
        
        results = {}
        
        # Get sentiment for crypto assets
        for crypto in config.DEFAULT_CONFIG["assets"]["crypto"]:
            if "news_collection" in crypto:
                collection_name = crypto["news_collection"]
                sentiment = self.get_average_sentiment(collection_name)
                results[crypto["name"]] = sentiment
        
        # Get sentiment for global economy
        for news_config in config.DEFAULT_CONFIG["news_queries"]:
            collection_name = news_config["collection"]
            sentiment = self.get_average_sentiment(collection_name)
            results[news_config["name"]] = sentiment
        
        # Add timestamp
        results["timestamp"] = pd.Timestamp.now()
        
        # Store results in database
        db_client.insert_sentiment_comparison(config.SENTIMENT_RESULTS_COLLECTION, results)
        
        return results

def analyze_and_store_all_sentiments():
    """Analyze sentiment for all collections and store results."""
    analyzer = SentimentAnalyzer()
    
    # First, analyze any unanalyzed articles in each collection
    for crypto in config.DEFAULT_CONFIG["assets"]["crypto"]:
        if "news_collection" in crypto:
            collection_name = crypto["news_collection"]
            analyzer.analyze_articles_from_collection(collection_name)
    
    for news_config in config.DEFAULT_CONFIG["news_queries"]:
        collection_name = news_config["collection"]
        analyzer.analyze_articles_from_collection(collection_name)
    
    # Then, compare overall sentiment
    comparison = analyzer.compare_crypto_vs_economy_sentiment()
    
    # Return comparison for logging/display
    return comparison

def analyze_and_print_sentiment():
    """Analyze sentiment and print results."""
    comparison = analyze_and_store_all_sentiments()
    
    print("\n--- Sentiment Analysis Results ---")
    
    # Print results for each item in the comparison
    for name, sentiment in comparison.items():
        if name == "timestamp":
            continue
            
        if isinstance(sentiment, dict) and "score" in sentiment:
            print(f"{name} Sentiment (from {sentiment.get('article_count', 0)} articles):")
            print(f"  Score: {sentiment['score']:.4f}")
            print(f"  Classification: {sentiment.get('label', 'unknown')}")
            print()
    
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
                print(f"Result: {crypto} sentiment is more positive than global economy sentiment")
            elif diff < -0.1:
                print(f"Result: Global economy sentiment is more positive than {crypto} sentiment")
            else:
                print(f"Result: {crypto} and global economy sentiment are approximately equal")

if __name__ == "__main__":
    analyze_and_print_sentiment()