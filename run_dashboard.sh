#!/bin/bash
# Crypto Sentiment Dashboard Service
# This script runs the FastAPI dashboard for crypto sentiment analysis

# Make script executable:
# chmod +x run_dashboard.sh

# Change to the project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set custom port if provided as an argument
PORT=${1:-8000}

# Run the dashboard
python dashboard.py

# Deactivate virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi