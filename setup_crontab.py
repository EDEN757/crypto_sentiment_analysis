#!/usr/bin/env python
"""
Crontab setup helper script.

This script helps configure crontab for running the data collection
and sentiment analysis scripts at regular intervals.
"""

import os
import sys
import subprocess
from pathlib import Path

def get_absolute_path():
    """Get the absolute path of the project directory."""
    return str(Path(__file__).resolve().parent)

def create_crontab_entries(hours_interval=3):
    """Create crontab entries for the data collection and sentiment analysis scripts.
    
    Args:
        hours_interval: Interval in hours for data collection
        
    Returns:
        List of crontab entries
    """
    project_path = get_absolute_path()
    python_path = sys.executable
    
    # Ensure scripts are executable
    os.chmod(os.path.join(project_path, "run_collector.py"), 0o755)
    os.chmod(os.path.join(project_path, "run_sentiment_analysis.py"), 0o755)
    
    # Create crontab entries
    entries = [
        f"# Crypto Sentiment Analysis - Data Collection (Every {hours_interval} hours)",
        f"0 */{hours_interval} * * * cd {project_path} && {python_path} {project_path}/run_collector.py",
        f"",
        f"# Crypto Sentiment Analysis - Sentiment Analysis (30 min after data collection)",
        f"30 */{hours_interval} * * * cd {project_path} && {python_path} {project_path}/run_sentiment_analysis.py"
    ]
    
    return entries

def preview_crontab_entries(entries):
    """Preview the crontab entries."""
    print("\n=== Crontab Configuration ===\n")
    for entry in entries:
        print(entry)
    print("\nThese entries will run:")
    print(f"1. Data collection on the hour (every {entries[0].split('(Every ')[1].split(' hours)')[0]} hours)")
    print(f"   - This collects BOTH news articles AND price data in the same run")
    print(f"2. Sentiment analysis 30 minutes after data collection")
    print(f"   - This analyzes sentiment with FinBERT and stores results")

def save_crontab_entries_to_file(entries, filename="crontab_config.txt"):
    """Save the crontab entries to a file.
    
    Args:
        entries: List of crontab entries
        filename: Name of the file to save to
    """
    project_path = get_absolute_path()
    file_path = os.path.join(project_path, filename)
    
    with open(file_path, "w") as f:
        for entry in entries:
            f.write(f"{entry}\n")
    
    print(f"\nCrontab configuration saved to: {file_path}")
    print("You can add these entries to your crontab with the following command:")
    print(f"crontab -l | cat - {file_path} | crontab -")

def setup_crontab_directly(entries):
    """Set up crontab directly using the crontab command.
    
    Args:
        entries: List of crontab entries
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get existing crontab
        try:
            existing_crontab = subprocess.check_output("crontab -l", shell=True, text=True)
        except subprocess.CalledProcessError:
            # No existing crontab
            existing_crontab = ""
        
        # Append new entries
        new_crontab = existing_crontab + "\n" + "\n".join(entries) + "\n"
        
        # Write to temporary file
        temp_file = os.path.join(get_absolute_path(), "temp_crontab.txt")
        with open(temp_file, "w") as f:
            f.write(new_crontab)
        
        # Install new crontab
        try:
            subprocess.run(f"crontab {temp_file}", shell=True, check=True)
            os.remove(temp_file)
            return True
        except subprocess.CalledProcessError:
            print(f"Failed to set up crontab. Crontab configuration saved to: {temp_file}")
            return False
    except Exception as e:
        print(f"Error setting up crontab: {str(e)}")
        return False

def setup_environment_file():
    """Create or update the .env file with required API keys."""
    project_path = get_absolute_path()
    env_file = os.path.join(project_path, ".env")
    env_example_file = os.path.join(project_path, ".env.example")
    
    # Create .env.example file if it doesn't exist
    if not os.path.exists(env_example_file):
        with open(env_example_file, "w") as f:
            f.write("# API Keys\n")
            f.write("NEWS_API_KEY=your_news_api_key_here\n\n")
            f.write("# MongoDB Configuration\n")
            f.write("MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/\n")
            f.write("MONGODB_DATABASE_NAME=crypto_sentiment\n\n")
            f.write("# Logging\n")
            f.write("LOG_LEVEL=INFO\n\n")
            f.write("# Data Collection\n")
            f.write("DATA_COLLECTION_INTERVAL_HOURS=3\n")
    
    # Check if .env file exists
    if os.path.exists(env_file):
        print("\n.env file already exists. Do you want to update it? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("Skipping .env file setup.")
            return
    
    # Get API keys from user
    print("\n=== Environment Configuration ===")
    print("Please provide the following API keys and configuration:")
    
    news_api_key = input("NewsAPI Key: ").strip()
    mongodb_conn = input("MongoDB Connection String: ").strip()
    mongodb_db = input("MongoDB Database Name [crypto_sentiment]: ").strip() or "crypto_sentiment"
    
    # Write to .env file
    with open(env_file, "w") as f:
        f.write(f"# API Keys\n")
        f.write(f"NEWS_API_KEY={news_api_key}\n\n")
        f.write(f"# MongoDB Configuration\n")
        f.write(f"MONGODB_CONNECTION_STRING={mongodb_conn}\n")
        f.write(f"MONGODB_DATABASE_NAME={mongodb_db}\n\n")
        f.write(f"# Logging\n")
        f.write(f"LOG_LEVEL=INFO\n\n")
        f.write(f"# Data Collection\n")
        f.write(f"DATA_COLLECTION_INTERVAL_HOURS=3\n")
    
    # Make sure .env is in .gitignore
    gitignore_file = os.path.join(project_path, ".gitignore")
    env_in_gitignore = False
    
    if os.path.exists(gitignore_file):
        with open(gitignore_file, "r") as f:
            content = f.read()
            env_in_gitignore = ".env" in content
    
    if not env_in_gitignore:
        with open(gitignore_file, "a") as f:
            f.write("\n# Environment variables\n.env\n")
    
    print("\n.env file has been created and added to .gitignore")

def setup_config_directory():
    """Create and set up the config directory with app_config.json."""
    project_path = get_absolute_path()
    config_dir = os.path.join(project_path, "config")
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, "app_config.json")
    
    # Check if config file exists
    if os.path.exists(config_file):
        print("\nConfig file already exists. Do you want to update it? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            print("Skipping config file setup.")
            return
    
    # Create default config
    default_config = {
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
    
    # Ask user if they want to customize config
    print("\n=== Configuration Setup ===")
    print("Do you want to customize the default configuration? (y/n)")
    response = input().strip().lower()
    
    if response == 'y':
        # Define function to collect asset details with consistent UI
        def get_asset_details(asset_type, default_values=None):
            """Collect details for an asset with consistent UI.
            
            Args:
                asset_type: Type of asset ('crypto', 'index', or 'news')
                default_values: Dictionary with default values
                
            Returns:
                Dictionary with asset details
            """
            defaults = default_values or {}
            details = {}
            
            # Common fields for all asset types
            details["name"] = defaults.get("name") or input(f"{asset_type.title()} name: ").strip()
            
            # Asset-specific fields
            if asset_type == 'crypto':
                details["symbol"] = defaults.get("symbol") or input(f"{details['name']} symbol (Yahoo Finance, e.g. BTC-USD): ").strip()
                details["collection"] = defaults.get("collection") or f"{details['name'].lower().replace(' ', '_')}_price"
                details["query"] = defaults.get("query") or input(f"{details['name']} search query: ").strip()
                details["news_collection"] = defaults.get("news_collection") or f"{details['name'].lower().replace(' ', '_')}_articles"
            elif asset_type == 'index':
                details["symbol"] = defaults.get("symbol") or input(f"{details['name']} symbol (Yahoo Finance, e.g. ^GSPC): ").strip()
                details["collection"] = defaults.get("collection") or f"{details['name'].lower().replace(' ', '_')}_price"
            elif asset_type == 'news':
                details["query"] = defaults.get("query") or input(f"{details['name']} search query: ").strip()
                details["collection"] = defaults.get("collection") or f"{details['name'].lower().replace(' ', '_')}_articles"
            
            # Common delay setting for all types
            delay_value = defaults.get("delay_hours", config.DEFAULT_DELAY_HOURS) 
            delay_prompt = f"{details['name']} data delay in hours [{delay_value}]: "
            delay_input = input(delay_prompt).strip() or str(delay_value)
            details["delay_hours"] = int(delay_input) if delay_input.isdigit() else delay_value
            
            return details

        # Customize crypto assets
        print("\nCrypto assets configuration:")
        
        # First, modify the default Bitcoin asset
        print("\nConfigure the default Bitcoin asset:")
        bitcoin_defaults = default_config["assets"]["crypto"][0]
        bitcoin_details = get_asset_details('crypto', bitcoin_defaults)
        default_config["assets"]["crypto"][0] = bitcoin_details
        
        # Ask if user wants to add more crypto assets
        print("\nDo you want to add another crypto asset? (y/n)")
        add_crypto = input().strip().lower() == 'y'
        
        while add_crypto:
            crypto_details = get_asset_details('crypto')
            default_config["assets"]["crypto"].append(crypto_details)
            
            print("\nDo you want to add another crypto asset? (y/n)")
            add_crypto = input().strip().lower() == 'y'
        
        # Customize indices
        print("\nDo you want to add another index? (y/n)")
        add_index = input().strip().lower() == 'y'
        
        while add_index:
            index_details = get_asset_details('index')
            default_config["assets"]["indices"].append(index_details)
            
            print("\nDo you want to add another index? (y/n)")
            add_index = input().strip().lower() == 'y'
        
        # Customize news queries
        print("\nDo you want to add another news query? (y/n)")
        add_query = input().strip().lower() == 'y'
        
        while add_query:
            news_details = get_asset_details('news')
            default_config["news_queries"].append(news_details)
            
            print("\nDo you want to add another news query? (y/n)")
            add_query = input().strip().lower() == 'y'
        
        # Customize collection interval
        interval = input("\nData collection interval in hours [3]: ").strip()
        if interval and interval.isdigit():
            default_config["collection_interval_hours"] = int(interval)
            
        # Customize articles per query
        articles_count = input("\nNumber of articles to collect per query [2]: ").strip()
        if articles_count and articles_count.isdigit():
            default_config["articles_per_query"] = int(articles_count)
            
        # Customize default delay
        default_delay = input("\nDefault data delay in hours for new sources [24]: ").strip()
        if default_delay and default_delay.isdigit():
            default_config["default_delay_hours"] = int(default_delay)
    
    # Write config to file
    with open(config_file, "w") as f:
        import json
        json.dump(default_config, f, indent=2)
    
    print(f"\nConfiguration has been saved to: {config_file}")

def main():
    """Set up the project for deployment."""
    print("Crypto Sentiment Analysis - Setup")
    print("====================================================\n")
    print("This script will help you set up and configure the project.")
    print("It will guide you through the following steps:")
    print("1. Set up environment variables (.env file)")
    print("2. Configure data sources and assets")
    print("3. Set up crontab for automated data collection and analysis\n")
    
    # Set up environment file
    setup_environment_file()
    
    # Set up config directory
    setup_config_directory()
    
    # Set up crontab
    print("\n=== Crontab Setup ===")
    print("This will set up crontab to:")
    print("1. Collect BOTH news articles AND price data every X hours")
    print("2. Run sentiment analysis 30 minutes after data collection\n")
    
    # Get hours interval
    try:
        hours_interval = int(input("Enter the interval in hours for data collection [3]: ") or "3")
        if hours_interval < 1 or hours_interval > 24:
            print("Interval must be between 1 and 24 hours. Using default of 3 hours.")
            hours_interval = 3
    except ValueError:
        print("Invalid input. Using default of 3 hours.")
        hours_interval = 3
    
    # Create crontab entries
    entries = create_crontab_entries(hours_interval)
    preview_crontab_entries(entries)
    
    # Ask user how to proceed
    print("\nHow would you like to proceed?")
    print("1. Add to crontab directly")
    print("2. Save to file for manual addition")
    print("3. Skip crontab setup")
    
    choice = input("\nEnter your choice [1]: ") or "1"
    
    if choice == "1":
        if setup_crontab_directly(entries):
            print("\nCrontab successfully configured!")
            print(f"Data will be collected every {hours_interval} hours.")
            print("You can verify your crontab with: crontab -l")
        else:
            print("\nFailed to configure crontab directly.")
    elif choice == "2":
        save_crontab_entries_to_file(entries)
    else:
        print("\nSkipping crontab setup.")
    
    print("\n=== Setup Complete ===")
    print("The project has been set up successfully. You can now:")
    print("1. Run the data collector manually: python run_collector.py")
    print("2. Run the sentiment analyzer manually: python run_sentiment_analysis.py")
    print("3. Wait for crontab to run these scripts automatically")
    print("\nEdit the config/app_config.json file to customize data sources and assets.")

if __name__ == "__main__":
    main()