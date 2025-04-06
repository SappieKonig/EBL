#!/usr/bin/env python3
"""
Simple Twitter/X Scraper
------------------------
This script scrolls through any Twitter/X page URL and extracts tweets to a CSV file
with specified columns.
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import re
import csv
import argparse
from webdriver_manager.chrome import ChromeDriverManager

class SimpleTwitterScraper:
    """
    A basic Twitter/X scraper that scrolls through any page and extracts tweets.
    """
    
    def __init__(self, output_file="twitter_data.csv", headless=False):
        """
        Initialize the Twitter scraper.
        
        Args:
            output_file (str): Path to save the CSV output
            headless (bool): Whether to run the browser in headless mode
        """
        self.output_file = output_file
        
        # Create output directory if needed
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Initialize Chrome browser options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--start-maximized")
        self.chrome_options.add_argument("--disable-notifications")
        self.chrome_options.add_argument("--disable-popup-blocking")
        
        # Add user agent to avoid detection
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        if headless:
            self.chrome_options.add_argument("--headless=new")
        
        self.driver = None
        
        # Initialize CSV with required columns
        self.csv_columns = [
            "URLs", "DateTime", "Title", "LangCode", "DocTone", 
            "Location", "CountryCode", "ContextualText"
        ]
        
        # Create empty CSV if it doesn't exist
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_columns, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                print(f"Created new CSV file: {self.output_file}")
    
    def setup_browser(self):
        """Set up the browser for scraping"""
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
    
    def login_to_twitter(self):
        """Navigate to Twitter/X and wait for login"""
        if not self.driver:
            self.setup_browser()
            
        self.driver.get("https://twitter.com/")
        
        print("\n" + "="*50)
        print("PLEASE LOG IN TO TWITTER/X")
        print("="*50)
        print("1. Sign in with your Twitter/X account")
        print("2. Make sure you're fully logged in and can see your timeline")
        print("3. Press Enter in this terminal ONLY after you've successfully logged in")
        print("="*50 + "\n")
        
        # Wait for login to complete (user has to do this manually)
        input("Press Enter once you have successfully logged in to Twitter/X... ")
        print("Thanks! Ready to scrape tweets.")
    
    def scrape_page(self, url, max_tweets=100, scroll_pause=2.0):
        """
        Scrape tweets from the given Twitter/X URL
        
        Args:
            url (str): Twitter URL to scrape
            max_tweets (int): Maximum number of tweets to collect
            scroll_pause (float): Seconds to pause between scrolls
            
        Returns:
            list: List of tweet dictionaries
        """
        if not self.driver:
            print("Browser not initialized. Setting up now...")
            self.setup_browser()
        
        print(f"\nNavigating to {url}")
        self.driver.get(url)
        
        # Wait for page to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main[role='main']"))
            )
            time.sleep(3)  # Additional wait for dynamic content
        except TimeoutException:
            print("Warning: Timed out waiting for page to load")
        
        tweets = []
        scroll_count = 0
        max_scrolls = 100  # Safety limit
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        print("Starting to scroll and collect tweets...")
        print("Progress: ", end="", flush=True)
        
        while len(tweets) < max_tweets and scroll_count < max_scrolls:
            # Try to find tweet elements
            tweet_elements = []
            tweet_selectors = [
                "article[data-testid='tweet']",
                "div[data-testid='cellInnerDiv']",
                "div[data-testid='tweetText']",
                "article[role='article']"
            ]
            
            for selector in tweet_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        tweet_elements = elements
                        break
                except:
                    continue
            
            # Process found tweets
            new_tweets = 0
            for elem in tweet_elements:
                try:
                    # Skip tweets we've already processed based on text
                    tweet_text = ""
                    try:
                        # First try to find the tweet text element
                        text_elem = elem.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
                        tweet_text = text_elem.text
                    except NoSuchElementException:
                        # If that fails, use the whole element text
                        tweet_text = elem.text
                    
                    # Skip if no text or too short
                    if not tweet_text or len(tweet_text.strip()) < 5:
                        continue
                    
                    # Normalize tweet text to ensure consistent processing
                    tweet_text = tweet_text.replace('\n', ' ').replace('\r', ' ')
                    tweet_text = re.sub(r'\s+', ' ', tweet_text).strip()
                        
                    # Skip if we already have this tweet (check first 50 chars)
                    text_start = tweet_text[:50]
                    if any(t["ContextualText"].startswith(text_start) for t in tweets):
                        continue
                    
                    # Extract timestamp
                    timestamp = ""
                    try:
                        time_elements = elem.find_elements(By.TAG_NAME, "time")
                        if time_elements:
                            timestamp = time_elements[0].get_attribute("datetime")
                    except:
                        # Try to find time pattern in text
                        time_pattern = r'\d+[hmd]'
                        matches = re.findall(time_pattern, elem.text)
                        if matches:
                            timestamp = matches[0]
                        else:
                            timestamp = datetime.now().isoformat()
                    
                    # Extract user info for title
                    title = ""
                    try:
                        user_info = elem.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']")
                        if user_info:
                            title = user_info.text.split('\n')[0]
                    except:
                        # Use first line of text as title if no username found
                        title = tweet_text.split('\n')[0]
                    
                    # Create tweet data
                    tweet_data = {
                        "URLs": url,
                        "DateTime": timestamp,
                        "Title": title[:100],  # Limit title length
                        "LangCode": "",  # Not detected
                        "DocTone": "",   # Not detected
                        "Location": "",  # Not detected
                        "CountryCode": "twitter",
                        "ContextualText": tweet_text
                    }
                    
                    tweets.append(tweet_data)
                    new_tweets += 1
                    
                    # Break if we've reached the limit
                    if len(tweets) >= max_tweets:
                        break
                        
                except Exception as e:
                    continue
            
            # Print progress
            print("▼", end="", flush=True)
            if new_tweets > 0:
                print(f"[+{new_tweets}]", end="", flush=True)
            
            # Break if we've reached the limit
            if len(tweets) >= max_tweets:
                break
                
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)  # Wait for content to load
            
            # Check if we've reached the end of the page
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                # Wait a bit longer and try one more scroll
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    print("\nReached end of page or no more tweets loading.")
                    break
                    
            last_height = new_height
        
        print(f"\nCollected {len(tweets)} tweets")
        return tweets
    
    def save_to_csv(self, tweets):
        """
        Save tweets to CSV file
        
        Args:
            tweets (list): List of tweet dictionaries
            
        Returns:
            bool: True if saved successfully
        """
        if not tweets:
            print("No tweets to save.")
            return False
        
        try:
            # Make sure all text is properly cleaned for CSV
            for tweet in tweets:
                # Ensure no newlines or special characters in any field
                for key, value in tweet.items():
                    if isinstance(value, str):
                        # Replace any remaining newlines with spaces
                        tweet[key] = value.replace('\n', ' ').replace('\r', ' ')
                        # Normalize spaces
                        tweet[key] = re.sub(r'\s+', ' ', tweet[key]).strip()
            
            # Append to existing CSV
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_columns, quoting=csv.QUOTE_ALL)
                for tweet in tweets:
                    writer.writerow(tweet)
            
            print(f"Successfully saved {len(tweets)} tweets to {self.output_file}")
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")

    def validate_tweet(self, tweet):
        """
        Validate tweet data and ensure all required fields exist
        
        Args:
            tweet (dict): Tweet dictionary
            
        Returns:
            dict: Validated tweet dictionary
        """
        # Create default values for missing fields
        default_values = {
            "URLs": "",
            "DateTime": datetime.now().isoformat(),
            "Title": "",
            "LangCode": "",
            "DocTone": "",
            "Location": "",
            "CountryCode": "twitter",
            "ContextualText": ""
        }
        
        # Ensure all required fields exist
        for field in self.csv_columns:
            if field not in tweet or not tweet[field]:
                tweet[field] = default_values.get(field, "")
        
        # Ensure all fields are strings with no newlines
        for field in self.csv_columns:
            if not isinstance(tweet[field], str):
                tweet[field] = str(tweet[field])
            
            # Replace newlines and normalize spaces
            tweet[field] = tweet[field].replace('\n', ' ').replace('\r', ' ')
            tweet[field] = re.sub(r'\s+', ' ', tweet[field]).strip()
        
        return tweet


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Simple Twitter/X Scraper')
    parser.add_argument('--url', type=str, help='Twitter/X URL to scrape')
    parser.add_argument('--output', type=str, default='data/twitter_data.csv', help='Output CSV file path')
    parser.add_argument('--max', type=int, default=100, help='Maximum tweets to collect')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--use-predefined', action='store_true', help='Use predefined links')
    parser.add_argument('--strip-content', action='store_true', default=True, 
                        help='Strip URLs and user mentions from tweet content')
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_arguments()
    
    # Print header
    print("\n" + "="*60)
    print(" "*15 + "SIMPLE TWITTER/X SCRAPER" + " "*15)
    print("="*60)
    
    # Predefined links to scrape
    predefined_links = [
        "https://x.com/i/trending/1908554482646233401",
        "https://x.com/i/trending/1908562448812294240",
        "https://x.com/i/trending/1908562447922798690",
        "https://x.com/i/trending/1908590797307670873"
        "https://x.com/search?q=Cramer&src=trend_click&vertical=trends"
    ]
    
    # Get URL if not provided from arguments and not using predefined links
    url = args.url
    if not url and not args.use_predefined:
        url = input("Enter Twitter/X URL to scrape (or press Enter to use predefined links): ").strip()
        if not url:
            print("Using predefined links...")
            use_predefined = True
        else:
            use_predefined = False
    else:
        use_predefined = args.use_predefined
    
    # Initialize scraper
    scraper = SimpleTwitterScraper(output_file=args.output, headless=args.headless)
    
    try:
        # Setup and login
        scraper.setup_browser()
        scraper.login_to_twitter()
        
        all_tweets = []
        
        # Scrape individual URL or predefined links
        if use_predefined:
            print(f"\nScraping {len(predefined_links)} predefined links...")
            
            for i, link in enumerate(predefined_links, 1):
                print(f"\n[{i}/{len(predefined_links)}] Scraping: {link}")
                
                # Fix URL if needed
                if not link.startswith("http"):
                    link = "https://" + link
                
                # Scrape the page with fewer tweets per page to avoid overloading
                tweets_per_page = min(args.max // len(predefined_links), 30)
                tweets = scraper.scrape_page(link, max_tweets=tweets_per_page)
                
                if tweets:
                    all_tweets.extend(tweets)
                    print(f"Got {len(tweets)} tweets from this link")
                
                # Short pause between links
                if i < len(predefined_links):
                    print("Pausing before next link...")
                    time.sleep(3)
        else:
            # Fix URL if needed
            if not url.startswith("http"):
                url = "https://" + url
                
            # Scrape the single provided URL
            all_tweets = scraper.scrape_page(url, max_tweets=args.max)
        
        # Clean and strip the tweet content
        if args.strip_content:
            all_tweets = [scraper.validate_tweet(tweet) for tweet in all_tweets]
        
        # Save results
        scraper.save_to_csv(all_tweets)
        
        print("\n" + "="*60)
        print(f"Scraping completed! {len(all_tweets)} tweets saved to {args.output}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        # Clean up
        scraper.close()


def clean_tweet(tweet):
    """
    Clean and strip unwanted content from tweet text
    
    Args:
        tweet (dict): Tweet dictionary
        
    Returns:
        dict: Cleaned tweet dictionary
    """
    # Make a copy to avoid modifying the original
    cleaned = tweet.copy()
    
    # Clean the contextual text
    text = cleaned.get("ContextualText", "")
    
    if text:
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove user mentions
        text = re.sub(r'@\w+', '', text)
        
        # Replace all newlines with spaces
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Update the tweet
        cleaned["ContextualText"] = text
    
    # Clean the title
    title = cleaned.get("Title", "")
    if title:
        # Remove user handles from title
        title = re.sub(r'@\w+', '', title)
        
        # Replace newlines with spaces
        title = title.replace('\n', ' ').replace('\r', ' ')
        
        # Replace multiple spaces with a single space
        title = re.sub(r'\s+', ' ', title)
        
        # Remove leading/trailing whitespace
        title = title.strip()
        
        cleaned["Title"] = title
    
    return cleaned


if __name__ == "__main__":
    # Check if the script is being run with command-line arguments
    if len(sys.argv) > 1:
        main()
    else:
        # Run with default parameters (use predefined links)
        print("Running with default parameters (predefined links)...")
        sys.argv = [sys.argv[0], "--use-predefined", "--strip-content", "--max=120"]
        main()
