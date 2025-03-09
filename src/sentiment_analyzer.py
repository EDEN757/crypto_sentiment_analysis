"""Sentiment analyzer module for financial news.

This module provides functions for analyzing sentiment in financial news articles
using NLP techniques.
"""

import logging
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

from . import config
from .database import db_client

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Class for analyzing sentiment in financial news articles."""
    
    def __init__(self):
        """Initialize the sentiment analyzer with NLP models."""
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
        
        # Initialize sentiment analyzer from VADER
        self.vader = SentimentIntensityAnalyzer()
        self.stop_words = set(stopwords.words('english'))
        
        logger.info("Sentiment analyzer initialized")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for sentiment analysis.
        
        Args:
            text: The text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
            
        # Tokenize and remove stopwords
        tokens = word_tokenize(text.lower())
        filtered_tokens = [
            token for token in tokens 
            if token.isalpha() and token not in self.stop_words
        ]
        
        # Join tokens back into a string
        return " ".join(filtered_tokens)
    
    def analyze_sentiment_vader(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using VADER.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        preprocessed_text = self._preprocess_text(text)
        if not preprocessed_text:
            return {
                'compound': 0.0,
                'neg': 0.0,
                'neu': 0.0,
                'pos': 0.0
            }
            
        return self.vader.polarity_scores(preprocessed_text)
    
    def analyze_sentiment_textblob(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using TextBlob.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        preprocessed_text = self._preprocess_text(text)
        if not preprocessed_text:
            return {
                'polarity': 0.0,
                'subjectivity': 0.0
            }
            
        blob = TextBlob(preprocessed_text)
        return {
            'polarity': blob.sentiment.polarity,
            'subjectivity': blob.sentiment.subjectivity
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
        vader_scores = self.analyze_sentiment_vader(full_text)
        textblob_scores = self.analyze_sentiment_textblob(full_text)
        
        # Add sentiment scores to result
        result['sentiment'] = {
            'vader': vader_scores,
            'textblob': textblob_scores,
            # Combined sentiment score (normalized from -1 to 1)
            'combined_score': (vader_scores['compound'] + textblob_scores['polarity']) / 2
        }
        
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
        
        # Get the latest articles
        articles = db_client.get_latest_articles(collection_name, limit)
        
        # Analyze sentiment for each article
        results = []
        for article in articles:
            analyzed = self.analyze_article(article)
            results.append(analyzed)
        
        logger.info(f"Analyzed sentiment for {len(results)} articles from {collection_name}")
        
        return results
    
    def get_average_sentiment(self, collection_name: str, limit: int = 100) -> Dict[str, float]:
        """Get average sentiment scores for articles in a collection.
        
        Args:
            collection_name: The name of the collection to analyze
            limit: Maximum number of articles to analyze
            
        Returns:
            Dictionary with average sentiment scores
        """
        articles = self.analyze_articles_from_collection(collection_name, limit)
        
        if not articles:
            return {
                'vader_compound': 0.0,
                'textblob_polarity': 0.0,
                'combined_score': 0.0
            }
        
        # Calculate average scores
        vader_compound_sum = sum(a['sentiment']['vader']['compound'] for a in articles)
        textblob_polarity_sum = sum(a['sentiment']['textblob']['polarity'] for a in articles)
        combined_score_sum = sum(a['sentiment']['combined_score'] for a in articles)
        
        count = len(articles)
        
        return {
            'vader_compound': vader_compound_sum / count,
            'textblob_polarity': textblob_polarity_sum / count,
            'combined_score': combined_score_sum / count,
            'article_count': count
        }
    
    def compare_bitcoin_vs_global_economy_sentiment(self) -> Dict[str, Any]:
        """Compare sentiment between Bitcoin and global economy news.
        
        Returns:
            Dictionary with comparative sentiment analysis
        """
        logger.info("Comparing Bitcoin vs global economy sentiment")
        
        bitcoin_sentiment = self.get_average_sentiment(
            config.BITCOIN_ARTICLES_COLLECTION
        )
        
        global_economy_sentiment = self.get_average_sentiment(
            config.GLOBAL_ECONOMY_ARTICLES_COLLECTION
        )
        
        # Calculate sentiment difference (Bitcoin - Global Economy)
        sentiment_diff = {
            'vader_compound_diff': bitcoin_sentiment['vader_compound'] - global_economy_sentiment['vader_compound'],
            'textblob_polarity_diff': bitcoin_sentiment['textblob_polarity'] - global_economy_sentiment['textblob_polarity'],
            'combined_score_diff': bitcoin_sentiment['combined_score'] - global_economy_sentiment['combined_score']
        }
        
        return {
            'bitcoin': bitcoin_sentiment,
            'global_economy': global_economy_sentiment,
            'difference': sentiment_diff,
            'timestamp': pd.Timestamp.now()
        }

def analyze_and_print_sentiment():
    """Analyze sentiment and print results."""
    analyzer = SentimentAnalyzer()
    comparison = analyzer.compare_bitcoin_vs_global_economy_sentiment()
    
    print("\n--- Sentiment Analysis Results ---")
    print(f"Bitcoin Sentiment (from {comparison['bitcoin']['article_count']} articles):")
    print(f"  VADER Compound: {comparison['bitcoin']['vader_compound']:.4f}")
    print(f"  TextBlob Polarity: {comparison['bitcoin']['textblob_polarity']:.4f}")
    print(f"  Combined Score: {comparison['bitcoin']['combined_score']:.4f}")
    
    print(f"\nGlobal Economy Sentiment (from {comparison['global_economy']['article_count']} articles):")
    print(f"  VADER Compound: {comparison['global_economy']['vader_compound']:.4f}")
    print(f"  TextBlob Polarity: {comparison['global_economy']['textblob_polarity']:.4f}")
    print(f"  Combined Score: {comparison['global_economy']['combined_score']:.4f}")
    
    print("\nDifference (Bitcoin - Global Economy):")
    print(f"  VADER Compound Diff: {comparison['difference']['vader_compound_diff']:.4f}")
    print(f"  TextBlob Polarity Diff: {comparison['difference']['textblob_polarity_diff']:.4f}")
    print(f"  Combined Score Diff: {comparison['difference']['combined_score_diff']:.4f}")
    
    if comparison['difference']['combined_score_diff'] > 0:
        print("\nResult: Bitcoin sentiment is more positive than global economy sentiment")
    elif comparison['difference']['combined_score_diff'] < 0:
        print("\nResult: Global economy sentiment is more positive than Bitcoin sentiment")
    else:
        print("\nResult: Bitcoin and global economy sentiment are approximately equal")

if __name__ == "__main__":
    analyze_and_print_sentiment()
