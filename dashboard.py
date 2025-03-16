#!/usr/bin/env python
"""
Cryptocurrency Sentiment Analysis Dashboard

This script provides a web dashboard for visualizing sentiment and price data
collected by the crypto_sentiment system. It uses FastAPI to serve the dashboard
and connects to MongoDB to retrieve the data.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any, Optional

# Ensure proper path resolution
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# FastAPI and web dependencies
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Data visualization
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from io import BytesIO
import base64

# Import project modules
from src.database import db_client
from src import config

# Create FastAPI app
app = FastAPI(title="Crypto Sentiment Dashboard")

# Define the port
PORT = 8000  # Change this to your desired port

# Create static directory if it doesn't exist
STATIC_DIR = BASE_DIR / "static"
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_available_assets() -> Dict[str, List[str]]:
    """Get list of available assets from config."""
    assets = {
        "crypto": [],
        "indices": [],
        "news": []
    }
    
    # Get crypto assets
    for crypto in config.DEFAULT_CONFIG["assets"]["crypto"]:
        assets["crypto"].append({
            "name": crypto["name"],
            "collection": crypto["collection"],
            "news_collection": crypto.get("news_collection", "")
        })
    
    # Get indices
    for index in config.DEFAULT_CONFIG["assets"]["indices"]:
        assets["indices"].append({
            "name": index["name"],
            "collection": index["collection"]
        })
    
    # Get news queries
    for news in config.DEFAULT_CONFIG["news_queries"]:
        assets["news"].append({
            "name": news["name"],
            "collection": news["collection"]
        })
    
    return assets

def get_sentiment_data(collection_name: str, days: int) -> List[Dict[str, Any]]:
    """Get sentiment data for a collection over a specified number of days.
    
    Args:
        collection_name: MongoDB collection name for sentiment data
        days: Number of days to look back
        
    Returns:
        List of sentiment data documents
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Query MongoDB for articles with sentiment in the date range
    articles = db_client.db[collection_name].find({
        "sentiment": {"$exists": True},
        "published_at": {"$gte": start_date, "$lte": end_date}
    }).sort("published_at", 1)  # Sort by date ascending
    
    return list(articles)

def get_price_data(collection_name: str, days: int) -> List[Dict[str, Any]]:
    """Get price data for an asset over a specified number of days.
    
    Args:
        collection_name: MongoDB collection name for price data
        days: Number of days to look back
        
    Returns:
        List of price data documents
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Query MongoDB for price data in the date range
    prices = db_client.db[collection_name].find({
        "timestamp": {"$gte": start_date, "$lte": end_date}
    }).sort("timestamp", 1)  # Sort by date ascending
    
    return list(prices)

def create_visualization(asset_name: str, price_collection: str, 
                         news_collection: str, days: int) -> dict:
    """Create visualization of sentiment and price data.
    
    Args:
        asset_name: Name of the asset
        price_collection: MongoDB collection name for price data
        news_collection: MongoDB collection name for sentiment data
        days: Number of days to look back
        
    Returns:
        Dictionary with base64 encoded image and data counts
    """
    # Get data
    sentiment_data = get_sentiment_data(news_collection, days)
    price_data = get_price_data(price_collection, days)
    
    # Store counts
    data_counts = {
        "sentiment_count": len(sentiment_data),
        "price_count": len(price_data),
        "days": days,
        "correlation": None  # Will be calculated if enough data
    }
    
    # Create DataFrame for sentiment data
    sentiment_df = pd.DataFrame([
        {"date": doc["published_at"], "score": doc["sentiment"]["score"]} 
        for doc in sentiment_data if "sentiment" in doc and "score" in doc["sentiment"]
    ])
    
    # Create DataFrame for price data
    price_df = pd.DataFrame([
        {"date": doc["timestamp"], "price": doc["price"]} 
        for doc in price_data if "price" in doc
    ])
    
    if sentiment_df.empty or price_df.empty:
        # If no data, create a placeholder image
        plt.figure(figsize=(10, 6))
        plt.title(f"No data available for {asset_name} in the last {days} days")
        plt.text(0.5, 0.5, "No data found", horizontalalignment='center', 
                 verticalalignment='center', transform=plt.gca().transAxes)
        plt.tight_layout()
        
        # Save to BytesIO
        img_bytes = BytesIO()
        plt.savefig(img_bytes, format='png')
        plt.close()
        img_bytes.seek(0)
        
        # Convert to base64 for HTML embedding
        img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
        
        # Return both the image and data counts
        return {
            "image": img_base64,
            "counts": data_counts
        }
    
    # Group sentiment by day and calculate mean
    if not sentiment_df.empty:
        sentiment_df['date'] = pd.to_datetime(sentiment_df['date'])
        sentiment_df = sentiment_df.set_index('date')
        # Resample to daily frequency and fill missing values
        daily_sentiment = sentiment_df.resample('D').mean()
        # Fill NaN values using forward fill, then backward fill for any remaining NaNs
        daily_sentiment = daily_sentiment.fillna(method='ffill').fillna(method='bfill')
    
    # Process price data
    if not price_df.empty:
        price_df['date'] = pd.to_datetime(price_df['date'])
        price_df = price_df.set_index('date')
        
    # Calculate correlation if both dataframes have data
    if not sentiment_df.empty and not price_df.empty and len(sentiment_df) >= 3 and len(price_df) >= 3:
        try:
            # Resample both to daily frequency to align the data
            daily_sentiment = sentiment_df.resample('D').mean()
            daily_price = price_df.resample('D').mean()
            
            # Align the indexes and dropna
            joined = pd.concat([daily_sentiment, daily_price], axis=1).dropna()
            
            if len(joined) >= 3:  # Need at least 3 points for meaningful correlation
                correlation = joined['score'].corr(joined['price'])
                data_counts["correlation"] = round(correlation, 3)
                logger.info(f"Calculated correlation for {asset_name}: {correlation}")
            else:
                logger.info(f"Not enough aligned data points for correlation calculation")
        except Exception as e:
            logger.error(f"Error calculating correlation: {str(e)}")
            data_counts["correlation"] = None
    
    # Create the visualization
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Plot sentiment data
    if not sentiment_df.empty:
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Sentiment Score (0-1)', color='blue')
        ax1.plot(daily_sentiment.index, daily_sentiment['score'], 'b-', label='Sentiment Score')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1.set_ylim([0, 1])  # Sentiment score range
        ax1.grid(True, alpha=0.3)
    
    # Create a second y-axis for price
    if not price_df.empty:
        ax2 = ax1.twinx()
        ax2.set_ylabel('Price (USD)', color='red')
        ax2.plot(price_df.index, price_df['price'], 'r-', label='Price')
        ax2.tick_params(axis='y', labelcolor='red')
        ax2.grid(False)
    
    # Set x-axis date format
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    
    # Add title and legend
    title = f'{asset_name} Sentiment and Price - Last {days} Days'
    if data_counts["correlation"] is not None:
        title += f' (Correlation: {data_counts["correlation"]})'
    plt.title(title)
    lines1, labels1 = ax1.get_legend_handles_labels()
    if not price_df.empty:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    else:
        ax1.legend(loc='upper left')
    
    plt.tight_layout()
    
    # Save to BytesIO
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format='png')
    plt.close()
    img_bytes.seek(0)
    
    # Convert to base64 for HTML embedding
    img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
    
    # Return both the image and data counts
    return {
        "image": img_base64,
        "counts": data_counts
    }

# API Routes

@app.get("/")
async def root():
    """Redirect to dashboard page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Render the dashboard page."""
    assets = get_available_assets()
    
    crypto_options = ""
    for crypto in assets["crypto"]:
        crypto_options += f'<option value="{crypto["name"]}" data-price="{crypto["collection"]}" data-news="{crypto["news_collection"]}">{crypto["name"]}</option>'
    
    index_options = ""
    for index in assets["indices"]:
        index_options += f'<option value="{index["name"]}" data-price="{index["collection"]}" data-news="">{index["name"]}</option>'
    
    return f"""
    <html>
    <head>
        <title>Crypto Sentiment Dashboard</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            header {{
                background-color: #2c3e50;
                color: white;
                padding: 15px 0;
                text-align: center;
                margin-bottom: 30px;
            }}
            h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .controls {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .control-group {{
                display: flex;
                flex-direction: column;
            }}
            label {{
                margin-bottom: 5px;
                font-weight: bold;
                font-size: 14px;
            }}
            select, button {{
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }}
            button {{
                background-color: #3498db;
                color: white;
                border: none;
                cursor: pointer;
                transition: background-color 0.3s;
                margin-top: 20px;
            }}
            button:hover {{
                background-color: #2980b9;
            }}
            .chart-container {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }}
            .chart-image {{
                width: 100%;
                height: auto;
            }}
            .loading {{
                text-align: center;
                padding: 50px;
                font-size: 18px;
                color: #7f8c8d;
            }}
            .data-stats {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 15px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }}
            .badge {{
                background-color: #3498db;
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
                display: inline-block;
                margin-left: 5px;
            }}
            .badge-red {{
                background-color: #e74c3c;
            }}
            .badge-blue {{
                background-color: #3498db;
            }}
            .badge-green {{
                background-color: #27ae60;
            }}
            .stat-item {{
                font-size: 14px;
                display: flex;
                align-items: center;
            }}
            .error {{
                background-color: #e74c3c;
                color: white;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                display: none;
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>Cryptocurrency Sentiment Analysis Dashboard</h1>
            </div>
        </header>
        
        <div class="container">
            <div class="error" id="errorMessage"></div>
            
            <div class="controls">
                <div class="control-group">
                    <label for="assetType">Asset Type:</label>
                    <select id="assetType" onchange="updateAssetOptions()">
                        <option value="crypto">Cryptocurrencies</option>
                        <option value="index">Stock Indices</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="assetSelect">Select Asset:</label>
                    <select id="assetSelect">
                        {crypto_options}
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="timeRange">Time Range:</label>
                    <select id="timeRange">
                        <option value="1">Last 24 Hours</option>
                        <option value="3">Last 3 Days</option>
                        <option value="7" selected>Last 7 Days</option>
                        <option value="30">Last 30 Days</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <button onclick="updateChart()">Update Chart</button>
                </div>
            </div>
            
            <div class="chart-container">
                <div class="data-stats" id="dataStats" style="display: none;">
                    <div class="stat-item">Time Range: <span id="daysCount" class="badge"></span></div>
                    <div class="stat-item">Price Points: <span id="priceCount" class="badge badge-red"></span></div>
                    <div class="stat-item">Sentiment Articles: <span id="sentimentCount" class="badge badge-blue"></span></div>
                    <div class="stat-item">Correlation: <span id="correlationValue" class="badge badge-green">N/A</span></div>
                </div>
                <div id="loading" class="loading">Loading data...</div>
                <img id="chartImage" class="chart-image" src="" style="display: none;" />
            </div>
        </div>
        
        <script>
            // Store asset options
            const assetOptions = {{
                "crypto": [
                    {json.dumps([{"name": c["name"], "price": c["collection"], "news": c["news_collection"]} for c in assets["crypto"]])}
                ],
                "index": [
                    {json.dumps([{"name": i["name"], "price": i["collection"], "news": ""} for i in assets["indices"]])}
                ]
            }};
            
            function updateAssetOptions() {{
                const assetType = document.getElementById('assetType').value;
                const assetSelect = document.getElementById('assetSelect');
                
                // Clear existing options
                assetSelect.innerHTML = '';
                
                // Add new options based on selected type
                assetOptions[assetType].forEach(asset => {{
                    const option = document.createElement('option');
                    option.value = asset.name;
                    option.dataset.price = asset.price;
                    option.dataset.news = asset.news || "";
                    option.textContent = asset.name;
                    assetSelect.appendChild(option);
                }});
            }}
            
            async function updateChart() {{
                // Show loading
                document.getElementById('loading').style.display = 'block';
                document.getElementById('chartImage').style.display = 'none';
                document.getElementById('errorMessage').style.display = 'none';
                
                // Get selected values
                const assetSelect = document.getElementById('assetSelect');
                const selectedOption = assetSelect.options[assetSelect.selectedIndex];
                
                const assetName = selectedOption.value;
                const priceCollection = selectedOption.dataset.price;
                const newsCollection = selectedOption.dataset.news;
                const days = document.getElementById('timeRange').value;
                
                try {{
                    // Fetch the chart data
                    const response = await fetch(`/api/chart?asset_name=${{encodeURIComponent(assetName)}}&price_collection=${{encodeURIComponent(priceCollection)}}&news_collection=${{encodeURIComponent(newsCollection)}}&days=${{days}}`);
                    
                    if (!response.ok) {{
                        throw new Error(`Error: ${{response.statusText}}`);
                    }}
                    
                    const data = await response.json();
                    
                    // Update chart image
                    document.getElementById('chartImage').src = `data:image/png;base64,${{data.image}}`;
                    document.getElementById('chartImage').style.display = 'block';
                    
                    // Update data count badges
                    document.getElementById('dataStats').style.display = 'flex';
                    document.getElementById('daysCount').textContent = `${{data.counts.days}} days`;
                    document.getElementById('priceCount').textContent = data.counts.price_count;
                    document.getElementById('sentimentCount').textContent = data.counts.sentiment_count;
                    
                    // Update correlation value if available
                    const correlationElement = document.getElementById('correlationValue');
                    if (data.counts.correlation !== null) {
                        correlationElement.textContent = data.counts.correlation;
                        
                        // Change color based on correlation strength
                        if (Math.abs(data.counts.correlation) > 0.7) {
                            correlationElement.className = 'badge ' + (data.counts.correlation > 0 ? 'badge-green' : 'badge-red');
                        } else if (Math.abs(data.counts.correlation) > 0.3) {
                            correlationElement.className = 'badge badge-blue';
                        } else {
                            correlationElement.className = 'badge';
                        }
                    } else {
                        correlationElement.textContent = 'N/A';
                        correlationElement.className = 'badge';
                    }
                }} catch (error) {{
                    // Show error message
                    document.getElementById('errorMessage').textContent = `Failed to load chart: ${{error.message}}`;
                    document.getElementById('errorMessage').style.display = 'block';
                }} finally {{
                    // Hide loading indicator
                    document.getElementById('loading').style.display = 'none';
                }}
            }}
            
            // Initial chart load
            document.addEventListener('DOMContentLoaded', () => {{
                updateChart();
            }});
        </script>
    </body>
    </html>
    """

@app.get("/api/assets")
async def get_assets():
    """API endpoint to get available assets."""
    return get_available_assets()

@app.get("/api/chart")
async def get_chart(
    asset_name: str = Query(..., description="Name of the asset"),
    price_collection: str = Query(..., description="MongoDB collection for price data"),
    news_collection: str = Query("", description="MongoDB collection for news data"),
    days: int = Query(7, description="Number of days to look back")
):
    """API endpoint to get chart image."""
    try:
        # Validate days parameter
        if days not in [1, 3, 7, 30]:
            days = 7
        
        # For indices without news data, show only price
        chart_data = create_visualization(asset_name, price_collection, news_collection, days)
        
        return chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Make sure static dir exists
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    print(f"Starting Crypto Sentiment Dashboard on port {PORT}")
    print(f"Access the dashboard at http://127.0.0.1:{PORT}/dashboard")
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=PORT)