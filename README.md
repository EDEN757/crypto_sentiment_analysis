# Financial Sentiment Analysis Dashboard

A Python-based dashboard for analyzing sentiment in financial news related to Bitcoin and global economy, with real-time price tracking.

## Project Overview

This project leverages Natural Language Processing (NLP) to analyze sentiment from financial news sources. It collects data from:
- News articles about Bitcoin via NewsAPI
- News articles about global economy via NewsAPI
- Bitcoin price data via Yahoo Finance API
- S&P 500 index price data via Yahoo Finance API

All collected data is stored in a MongoDB database for later analysis and visualization.

## Project Structure

```
crypto_sentiment/
├── config/               # Configuration files
├── data/                 # Local data storage (if needed)
├── logs/                 # Application logs
├── src/                  # Source code
│   ├── __init__.py       # Package initializer
│   ├── config.py         # Configuration loader
│   ├── data_collector.py # Data collection from APIs
│   ├── database.py       # MongoDB connection and operations
│   ├── sentiment_analyzer.py # NLP sentiment analysis
├── tests/                # Unit and integration tests
├── run_collector.py      # Script for collecting data (for crontab)
├── run_sentiment_analysis.py # Script for analyzing sentiment (for crontab)
├── setup_crontab.py      # Helper script for setting up crontab
├── .env                  # Environment variables (not tracked in git)
├── .env.example          # Example environment file (safe to commit)
├── .gitignore            # Git ignore file
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

## Setup Instructions

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on `.env.example` and add your API keys
5. Set up periodic data collection using one of the methods below

## Running on a Linux Server with Crontab (Recommended)

This project is designed to run optimally on a Linux server using crontab for scheduled execution:

1. Make sure all scripts are executable:
   ```
   chmod +x run_collector.py run_sentiment_analysis.py setup_crontab.py
   ```

2. Run the automated crontab setup script:
   ```
   python setup_crontab.py
   ```
   
   This will:
   - Ask for your preferred data collection interval (default: 3 hours)
   - Preview the crontab entries
   - Offer to install the crontab entries automatically or save them to a file

3. Verify your crontab is set up correctly:
   ```
   crontab -l
   ```

4. Monitor the logs in the `logs/` directory:
   ```
   tail -f logs/cron-collector-*.log
   tail -f logs/cron-sentiment-*.log
   ```

The crontab configuration will:
- Run a complete data collection cycle every 3 hours (by default) that:
  - Collects BOTH news articles AND price data in the same run
  - Updates all MongoDB collections with fresh data
  - Creates detailed logs of what was collected
- Run sentiment analysis 30 minutes after each data collection
- Store results in MongoDB and save analysis summary files to the `data/` directory

## Data Collection Cycle

Each 3-hour collection cycle:
1. Collects and stores Bitcoin news articles
2. Collects and stores global economy news articles
3. Collects and stores Bitcoin price data (with precise timestamps)
4. Collects and stores S&P 500 price data (with precise timestamps)

All types of data are collected and stored in a single execution to ensure consistent data points across all collections.

## Manually Running Scripts

You can also run the scripts manually:

- To collect all data types at once (articles and prices):
  ```
  python run_collector.py
  ```

- To analyze sentiment once:
  ```
  python run_sentiment_analysis.py
  ```

## Configuration

The project requires the following API keys:
- NewsAPI key
- MongoDB connection string

Store these in the `.env` file (see `.env.example` for format).

## Data Collection and Storage

The application collects and stores data with accurate timestamps:

### News Articles
- Articles are stored with their original publication datetime (`published_at` field)
- The collection time is also recorded (`stored_at` field)
- Duplicate articles are automatically detected and not re-inserted
- Articles are stored in the following collections:
  - Bitcoin news → `bitcoin_articles` collection
  - Global economy news → `global_economy_articles` collection

### Price Data
- Price data is stored with actual market timestamps (`timestamp` field)
- The collection time is also recorded (`collection_time` field)
- Data includes open, high, low, close prices and volume
- Price data is stored in the following collections:
  - Bitcoin prices → `bitcoin_price` collection
  - S&P 500 index → `sp500` collection
  
### Sentiment Analysis
- Results are stored with their calculation timestamp
- Each result includes scores for both Bitcoin and global economy news
- Results are stored in the `sentiment_results` collection
- Summary JSON files are also saved to the `data/` directory

## MongoDB Connection

The project connects to a MongoDB Atlas free tier cluster. Connection details 
are stored in the `.env` file and loaded via the config module.

## Future Enhancements

- Web dashboard for visualizing sentiment trends
- Real-time sentiment analysis updates
- Additional financial assets and indicators
- Predictive analytics based on sentiment data
