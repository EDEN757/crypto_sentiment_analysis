# Crypto Sentiment Analysis

A scalable system for analyzing sentiment in cryptocurrency and financial news using NewsAPI data and the FinBERT model.

## Project Overview

This project automatically collects financial news and price data every 3 hours and performs sentiment analysis using FinBERT, a pre-trained NLP model specialized for financial text. It collects:

- News articles about Bitcoin (or other configured cryptocurrencies) via NewsAPI
- News articles about global economy via NewsAPI
- Bitcoin price data via Yahoo Finance API
- S&P 500 index price data via Yahoo Finance API

All collected data is stored in MongoDB with precise timestamps, making it ideal for time series analysis and correlation studies. The system is designed to run on a Linux server using crontab for automated data collection and analysis.

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
├── dashboard.py          # FastAPI web dashboard for data visualization
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

- **Streamlined Setup Process**: Interactive setup script that guides you through configuration of all data sources with custom parameters.
- **Flexible Configuration**: Define which cryptocurrencies, indices, and news topics to track using a simple JSON configuration.
- **FinBERT NLP Model**: Uses the state-of-the-art FinBERT sentiment analysis model trained specifically for financial text.
- **Accurate Data Timestamps**: All data is stored with its original publication or market timestamp.
- **Interactive Dashboard**: Web-based visualization of sentiment scores and price data with customizable time ranges, correlation analysis, and asset selection options. Built with FastAPI for a responsive and user-friendly experience.
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
   - Configuring which assets and news to track, including custom delays for each
   - Setting up crontab for automated data collection
   
   The improved setup process allows you to configure all parameters for each asset, cryptocurrency, or news category in one step, including custom delay settings.

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
           "news_collection": "bitcoin_articles",
           "delay_hours": 24
         }
       ],
       "indices": [
         {
           "name": "S&P 500",
           "symbol": "^GSPC",
           "collection": "sp500",
           "delay_hours": 24
         }
       ]
     },
     "news_queries": [
       {
         "name": "Global Economy",
         "query": "global economy OR economic outlook OR financial markets",
         "collection": "global_economy_articles",
         "delay_hours": 24
       }
     ],
     "collection_interval_hours": 3,
     "sentiment_model": "ProsusAI/finbert",
     "articles_per_query": 2,
     "default_delay_hours": 24
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

- To start the dashboard:
  ```
  python dashboard.py
  ```
  
  Access the dashboard at http://your-server-ip:8000/dashboard
  
  The dashboard is implemented using FastAPI and provides an interactive web interface with the following features:
  - Real-time visualization of sentiment scores and cryptocurrency prices
  - Correlation analysis between sentiment and price movements
  - Interactive charts with customizable time ranges (24 hours, 3 days, 7 days, 30 days)
  - Asset selection options (cryptocurrencies and stock indices)
  - Data statistics display showing number of data points and correlation strength

## Data Flow

1. **Collection Phase**:
   - Every 3 hours (configurable), `run_collector.py` runs.
   - For each query, a configurable number of articles (default: 2) are fetched and stored.
   - Each data source (news query, cryptocurrency, index) can have its own custom delay configuration:
     - News articles can be collected with e.g. 24, 48, or 72 hour delays to accommodate API limitations
     - Price data can also use delays to ensure synchronization with news data
   - Articles are always stored with their original publication timestamps to maintain data integrity.
   - The system collects the most recent articles within the specified delay window.
   - A lock file prevents concurrent execution.

2. **Analysis Phase**:
   - 30 minutes after collection, `run_sentiment_analysis.py` runs.
   - Any new articles without sentiment scores are analyzed using FinBERT.
   - Results are stored in MongoDB and as JSON files in the `data/` directory.

## Dashboard

The project includes a comprehensive web dashboard built with FastAPI for visualizing all collected and analyzed data.

### Dashboard Features

- **Interactive Charts**: Dual-axis charts that display both sentiment scores and price data on the same timeline.
- **Correlation Analysis**: Automatically calculates and displays the correlation between sentiment scores and price movements.
- **Asset Selection**: Dropdown menus to choose between different cryptocurrencies and stock indices.
- **Time Range Selection**: Filter data by time periods (24 hours, 3 days, 7 days, or 30 days).
- **Data Statistics**: Display of data point counts and correlation strength with color-coded indicators.
- **Responsive Design**: Accessible from both desktop and mobile devices.

To start the dashboard:
```
python dashboard.py
```

The dashboard will be available at `http://your-server-ip:8000/dashboard`

### Dashboard Technical Details

- Built with FastAPI as the backend web framework
- Uses Matplotlib for generating data visualizations
- Implements JavaScript for interactive elements and dynamic chart updates
- MongoDB queries are optimized for time-range filtering
- Correlation calculation between sentiment and price data

## Sentiment Analysis

The system uses FinBERT, a pre-trained BERT model specialized for financial text, which provides scores in the range 0-1:
- Score < 0.4: Negative sentiment (bearish)
- Score 0.4-0.6: Neutral sentiment 
- Score > 0.6: Positive sentiment (bullish)

The system analyzes both the title and content of each news article, handling texts of any length by splitting them into sentences for processing. It then aggregates these scores to provide an overall sentiment for the article.

The analysis compares crypto sentiment with global economy sentiment to detect divergences, which can be useful for identifying market trends and potential investment opportunities.

## Customization

### Adding/Modifying Data Sources

The easiest way to add or modify data sources is to run the setup script again:

```
python setup_crontab.py
```

When prompted, choose to customize the configuration. The interactive setup will guide you through configuring:
- Crypto assets (Bitcoin, Ethereum, etc.)
- Financial indices (S&P 500, etc.)
- News categories (Global Economy, etc.)

For each data source, you can configure all relevant parameters in one step, including:
- Name and symbol
- Search queries for news articles 
- Collection names for database storage
- Custom delay settings for each source

### Manual Configuration

If you prefer to edit the configuration file directly, you can modify `config/app_config.json`:

#### Adding Cryptocurrencies

```json
"crypto": [
  {
    "name": "Bitcoin",
    "symbol": "BTC-USD",
    "collection": "bitcoin_price",
    "query": "bitcoin OR btc",
    "news_collection": "bitcoin_articles",
    "delay_hours": 24
  },
  {
    "name": "Ethereum",
    "symbol": "ETH-USD",
    "collection": "ethereum_price",
    "query": "ethereum OR eth",
    "news_collection": "ethereum_articles",
    "delay_hours": 24
  }
]
```

#### Adding News Topics

```json
"news_queries": [
  {
    "name": "Global Economy",
    "query": "global economy OR economic outlook OR financial markets",
    "collection": "global_economy_articles",
    "delay_hours": 24
  },
  {
    "name": "Central Banks",
    "query": "central bank OR federal reserve OR monetary policy",
    "collection": "central_banks_articles",
    "delay_hours": 48
  }
]
```

### Global Collection Parameters

You can customize several global collection parameters in `app_config.json`:

1. **Collection Interval**: Change how often data is collected
   ```json
   "collection_interval_hours": 3
   ```

2. **Articles Per Query**: Control how many articles are stored per category each collection cycle
   ```json
   "articles_per_query": 2
   ```

3. **Default Delay Hours**: Set the default historical delay for all data sources
   ```json
   "default_delay_hours": 24
   ```

After making manual changes to the configuration, update your crontab:
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
- 24-hour delay on articles (historical articles only)

To work with these limitations:
1. Configure the delay_hours parameter for each data source to match your NewsAPI tier constraints.
2. For free tier, set delay_hours to at least 24 to work with the historical data limitation.
3. Adjust articles_per_query to limit database growth while maintaining adequate data volume.

Consider upgrading to a paid plan for production use or real-time data needs.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FinBERT](https://github.com/ProsusAI/finBERT) - Financial sentiment analysis model
- [NewsAPI](https://newsapi.org/) - News articles API
- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance market data API