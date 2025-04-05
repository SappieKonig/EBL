# Twitter Country Scraper

This tool automatically scrapes tweets from Twitter/X, with two main functions:
1. Gather tweets by country - collects tweets from specific countries
2. Scrape trending tweets - gets the most viewed tweets from the Explore tab

In both cases, you only need to manually log in, and the bot handles all the scrolling and data collection.

## Features

- Collect tweets by specific countries
- Scrape trending tweets from the Explore tab
- Automatic infinite scrolling to gather large amounts of data
- Extract tweet text, username, timestamp, location, and engagement metrics
- Save data in CSV or JSON formats
- Manual login to avoid detection issues
- Filter by language, keywords, and date ranges
- Extract hashtags and images from tweets
- Analyze engagement statistics and trending hashtags

## Requirements

- Python 3.7+
- Chrome browser installed
- Required Python packages (install using `pip install -r requirements.txt`):
  - selenium
  - pandas
  - webdriver-manager

## Installation

1. Make sure you have Chrome browser installed
2. Install the required Python packages:
```
pip install -r requirements.txt
```

## Usage

### Scraping Trending Tweets (NEW!)

To collect the most viewed tweets from Twitter's Explore tab:

```
python explore_trending_tweets.py
```

This will:
1. Open a Chrome browser for you to log in manually
2. Navigate to the Twitter Explore tab
3. Collect trending tweets by scrolling automatically
4. Analyze and save the data with engagement statistics and hashtag analytics

### Interactive Easy Mode (Countries)

For the simplest experience, run the easy interface script:

```
python easy_tweet_scraper.py
```

This interactive script will:
1. Ask you for all necessary parameters through a user-friendly interface
2. Open a Chrome browser window for you to log in manually
3. Scrape tweets based on your selections
4. Save the data in your preferred format

### Advanced Command-Line Mode

For more control, use the advanced version with command-line arguments:

```
python twitter_country_scraper_advanced.py --countries "United States" "Japan" "Brazil" --limit 200 --language en --keywords "climate change" --date-since 2023-01-01 --output-format json --data-folder custom_data_folder
```

Available command-line options:

- `--countries`: List of countries to scrape tweets from (default: United States, United Kingdom, Canada)
- `--limit`: Maximum number of tweets to collect per country (default: 100)
- `--language`: Language filter (e.g., 'en' for English)
- `--keywords`: Additional keywords to filter by
- `--date-since`: Start date in format YYYY-MM-DD
- `--date-until`: End date in format YYYY-MM-DD
- `--headless`: Run in headless mode (no browser UI)
- `--output-format`: Output format for saving tweets (csv, json, or both)
- `--data-folder`: Directory to save scraped data (default: data/twitter)

### Using as a library

You can also import the `TwitterCountryScraper` class in your own scripts:

```python
from twitter_country_scraper import TwitterCountryScraper

# Initialize the scraper
scraper = TwitterCountryScraper(data_folder="my_twitter_data")

# Setup and login manually
scraper.setup_browser()
scraper.goto_twitter()

# Scrape tweets for a specific country with language filter
tweets = scraper.search_by_country("Japan", language="ja", limit=500)

# Save the tweets
scraper.save_tweets(tweets, "Japan", format="csv")

# Close the browser when done
scraper.close()
```

## Data Format

The scraped tweets contain the following information:

- `id`: Unique identifier for the tweet
- `username`: Twitter username of the author
- `timestamp`: When the tweet was posted
- `text`: Content of the tweet
- `location`: Location information from user profile (for country search)
- `country`: The country used in the search query (for country search)
- `stats`: Engagement metrics (likes, retweets, etc.)
- `hashtags`: List of hashtags used in the tweet
- `image_urls`: URLs of images in the tweet
- `search_query`: The query used to find this tweet (for country search)
- `is_trending`: Whether the tweet appears to be trending (for trending search)
- `source`: Where the tweet was collected from

## Notes

- Twitter/X may change its HTML structure, which could break the scraper. If this happens, the selectors in the code might need to be updated.
- Aggressive scraping may lead to rate limiting or account restrictions. Use responsibly.
- This tool is for educational purposes only.

## Troubleshooting

### "WebDriver.__init__() got multiple values for argument 'options'"
This error has been fixed in the latest version. If you encounter it, make sure you're using the latest code.

### No tweets are being found
Try the following:
- Make sure you're fully logged in to Twitter/X before pressing Enter
- Check that the country name is valid (try "United States" instead of "USA")
- Try different search terms or remove date filters
- Check if Twitter has changed its HTML structure (this happens periodically)

### Browser closes immediately
Make sure you're not running in headless mode. The script is designed to keep the browser visible so you can log in manually.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 