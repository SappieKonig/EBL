import time
import json
import os
import pandas as pd
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from webdriver_manager.chrome import ChromeDriverManager

class TwitterCountryScraper:
    """
    A class to scrape tweets from Twitter/X by country using automated scrolling.
    The user only needs to log in manually, and the bot handles the scrolling and data collection.
    """
    
    def __init__(self, data_folder="data/twitter", headless=False):
        """
        Initialize the Twitter Country Scraper.
        
        Args:
            data_folder (str): Directory to save scraped tweet data
            headless (bool): Whether to run in headless mode
        """
        self.data_folder = data_folder
        os.makedirs(data_folder, exist_ok=True)
        
        # Initialize the Chrome browser
        self.chrome_options = Options()
        self.chrome_options.add_argument("--start-maximized")
        
        # Add user agent to avoid detection as a bot
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Disable notifications and other popups
        self.chrome_options.add_argument("--disable-notifications")
        self.chrome_options.add_argument("--disable-popup-blocking")
        
        # Ensure headless mode is off by default
        self.headless = headless
        if headless:
            self.chrome_options.add_argument("--headless=new")
        
        self.driver = None
        
    def setup_browser(self):
        """Set up the browser for scraping using webdriver manager"""
        # Fixed initialization - ChromeDriverManager().install() returns the path
        service = webdriver.chrome.service.Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
        
    def goto_twitter(self):
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
        print("Thanks! Starting to collect tweets...\n")
        
    def goto_explore_tab(self):
        """Navigate to the Explore tab to see trending topics and tweets"""
        if not self.driver:
            print("Browser not initialized. Setting up now...")
            self.setup_browser()
            self.goto_twitter()
        
        print("\nNavigating to the Explore tab...")
        
        try:
            # Direct navigation is more reliable
            self.driver.get("https://twitter.com/explore")
            print("✓ Navigating directly to Twitter Explore page")
            
            # Wait for the explore page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main[role='main']"))
            )
            
            # Give the page a moment to fully render
            time.sleep(3)
            
            print("✓ Explore page loaded")
            return True
        except Exception as e:
            print(f"Error navigating to Explore tab: {str(e)}")
            return False
    
    def navigate_to_news_topic(self, topic_text):
        """
        Navigate to a specific news topic on the Explore page
        
        Args:
            topic_text (str): Text fragment to identify the news topic
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        if not self.driver:
            print("Browser not initialized. Setting up now...")
            self.setup_browser()
            self.goto_twitter()
            self.goto_explore_tab()
        
        print(f"\nLooking for news topic: '{topic_text}'...")
        
        try:
            # Try to find elements containing the specified text using JavaScript
            script = f"""
            return Array.from(document.querySelectorAll('*')).filter(
                el => el.textContent.includes('{topic_text}')
            );
            """
            elements = self.driver.execute_script(script)
            
            if not elements:
                print(f"Could not find any elements containing '{topic_text}'")
                return False
            
            # Find the most relevant element (closest to a clickable link or headline)
            target_element = None
            for element in elements:
                tag_name = self.driver.execute_script("return arguments[0].tagName", element)
                
                # Prioritize links and headline-like elements
                if tag_name.lower() in ['a', 'h1', 'h2', 'h3', 'span', 'div']:
                    target_element = element
                    
                    # Check if this element or its parent is clickable
                    try:
                        click_script = """
                        let el = arguments[0];
                        // Check up to 3 parent levels for clickable elements
                        for (let i = 0; i < 3; i++) {
                            if (el.tagName === 'A' || el.onclick || el.role === 'button' || 
                                el.getAttribute('data-testid') === 'trend' || 
                                el.classList.contains('r-cursor-pointer')) {
                                return el;
                            }
                            if (!el.parentElement) break;
                            el = el.parentElement;
                        }
                        return arguments[0]; // Return original if no better match
                        """
                        better_element = self.driver.execute_script(click_script, element)
                        if better_element:
                            target_element = better_element
                            break
                    except Exception:
                        # Continue with the current element if script fails
                        pass
            
            if not target_element:
                print(f"Found text '{topic_text}' but couldn't identify a clickable element")
                target_element = elements[0]  # Use the first element as fallback
            
            # Scroll the element into view
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
            time.sleep(1)
            
            # Try clicking the element
            print(f"Clicking on element containing '{topic_text}'...")
            
            # Use JavaScript click which is more reliable
            self.driver.execute_script("arguments[0].click();", target_element)
            
            # Wait for the page to load after clicking
            time.sleep(3)
            
            # Verify we navigated somewhere (URL changed or new content loaded)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
                )
                print(f"✓ Successfully navigated to content related to '{topic_text}'")
                return True
            except:
                print(f"Navigation may have failed - couldn't find tweets for '{topic_text}'")
                return False
                
        except Exception as e:
            print(f"Error navigating to news topic '{topic_text}': {str(e)}")
            return False
    
    def explore_specific_topics(self, topics, limit_per_topic=20):
        """
        Explore specific news topics from the Explore tab
        
        Args:
            topics (list): List of topics to explore
            limit_per_topic (int): Maximum tweets to collect per topic
            
        Returns:
            dict: Dictionary with topic names as keys and tweets as values
        """
        if not self.goto_explore_tab():
            print("Failed to navigate to Explore tab")
            return {}
        
        # Dictionary to store tweets for each topic
        topic_tweets = {}
        
        for topic in topics:
            print(f"\n{'='*60}")
            print(f"EXPLORING TOPIC: {topic}")
            print(f"{'='*60}")
            
            # Navigate to this specific topic
            if self.navigate_to_news_topic(topic):
                # Collect tweets for this topic
                tweets = self.collect_tweets_from_current_view(limit=limit_per_topic, context=topic)
                
                if tweets:
                    print(f"Collected {len(tweets)} tweets related to '{topic}'")
                    topic_tweets[topic] = tweets
                else:
                    print(f"No tweets found for '{topic}'")
                
                # Go back to the Explore tab for the next topic
                self.goto_explore_tab()
                time.sleep(2)  # Wait for Explore page to reload
            else:
                print(f"Could not navigate to topic: '{topic}'")
        
        return topic_tweets
    
    def collect_tweets_from_current_view(self, limit=30, context=""):
        """
        Collect tweets from the current page view
        
        Args:
            limit (int): Maximum number of tweets to collect
            context (str): Context/topic for these tweets
            
        Returns:
            list: Collected tweets data
        """
        print(f"Collecting tweets related to {context}...")
        print("Scroll progress: ", end="", flush=True)
        
        tweets = []
        scroll_count = 0
        max_scrolls = 20  # Safety limit
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while len(tweets) < limit and scroll_count < max_scrolls:
            # Extract tweets from current view
            tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
            new_tweets_found = 0
            
            for tweet_elem in tweet_elements:
                try:
                    # Get the tweet ID - be more defensive about IDs
                    tweet_id = None
                    try:
                        tweet_id = tweet_elem.get_attribute("aria-labelledby")
                    except:
                        # If we can't get the ID, generate a pseudo-ID from content
                        tweet_content = tweet_elem.text[:50]
                        tweet_id = f"pseudo-id-{len(tweets)}-{hash(tweet_content)}"
                    
                    # Skip tweets we've already processed
                    if any(t.get('id') == tweet_id for t in tweets):
                        continue
                    
                    # Extract tweet information
                    username = ""
                    try:
                        username_elem = tweet_elem.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']")
                        username = username_elem.text
                    except:
                        pass
                    
                    timestamp = ""
                    try:
                        time_elems = tweet_elem.find_elements(By.TAG_NAME, "time")
                        if time_elems:
                            timestamp = time_elems[0].get_attribute("datetime")
                    except:
                        pass
                    
                    tweet_text = ""
                    try:
                        text_elem = tweet_elem.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
                        tweet_text = text_elem.text
                    except:
                        # If no tweet text element, try getting the general content
                        tweet_text = tweet_elem.text
                    
                    # Get engagement metrics
                    stats = {}
                    try:
                        stats_elements = tweet_elem.find_elements(By.CSS_SELECTOR, "[data-testid$='-count']")
                        for stat in stats_elements:
                            try:
                                stat_id = stat.get_attribute("data-testid")
                                value = stat.text
                                stats[stat_id] = value
                            except:
                                continue
                    except:
                        pass
                    
                    # Try to get hashtags
                    hashtags = []
                    if tweet_text:
                        hashtag_pattern = r"#(\w+)"
                        hashtags = re.findall(hashtag_pattern, tweet_text)
                    
                    # Build tweet data object
                    tweet_data = {
                        'id': tweet_id,
                        'username': username,
                        'timestamp': timestamp,
                        'text': tweet_text,
                        'stats': stats,
                        'hashtags': hashtags,
                        'topic': context,
                        'source': 'news_topic'
                    }
                    
                    tweets.append(tweet_data)
                    new_tweets_found += 1
                    
                    if len(tweets) >= limit:
                        break
                        
                except Exception as e:
                    continue
            
            if len(tweets) >= limit:
                break
            
            # Print progress indicator
            print("▶", end="", flush=True)
            if new_tweets_found > 0:
                print(f"[+{new_tweets_found}]", end="", flush=True)
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            # Check if we've reached the end of the page
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                # Try one more scroll after a longer wait
                print("(waiting...)", end="", flush=True)
                time.sleep(3)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    print("\nReached end of tweets or no more tweets loading.")
                    break
                    
            last_height = new_height
        
        print(f"\nCollected {len(tweets)} tweets")
        return tweets
    
    def scrape_trending_tweets(self, limit=50, timeframe="24h"):
        """
        Scrape trending/most viewed tweets from the Explore tab
        
        Args:
            limit (int): Maximum number of tweets to collect
            timeframe (str): Time frame for trending (24h, 12h, etc.)
            
        Returns:
            list: Collected trending tweets data
        """
        # Navigate to explore tab
        if not self.goto_explore_tab():
            print("Failed to navigate to Explore tab")
            return []
        
        print(f"\n{'='*60}")
        print(f"SCRAPING TRENDING TWEETS (LAST {timeframe})")
        print(f"{'='*60}")
        
        try:
            # Try to find the trending section
            trending_section = None
            
            # Look for the trending section - different selectors to try
            selectors = [
                "section[aria-labelledby*='trend']", 
                "div[data-testid='trend']",
                "section[role='region']",
                "div[data-testid='primaryColumn']"
            ]
            
            for selector in selectors:
                try:
                    trending_section = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"✓ Found trending section using selector: {selector}")
                    break
                except:
                    continue
            
            if not trending_section:
                print("Could not find trending section, using main content instead")
                trending_section = self.driver.find_element(By.CSS_SELECTOR, "main")
            
            # Collect tweets
            tweets = []
            scroll_count = 0
            max_scrolls = 50  # Safety limit
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            print("\nScroll progress: ", end="", flush=True)
            
            while len(tweets) < limit and scroll_count < max_scrolls:
                # Extract tweets from current view
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                new_tweets_found = 0
                
                for tweet_elem in tweet_elements:
                    try:
                        # Skip tweets we've already processed
                        tweet_id = tweet_elem.get_attribute("aria-labelledby")
                        if any(t.get('id') == tweet_id for t in tweets):
                            continue
                        
                        # Extract tweet information
                        username = tweet_elem.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']").text
                        timestamp = tweet_elem.find_elements(By.TAG_NAME, "time")[0].get_attribute("datetime")
                        
                        try:
                            tweet_text = tweet_elem.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']").text
                        except NoSuchElementException:
                            tweet_text = ""
                        
                        try:
                            # Get engagement metrics
                            stats = {}
                            stats_elements = tweet_elem.find_elements(By.CSS_SELECTOR, "[data-testid$='-count']")
                            for stat in stats_elements:
                                stat_id = stat.get_attribute("data-testid")
                                value = stat.text
                                stats[stat_id] = value
                        except Exception:
                            stats = {}
                        
                        # Try to get hashtags
                        hashtags = []
                        if tweet_text:
                            hashtag_pattern = r"#(\w+)"
                            hashtags = re.findall(hashtag_pattern, tweet_text)
                        
                        # Try to extract image URLs
                        image_urls = []
                        try:
                            img_elements = tweet_elem.find_elements(By.CSS_SELECTOR, "img[alt='Image']")
                            for img in img_elements:
                                src = img.get_attribute("src")
                                if src and "https://" in src:
                                    image_urls.append(src)
                        except Exception:
                            pass
                        
                        # Try to determine if it's trending
                        is_trending = False
                        try:
                            trending_indicators = ["trending", "view", "for you", "recommended"]
                            parent_text = tweet_elem.find_element(By.XPATH, "ancestor::div[3]").text.lower()
                            is_trending = any(indicator in parent_text for indicator in trending_indicators)
                        except:
                            pass
                        
                        tweet_data = {
                            'id': tweet_id,
                            'username': username,
                            'timestamp': timestamp,
                            'text': tweet_text,
                            'stats': stats,
                            'hashtags': hashtags,
                            'image_urls': image_urls,
                            'is_trending': is_trending,
                            'source': 'explore_tab'
                        }
                        
                        tweets.append(tweet_data)
                        new_tweets_found += 1
                        
                        if len(tweets) >= limit:
                            break
                            
                    except Exception as e:
                        print(f"\nError extracting tweet information: {e}")
                        continue
                
                if len(tweets) >= limit:
                    break
                
                # Print progress indicator
                print("▶", end="", flush=True)
                if new_tweets_found > 0:
                    print(f"[+{new_tweets_found}]", end="", flush=True)
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Check if we've reached the end of the page
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_count += 1
                
                if new_height == last_height:
                    # Try one more scroll after a longer wait
                    print("(waiting...)", end="", flush=True)
                    time.sleep(5)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        print("\nReached end of trending tweets or no more tweets loading.")
                        break
                        
                last_height = new_height
            
            print(f"\n\nCollected {len(tweets)} trending tweets")
            return tweets
            
        except Exception as e:
            print(f"Error scraping trending tweets: {str(e)}")
            return []
    
    def search_by_country(self, country_name, language=None, limit=1000, keywords=None, date_since=None, date_until=None):
        """
        Search tweets by country and language.
        
        Args:
            country_name (str): Name of the country to search for
            language (str, optional): Language code to filter by (e.g., 'en' for English)
            limit (int): Maximum number of tweets to collect
            keywords (str, optional): Additional keywords to filter by
            date_since (str, optional): Start date in format YYYY-MM-DD
            date_until (str, optional): End date in format YYYY-MM-DD
            
        Returns:
            list: Collected tweets data
        """
        if not self.driver:
            print("Browser not initialized. Setting up now...")
            self.setup_browser()
            self.goto_twitter()
        
        # Construct search query
        query = f"place:{country_name}"
        
        if language:
            query += f" lang:{language}"
            
        if keywords:
            query += f" {keywords}"
            
        if date_since:
            query += f" since:{date_since}"
            
        if date_until:
            query += f" until:{date_until}"
        
        print(f"\n{'='*60}")    
        print(f"SEARCH QUERY: {query}")
        print(f"{'='*60}")
            
        # Navigate to search URL
        encoded_query = query.replace(" ", "%20")
        search_url = f"https://twitter.com/search?q={encoded_query}&src=typed_query&f=live"
        print(f"Navigating to: {search_url}")
        
        try:
            self.driver.get(search_url)
            
            # Wait for the search results to load
            try:
                print("Waiting for search results to load...")
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
                )
                print("✓ Search results loaded successfully")
            except TimeoutException:
                print(f"\n⚠️ No tweets found for search query: {query}")
                print("This could be because:")
                print("  - The country name may be incorrect")
                print("  - There might not be any tweets for this country with the given filters")
                print("  - Twitter's search functionality might have changed")
                print("\nTrying to continue in case tweets load later...\n")
        
            tweets = []
            scroll_count = 0
            max_scrolls = 100  # Safety limit
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            print(f"Starting to collect tweets for {country_name}...")
            print(f"Will attempt to collect up to {limit} tweets (max {max_scrolls} scrolls)")
            
            # Add a progress indicator
            print("\nScroll progress: ", end="", flush=True)
            
            while len(tweets) < limit and scroll_count < max_scrolls:
                # Extract tweets from current view
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                
                # Show the number of tweets found on this scroll
                new_tweets_found = 0
                
                for tweet_elem in tweet_elements:
                    try:
                        # Skip tweets we've already processed
                        tweet_id = tweet_elem.get_attribute("aria-labelledby")
                        if any(t.get('id') == tweet_id for t in tweets):
                            continue
                        
                        # Extract tweet information
                        username = tweet_elem.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']").text
                        timestamp = tweet_elem.find_elements(By.TAG_NAME, "time")[0].get_attribute("datetime")
                        
                        try:
                            tweet_text = tweet_elem.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']").text
                        except NoSuchElementException:
                            tweet_text = ""
                        
                        try:
                            # Get engagement metrics
                            stats = {}
                            stats_elements = tweet_elem.find_elements(By.CSS_SELECTOR, "[data-testid$='-count']")
                            for stat in stats_elements:
                                stat_id = stat.get_attribute("data-testid")
                                value = stat.text
                                stats[stat_id] = value
                        except Exception:
                            stats = {}
                        
                        # Extract location information when available
                        try:
                            location_elements = tweet_elem.find_elements(By.CSS_SELECTOR, "[data-testid='User-Name'] + div")
                            location = location_elements[0].text if location_elements else ""
                        except Exception:
                            location = ""
                        
                        # Try to extract image URLs
                        image_urls = []
                        try:
                            img_elements = tweet_elem.find_elements(By.CSS_SELECTOR, "img[alt='Image']")
                            for img in img_elements:
                                src = img.get_attribute("src")
                                if src and "https://" in src:
                                    image_urls.append(src)
                        except Exception:
                            pass
                        
                        # Try to get hashtags
                        hashtags = []
                        if tweet_text:
                            hashtag_pattern = r"#(\w+)"
                            hashtags = re.findall(hashtag_pattern, tweet_text)
                        
                        tweet_data = {
                            'id': tweet_id,
                            'username': username,
                            'timestamp': timestamp,
                            'text': tweet_text,
                            'location': location,
                            'country': country_name,
                            'stats': stats,
                            'hashtags': hashtags,
                            'image_urls': image_urls,
                            'search_query': query
                        }
                        
                        tweets.append(tweet_data)
                        new_tweets_found += 1
                        
                        if len(tweets) >= limit:
                            break
                            
                    except Exception as e:
                        print(f"\nError extracting tweet information: {e}")
                        continue
                
                if len(tweets) >= limit:
                    break
                
                # Print progress indicator
                print("▶", end="", flush=True)
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Check if we've reached the end of the page
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_count += 1
                
                if new_tweets_found > 0:
                    print(f"[+{new_tweets_found}]", end="", flush=True)
                
                if new_height == last_height:
                    # Try one more scroll after a longer wait
                    print("(waiting for more tweets...)", end="", flush=True)
                    time.sleep(5)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        print("\nReached end of tweets or no more new tweets loading.")
                        break
                        
                last_height = new_height
            
            print(f"\n\nCollected {len(tweets)} tweets for {country_name}")
            
            if len(tweets) == 0:
                print("\n⚠️ Warning: No tweets were collected. This could be due to:")
                print("  - Twitter's search for this country returned no results")
                print("  - The CSS selectors may have changed (Twitter updates its UI frequently)")
                print("  - There might be an issue with your search query")
            
            return tweets
            
        except Exception as e:
            print(f"\n❌ Error during search: {str(e)}")
            return []
    
    def save_tweets(self, tweets, country_name, format="csv"):
        """
        Save collected tweets to a file.
        
        Args:
            tweets (list): List of tweet data dictionaries
            country_name (str): Name of the country for file naming
            format (str): Output format (csv or json)
            
        Returns:
            str: Path to the saved file
        """
        if not tweets:
            print("No tweets to save.")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{country_name.replace(' ', '_')}_{timestamp}"
        
        if format.lower() == "csv":
            # Flatten the stats dictionary for CSV format
            flattened_tweets = []
            for tweet in tweets:
                tweet_copy = tweet.copy()
                stats = tweet_copy.pop('stats', {})
                for stat_key, stat_value in stats.items():
                    tweet_copy[stat_key] = stat_value
                    
                # Join lists to strings for CSV format
                if 'hashtags' in tweet_copy:
                    tweet_copy['hashtags'] = ','.join(tweet_copy['hashtags'])
                if 'image_urls' in tweet_copy:
                    tweet_copy['image_urls'] = ','.join(tweet_copy['image_urls'])
                    
                flattened_tweets.append(tweet_copy)
                
            df = pd.DataFrame(flattened_tweets)
            output_path = os.path.join(self.data_folder, f"{filename}.csv")
            df.to_csv(output_path, index=False)
            
        elif format.lower() == "json":
            output_path = os.path.join(self.data_folder, f"{filename}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tweets, f, ensure_ascii=False, indent=4)
                
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'json'.")
            
        print(f"Saved {len(tweets)} tweets to {output_path}")
        return output_path
    
    def close(self):
        """Close the browser and clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("Browser closed.")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Scrape tweets by country")
    
    parser.add_argument("--countries", type=str, nargs="+", 
                       default=["United States", "United Kingdom", "Canada"],
                       help="List of countries to scrape tweets from")
    
    parser.add_argument("--limit", type=int, default=100,
                       help="Maximum number of tweets to collect per country")
    
    parser.add_argument("--language", type=str,
                       help="Language filter (e.g., 'en' for English)")
    
    parser.add_argument("--keywords", type=str,
                       help="Additional keywords to filter by")
    
    parser.add_argument("--date-since", type=str,
                       help="Start date in format YYYY-MM-DD")
    
    parser.add_argument("--date-until", type=str,
                       help="End date in format YYYY-MM-DD")
    
    parser.add_argument("--headless", action="store_true",
                       help="Run in headless mode (no browser UI)")
    
    parser.add_argument("--output-format", type=str, choices=["csv", "json", "both"],
                       default="both", help="Output format for saving tweets")
    
    parser.add_argument("--data-folder", type=str, default="data/twitter",
                       help="Directory to save scraped data")
    
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize the scraper
    scraper = TwitterCountryScraper(data_folder=args.data_folder, headless=args.headless)
    
    try:
        # Setup browser and wait for manual login
        scraper.setup_browser()
        scraper.goto_twitter()
        
        # Scrape tweets for each country
        for country in args.countries:
            print(f"\nScraping tweets for {country}...")
            tweets = scraper.search_by_country(
                country_name=country,
                language=args.language,
                limit=args.limit,
                keywords=args.keywords,
                date_since=args.date_since,
                date_until=args.date_until
            )
            
            if tweets:
                # Save based on output format preference
                if args.output_format in ["csv", "both"]:
                    scraper.save_tweets(tweets, country, format="csv")
                if args.output_format in ["json", "both"]:
                    scraper.save_tweets(tweets, country, format="json")
    
    finally:
        # Clean up resources
        scraper.close()


if __name__ == "__main__":
    main() 