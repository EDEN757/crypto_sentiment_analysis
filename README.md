# Crypto Sentiment Analysis

A scalable system for analyzing sentiment in cryptocurrency and financial news using NewsAPI data and the FinBERT model.

## Project Overview

This project automatically collects financial news and price data every 3 hours and performs sentiment analysis using FinBERT, a pre-trained NLP model specialized for financial text. It collects:

- News articles about Bitcoin (or other configured cryptocurrencies) via NewsAPI
- News articles about global economy via NewsAPI
- Bitcoin price data via Yahoo Finance API
- S&P 500 index price data via Yahoo Finance API

All collected data is stored in MongoDB with precise timestamps, making it ideal for time series analysis and correlation studies.

## Project Structure

```
crypto_sentiment/
├── config/               # Configuration files (app_config.json)
├── data/                 # Local data storage (sentiment analysis results)
├── logs/                 # Application logs
├── models/               # Downloaded models (auto-created)
├── src/                  # Source code
│   ├── __init__.py       
│   ├── config.py         # Configuration loader
│   ├── data_collector.py # Data collection from APIs
│   ├── database.py       # MongoDB connection and operations
│   ├── sentiment_analyzer.py # FinBERT sentiment analysis
├── tests/                # Unit and integration tests
├── run_collector.py      # Script for collecting data (for crontab)
├── run_sentiment_analysis.py # Script for analyzing sentiment (for crontab)
├── setup_crontab.py      # Helper for setting up project and crontab
├── .env                  # Environment variables (not tracked in git)
├── .env.example          # Example environment file
├── .gitignore            
├── requirements.txt      # Project dependencies
└── README.md             # This file
```

## Key Features

- **Flexible Configuration**: Define which cryptocurrencies, indices, and news topics to track using a simple JSON configuration.
- **FinBERT NLP Model**: Uses the state-of-the-art FinBERT sentiment analysis model trained specifically for financial text.
- **Accurate Data Timestamps**: All data is stored with its original publication or market timestamp.
- **Modular Design**: Easy to extend with new data sources, assets, or analysis methods.
- **Automated Collection**: Configurable crontab integration for hands-off operation.
- **Detailed Logging**: Comprehensive logging of all operations for troubleshooting.
- **MongoDB Storage**: Scales well as your data grows over time.

## Setup Instructions

### Prerequisites

- Python 3.8+ 
- MongoDB instance (local or Atlas)
- NewsAPI key (from https://newsapi.org/)
- Linux system with crontab (for automated collection)

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/crypto_sentiment.git
   cd crypto_sentiment
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the setup script to configure your environment:
   ```
   python setup_crontab.py
   ```
   
   This will guide you through:
   - Setting up API keys and MongoDB connection
   - Configuring which assets and news to track
   - Setting up crontab for automated data collection

### Manual Configuration

If you prefer to set things up manually:

1. Create a `.env` file based on `.env.example` with your API keys and MongoDB connection:
   ```
   # API Keys
   NEWS_API_KEY=your_news_api_key_here
   
   # MongoDB Configuration
   MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/
   MONGODB_DATABASE_NAME=crypto_sentiment
   
   # Logging
   LOG_LEVEL=INFO
   
   # Data Collection
   DATA_COLLECTION_INTERVAL_HOURS=3
   ```

2. Create a `config/app_config.json` file to define which assets to track:
   ```json
   {
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
     "collection_interval_hours": 3,
     "sentiment_model": "ProsusAI/finbert"
   }
   ```

3. Make the scripts executable:
   ```
   chmod +x run_collector.py run_sentiment_analysis.py
   ```

4. Set up crontab manually:
   ```
   crontab -e
   ```
   
   Add the following entries:
   ```
   # Crypto Sentiment Analysis - Data Collection (Every 3 hours)
   0 */3 * * * cd /path/to/crypto_sentiment && /path/to/python /path/to/crypto_sentiment/run_collector.py
   
   # Crypto Sentiment Analysis - Sentiment Analysis (30 min after data collection)
   30 */3 * * * cd /path/to/crypto_sentiment && /path/to/python /path/to/crypto_sentiment/run_sentiment_analysis.py
   ```

## Running Manually

You can run the scripts manually:

- To collect all data types at once:
  ```
  python run_collector.py
  ```

- To analyze sentiment:
  ```
  python run_sentiment_analysis.py
  ```

## Data Flow

1. **Collection Phase**:
   - Every 3 hours (configurable), `run_collector.py` runs.
   - News articles and price data are fetched and stored with original timestamps.
   - A lock file prevents concurrent execution.

2. **Analysis Phase**:
   - 30 minutes after collection, `run_sentiment_analysis.py` runs.
   - Any new articles without sentiment scores are analyzed using FinBERT.
   - Results are stored in MongoDB and as JSON files in the `data/` directory.

## Sentiment Analysis

The system uses FinBERT, which provides scores in the range 0-1:
- Score < 0.4: Negative sentiment (bearish)
- Score 0.4-0.6: Neutral sentiment 
- Score > 0.6: Positive sentiment (bullish)

The analysis compares crypto sentiment with global economy sentiment to detect divergences.

## Customization

### Adding More Cryptocurrencies

Edit `config/app_config.json` to add more cryptocurrencies:

```json
"crypto": [
  {
    "name": "Bitcoin",
    "symbol": "BTC-USD",
    "collection": "bitcoin_price",
    "query": "bitcoin OR btc",
    "news_collection": "bitcoin_articles"
  },
  {
    "name": "Ethereum",
    "symbol": "ETH-USD",
    "collection": "ethereum_price",
    "query": "ethereum OR eth",
    "news_collection": "ethereum_articles"
  }
]
```

### Adding More News Topics

Edit the `news_queries` section in `config/app_config.json`:

```json
"news_queries": [
  {
    "name": "Global Economy",
    "query": "global economy OR economic outlook OR financial markets",
    "collection": "global_economy_articles"
  },
  {
    "name": "Central Banks",
    "query": "central bank OR federal reserve OR monetary policy",
    "collection": "central_banks_articles"
  }
]
```

### Changing Collection Interval

Edit the `DATA_COLLECTION_INTERVAL_HOURS` in your `.env` file or `collection_interval_hours` in `app_config.json`.

Then update your crontab:
```
python setup_crontab.py
```

## Troubleshooting

### Check Logs

Log files are stored in the `logs/` directory with filenames like:
- `cron-collector-YYYYMMDD.log` - Data collection logs
- `cron-sentiment-YYYYMMDD.log` - Sentiment analysis logs

### MongoDB Connection Issues

If MongoDB connection fails:
1. Check your connection string in `.env`
2. Ensure network connectivity to your MongoDB server
3. Verify database user permissions

### NewsAPI Limits

The free tier of NewsAPI has some limitations:
- Only news from the last month
- Limited to 100 articles per request
- Rate limited to 100 requests per day

Consider upgrading to a paid plan for production use.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FinBERT](https://github.com/ProsusAI/finBERT) - Financial sentiment analysis model
- [NewsAPI](https://newsapi.org/) - News articles API
- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance market data API