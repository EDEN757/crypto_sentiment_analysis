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
        f"# Financial Sentiment Analysis Dashboard - Data Collection (Every {hours_interval} hours)",
        f"0 */{hours_interval} * * * cd {project_path} && {python_path} {project_path}/run_collector.py",
        f"",
        f"# Financial Sentiment Analysis Dashboard - Sentiment Analysis (30 min after data collection)",
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

def main():
    """Set up crontab for the project."""
    print("Financial Sentiment Analysis Dashboard - Crontab Setup")
    print("====================================================\n")
    print("This script will set up crontab to:")
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
    print("3. Cancel")
    
    choice = input("\nEnter your choice [1]: ") or "1"
    
    if choice == "1":
        if setup_crontab_directly(entries):
            print("\nCrontab successfully configured!")
            print(f"Both news articles AND price data will be collected every {hours_interval} hours.")
            print("You can verify your crontab with: crontab -l")
        else:
            print("\nFailed to configure crontab directly.")
    elif choice == "2":
        save_crontab_entries_to_file(entries)
    else:
        print("\nCancelled. No changes were made to your crontab.")

if __name__ == "__main__":
    main() 