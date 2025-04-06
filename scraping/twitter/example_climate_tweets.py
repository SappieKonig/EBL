#!/usr/bin/env python3
"""
Example script: Gather climate change tweets from different countries
This script demonstrates using the TwitterCountryScraper to collect tweets
about climate change from multiple countries and perform a simple analysis.
"""

import os
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
from twitter_country_scraper_advanced import TwitterCountryScraper

# Countries to analyze for climate change discussions
COUNTRIES = [
    "United States",
    "United Kingdom",
    "Canada",
    "Australia",
    "India",
    "Germany",
    "France",
    "Brazil"
]

# Keywords related to climate change
CLIMATE_KEYWORDS = "climate OR warming OR sustainability OR carbon OR emissions OR renewable"

# Output directory
OUTPUT_DIR = "data/climate_tweets"


def gather_climate_tweets():
    """Gather climate change tweets from multiple countries"""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Initialize the Twitter scraper
    scraper = TwitterCountryScraper(data_folder=OUTPUT_DIR)
    
    try:
        # Setup browser and wait for manual login
        scraper.setup_browser()
        scraper.goto_twitter()
        
        # Track all tweet dataframes for combined analysis
        all_dfs = []
        
        # Scrape tweets for each country
        for country in COUNTRIES:
            print(f"\n{'='*50}")
            print(f"Scraping climate change tweets for {country}...")
            print(f"{'='*50}")
            
            tweets = scraper.search_by_country(
                country_name=country,
                language="en",  # English tweets only
                limit=100,  # Limit per country
                keywords=CLIMATE_KEYWORDS,
                date_since="2023-01-01"  # Tweets from 2023 onwards
            )
            
            if tweets:
                # Save tweets to CSV
                csv_path = scraper.save_tweets(tweets, f"{country}_climate", format="csv")
                
                # Load CSV into dataframe for analysis
                df = pd.read_csv(csv_path)
                df['country'] = country  # Ensure country column is set
                all_dfs.append(df)
                
                print(f"Collected {len(tweets)} climate tweets from {country}")
            else:
                print(f"No climate tweets found for {country}")
        
        # Combine all tweets for analysis
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            combined_path = os.path.join(OUTPUT_DIR, "all_countries_climate.csv")
            combined_df.to_csv(combined_path, index=False)
            print(f"\nSaved combined dataset with {len(combined_df)} tweets to {combined_path}")
            
            return combined_df
        
    finally:
        # Clean up resources
        scraper.close()


def analyze_climate_tweets(df):
    """Perform basic analysis on collected climate tweets"""
    if df is None or len(df) == 0:
        print("No tweets to analyze")
        return
    
    print("\n\n" + "="*80)
    print("CLIMATE TWEET ANALYSIS")
    print("="*80)
    
    # 1. Count tweets by country
    country_counts = df['country'].value_counts()
    print("\nTweet count by country:")
    for country, count in country_counts.items():
        print(f"  {country}: {count} tweets")
    
    # 2. Extract and count all hashtags
    all_hashtags = []
    for hashtags_str in df['hashtags'].dropna():
        if hashtags_str:  # Skip empty strings
            all_hashtags.extend(hashtags_str.split(','))
    
    # Get top 15 hashtags
    hashtag_counter = Counter(all_hashtags)
    top_hashtags = hashtag_counter.most_common(15)
    
    print("\nTop 15 climate hashtags:")
    for hashtag, count in top_hashtags:
        print(f"  #{hashtag}: {count} mentions")
    
    # 3. Create visualizations
    output_dir = os.path.join(OUTPUT_DIR, "analysis")
    os.makedirs(output_dir, exist_ok=True)
    
    # Bar chart of tweets by country
    plt.figure(figsize=(12, 6))
    country_counts.plot(kind='bar', color='skyblue')
    plt.title('Climate Change Tweets by Country')
    plt.xlabel('Country')
    plt.ylabel('Number of Tweets')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'tweets_by_country.png'))
    
    # Pie chart of top hashtags
    plt.figure(figsize=(12, 12))
    labels = [f"#{h}" for h, _ in top_hashtags]
    values = [count for _, count in top_hashtags]
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title('Top Climate Change Hashtags')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'top_hashtags_pie.png'))
    
    print(f"\nSaved analysis visualizations to {output_dir}")


if __name__ == "__main__":
    print("Climate Change Tweet Analysis")
    print("============================")
    
    # Check if we already have the combined dataset
    combined_path = os.path.join(OUTPUT_DIR, "all_countries_climate.csv")
    
    if os.path.exists(combined_path):
        print(f"Found existing dataset at {combined_path}")
        user_input = input("Use existing data? (y/n): ").lower()
        
        if user_input.startswith('y'):
            # Use existing data
            print("Using existing dataset for analysis...")
            df = pd.read_csv(combined_path)
        else:
            # Gather new data
            print("Gathering new climate tweet data...")
            df = gather_climate_tweets()
    else:
        # No existing data, gather new data
        print("No existing dataset found. Gathering climate tweet data...")
        df = gather_climate_tweets()
    
    # Analyze the data
    if df is not None and len(df) > 0:
        analyze_climate_tweets(df)
    else:
        print("No data available for analysis.") 