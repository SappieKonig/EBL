#!/usr/bin/env python3
"""
Twitter Explore/Trending Tweets Scraper
--------------------------------------
This script scrapes the most viewed tweets from Twitter's Explore tab.
It automatically navigates to the Explore tab and captures trending content.
"""

import os
import sys
import time
import json
import pandas as pd
from datetime import datetime
from twitter_country_scraper_advanced import TwitterCountryScraper
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the program header"""
    print("\n" + "="*70)
    print(" "*15 + "TWITTER TRENDING TWEETS SCRAPER" + " "*15)
    print("="*70)
    print("This tool will scrape the most viewed tweets from Twitter's Explore tab")
    print("You will need to log in to Twitter/X manually when the browser opens")
    print("="*70 + "\n")

def get_tweet_limit():
    """Get the maximum number of tweets to collect"""
    while True:
        try:
            limit = input("Maximum tweets to collect (default: 50): ").strip()
            if not limit:
                return 50
            limit = int(limit)
            if limit <= 0:
                print("Please enter a positive number")
                continue
            return limit
        except ValueError:
            print("Please enter a valid number")

def get_output_format():
    """Get the preferred output format"""
    print("\nOutput format:")
    print("1. CSV")
    print("2. JSON")
    print("3. Both CSV and JSON (default)")
    
    choice = input("Choose an option (1-3): ").strip()
    
    if choice == "1":
        return "csv"
    elif choice == "2":
        return "json"
    else:
        return "both"

def get_output_folder():
    """Get the folder to save output files"""
    folder = input("\nOutput folder (default: data/twitter_trending): ").strip()
    return folder if folder else "data/twitter_trending"

def analyze_top_hashtags(tweets, top_n=10):
    """Analyze and print the top hashtags from the collected tweets"""
    all_hashtags = []
    for tweet in tweets:
        if 'hashtags' in tweet and tweet['hashtags']:
            if isinstance(tweet['hashtags'], list):
                all_hashtags.extend(tweet['hashtags'])
            elif isinstance(tweet['hashtags'], str):
                all_hashtags.extend(tweet['hashtags'].split(','))
    
    # Count hashtag frequencies
    hashtag_counts = {}
    for tag in all_hashtags:
        if tag:  # Skip empty strings
            tag = tag.lower()  # Normalize to lowercase
            if tag in hashtag_counts:
                hashtag_counts[tag] += 1
            else:
                hashtag_counts[tag] = 1
    
    # Sort by count (descending)
    sorted_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Print the top N hashtags
    print("\n" + "="*40)
    print(f"TOP {min(top_n, len(sorted_hashtags))} HASHTAGS")
    print("="*40)
    
    for i, (tag, count) in enumerate(sorted_hashtags[:top_n], 1):
        print(f"{i}. #{tag}: {count} occurrences")

def analyze_engagement(tweets):
    """Analyze and print engagement statistics for the collected tweets"""
    # Initialize counters for different engagement metrics
    likes_count = []
    retweet_count = []
    reply_count = []
    
    for tweet in tweets:
        stats = tweet.get('stats', {})
        
        # Extract engagement metrics, handle both string and dict formats
        if isinstance(stats, dict):
            if 'like-count' in stats:
                try:
                    likes_count.append(int(stats['like-count'].replace(',', '')))
                except (ValueError, AttributeError):
                    pass
                    
            if 'retweet-count' in stats:
                try:
                    retweet_count.append(int(stats['retweet-count'].replace(',', '')))
                except (ValueError, AttributeError):
                    pass
                    
            if 'reply-count' in stats:
                try:
                    reply_count.append(int(stats['reply-count'].replace(',', '')))
                except (ValueError, AttributeError):
                    pass
    
    # Calculate averages
    avg_likes = sum(likes_count) / len(likes_count) if likes_count else 0
    avg_retweets = sum(retweet_count) / len(retweet_count) if retweet_count else 0
    avg_replies = sum(reply_count) / len(reply_count) if reply_count else 0
    
    # Find max values
    max_likes = max(likes_count) if likes_count else 0
    max_retweets = max(retweet_count) if retweet_count else 0
    max_replies = max(reply_count) if reply_count else 0
    
    # Print engagement stats
    print("\n" + "="*40)
    print("ENGAGEMENT STATISTICS")
    print("="*40)
    print(f"Average likes: {avg_likes:.1f}")
    print(f"Average retweets: {avg_retweets:.1f}")
    print(f"Average replies: {avg_replies:.1f}")
    print(f"Maximum likes: {max_likes}")
    print(f"Maximum retweets: {max_retweets}")
    print(f"Maximum replies: {max_replies}")

def main():
    """Main function"""
    clear_screen()
    print_header()
    
    # Get user preferences
    print("What would you like to do?")
    print("1. Scrape general trending tweets")
    print("2. Navigate through news items (Today's News, etc.)")
    print("3. Explore specific news topics")
    print("4. Scrape today's news stories")
    print("5. Specifically target 'Trump's 10% Global Tariff' discussions (NEW!)")
    choice = input("Enter your choice (1-5): ").strip()
    
    limit = get_tweet_limit()
    output_format = get_output_format()
    output_folder = get_output_folder()
    
    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Initialize the scraper
    scraper = TwitterCountryScraper(data_folder=output_folder)
    
    try:
        # Setup browser and wait for manual login
        scraper.setup_browser()
        scraper.goto_twitter()
        
        if choice == "2":
            # Navigate through news items
            explore_news_items(scraper, limit, output_format, output_folder)
        elif choice == "3":
            # Explore specific news topics
            explore_specific_topics(scraper, output_format, output_folder)
        elif choice == "4":
            # Scrape today's news stories
            scrape_todays_news(scraper, limit, output_format, output_folder)
        elif choice == "5":
            # Special mode to target Trump tariff discussions
            scrape_tariff_discussions(scraper, limit, output_format, output_folder)
        else:
            # Default to trending tweets
            scrape_trending_tweets(scraper, limit, output_format, output_folder)
    
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
    
    finally:
        # Clean up resources
        scraper.close()
        print("\n" + "="*50)
        print("SCRAPING COMPLETED")
        print("="*50)

def explore_news_items(scraper, limit, output_format, output_folder):
    """Navigate through specific news items in the Explore tab"""
    # First navigate to the explore tab
    if not scraper.goto_explore_tab():
        print("Failed to navigate to Explore tab")
        return
    
    print("\n" + "="*60)
    print("NAVIGATING THROUGH NEWS ITEMS")
    print("="*60)
    
    # Wait for the explore page to load completely
    time.sleep(3)
    
    try:
        # Look for news category headers or trending news items
        news_items = find_news_items(scraper.driver)
        
        if not news_items:
            print("Could not find specific news items. Looking for trending sections instead...")
            # Try to find trending sections
            sections = scraper.driver.find_elements(By.CSS_SELECTOR, "section[role='region']")
            if sections:
                print(f"Found {len(sections)} general sections")
                news_items = [{"element": section, "title": "General Trending Section"} for section in sections]
            else:
                print("Could not find any news sections. Using main content.")
                main_content = scraper.driver.find_element(By.CSS_SELECTOR, "main")
                news_items = [{"element": main_content, "title": "Main Content"}]
        
        # Process each news item
        all_tweets = []
        for i, news_item in enumerate(news_items, 1):
            title = news_item.get("title", f"News Item {i}")
            print(f"\n{'-'*50}")
            print(f"Exploring: {title}")
            print(f"{'-'*50}")
            
            # Try to click on the news item if it's clickable
            try:
                if "element" in news_item and news_item["element"].is_displayed():
                    # Scroll the item into view
                    scraper.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", news_item["element"])
                    time.sleep(1)
                    
                    # Try to click if it seems to be a link
                    try:
                        links = news_item["element"].find_elements(By.TAG_NAME, "a")
                        if links:
                            print(f"Clicking on link in {title}...")
                            links[0].click()
                            time.sleep(3)
                    except Exception as e:
                        print(f"Could not click on news item: {e}")
                        # Try clicking on the element itself
                        try:
                            news_item["element"].click()
                            time.sleep(3)
                        except:
                            pass
            except Exception as e:
                print(f"Error interacting with news item: {e}")
            
            # Collect tweets from this news topic
            tweets = collect_tweets_from_current_view(scraper.driver, limit=min(limit, 30), context=title)
            
            if tweets:
                print(f"Collected {len(tweets)} tweets related to '{title}'")
                all_tweets.extend(tweets)
                
                # Try to go back if we navigated away
                try:
                    if scraper.driver.current_url != "https://twitter.com/explore":
                        print("Navigating back to Explore tab...")
                        scraper.driver.back()
                        time.sleep(2)
                except:
                    # If going back fails, go directly to explore
                    scraper.goto_explore_tab()
            else:
                print(f"No tweets found for '{title}'")
        
        # Save all collected tweets
        if all_tweets:
            save_tweets(all_tweets, output_format, output_folder, "news_items")
            
            # Analyze the data
            print("\n" + "="*50)
            print("NEWS ITEMS ANALYSIS")
            print("="*50)
            
            # Analyze hashtags
            analyze_top_hashtags(all_tweets)
            
            # Analyze engagement
            analyze_engagement(all_tweets)
        else:
            print("\n⚠️ No tweets were collected from news items")
            
    except Exception as e:
        print(f"Error exploring news items: {str(e)}")

def find_news_items(driver):
    """Find news item sections in the Explore tab"""
    news_items = []
    
    # Look for news headlines - different selectors to try
    headline_selectors = [
        "span:contains('Today's News')",
        "span:contains('Trending now')",
        "span:contains('Trending')",
        "div[data-testid='trend']",
        "a[aria-label*='news']",
        "a[aria-label*='trending']"
    ]
    
    for selector in headline_selectors:
        try:
            # Use JavaScript to find elements by text content
            if ":contains" in selector:
                text = selector.split(":contains('")[1].split("')")[0]
                script = f"""
                return Array.from(document.querySelectorAll('span')).filter(
                    el => el.textContent.includes('{text}')
                );
                """
                elements = driver.execute_script(script)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
            for element in elements:
                # Find the parent container of this news item
                parent = None
                try:
                    # Go up to find a suitable container element
                    parent = element
                    for _ in range(4):  # Try going up 4 levels max
                        if parent.tag_name in ['article', 'div', 'section']:
                            break
                        parent = parent.find_element(By.XPATH, "./..")
                except:
                    parent = element
                
                # Extract the title
                title = element.text
                
                # If we found a news item, add it to our list
                if title and parent:
                    news_items.append({
                        "element": parent,
                        "title": title
                    })
                    print(f"Found news item: {title}")
        except Exception as e:
            pass  # Try next selector if this one fails
    
    # Look specifically for the news items mentioned by the user
    specific_news_items = [
        "Trump's 10% Tariff",
        "Jaland Lowe Transfers to Kentucky",
        "iShowSpeed Experiences Advanced Tech in China"
    ]
    
    for item in specific_news_items:
        try:
            script = f"""
            return Array.from(document.querySelectorAll('*')).filter(
                el => el.textContent.includes('{item}')
            );
            """
            elements = driver.execute_script(script)
            
            for element in elements:
                # Extract the title
                title = element.text
                
                # If we found a news item, add it to our list
                if title:
                    news_items.append({
                        "element": element,
                        "title": item
                    })
                    print(f"Found specific news item: {item}")
                    break  # Just get the first match for each specific item
        except Exception as e:
            pass
    
    return news_items

def collect_tweets_from_current_view(driver, limit=30, context=""):
    """Collect tweets from the current page view"""
    tweets = []
    scroll_count = 0
    max_scrolls = 20  # Safety limit
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    print(f"Collecting tweets related to {context}...")
    print("Scroll progress: ", end="", flush=True)
    
    while len(tweets) < limit and scroll_count < max_scrolls:
        # Extract tweets from current view
        tweet_elements = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
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
                
                tweet_data = {
                    'id': tweet_id,
                    'username': username,
                    'timestamp': timestamp,
                    'text': tweet_text,
                    'stats': stats,
                    'hashtags': hashtags,
                    'image_urls': image_urls,
                    'news_context': context,
                    'source': 'news_item'
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
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load
        
        # Check if we've reached the end of the page
        new_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count += 1
        
        if new_height == last_height:
            # Try one more scroll after a longer wait
            print("(waiting...)", end="", flush=True)
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print("\nReached end of tweets or no more tweets loading.")
                break
                
        last_height = new_height
    
    print(f"\nCollected {len(tweets)} tweets")
    return tweets

def save_tweets(tweets, output_format, output_folder, prefix=""):
    """Save tweets to files in the specified format"""
    if not tweets:
        print("No tweets to save.")
        return None
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{prefix}_" if prefix else ""
    filename = f"{prefix}tweets_{timestamp}"
    
    if output_format in ["csv", "both"]:
        # Flatten the data for CSV
        flattened_tweets = []
        for tweet in tweets:
            tweet_copy = tweet.copy()
            
            # Handle stats dictionary
            stats = tweet_copy.pop('stats', {})
            for stat_key, stat_value in stats.items():
                tweet_copy[stat_key] = stat_value
            
            # Join lists to strings for CSV format
            if 'hashtags' in tweet_copy and isinstance(tweet_copy['hashtags'], list):
                tweet_copy['hashtags'] = ','.join(tweet_copy['hashtags'])
            if 'image_urls' in tweet_copy and isinstance(tweet_copy['image_urls'], list):
                tweet_copy['image_urls'] = ','.join(tweet_copy['image_urls'])
            
            flattened_tweets.append(tweet_copy)
        
        # Save as CSV
        csv_path = os.path.join(output_folder, f"{filename}.csv")
        df = pd.DataFrame(flattened_tweets)
        df.to_csv(csv_path, index=False)
        print(f"\nSaved {len(tweets)} tweets to {csv_path}")
    
    if output_format in ["json", "both"]:
        # Save as JSON
        json_path = os.path.join(output_folder, f"{filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(tweets)} tweets to {json_path}")
    
    return True

def scrape_trending_tweets(scraper, limit, output_format, output_folder):
    """Scrape general trending tweets from the Explore tab"""
    # Original trending tweets functionality
    trending_tweets = scraper.scrape_trending_tweets(limit=limit)
    
    if trending_tweets:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trending_tweets_{timestamp}"
        
        # Save based on output format preference
        if output_format in ["csv", "both"]:
            # Flatten the data for CSV
            flattened_tweets = []
            for tweet in trending_tweets:
                tweet_copy = tweet.copy()
                
                # Handle stats dictionary
                stats = tweet_copy.pop('stats', {})
                for stat_key, stat_value in stats.items():
                    tweet_copy[stat_key] = stat_value
                
                # Join lists to strings for CSV format
                if 'hashtags' in tweet_copy and isinstance(tweet_copy['hashtags'], list):
                    tweet_copy['hashtags'] = ','.join(tweet_copy['hashtags'])
                if 'image_urls' in tweet_copy and isinstance(tweet_copy['image_urls'], list):
                    tweet_copy['image_urls'] = ','.join(tweet_copy['image_urls'])
                
                flattened_tweets.append(tweet_copy)
            
            # Save as CSV
            csv_path = os.path.join(output_folder, f"{filename}.csv")
            df = pd.DataFrame(flattened_tweets)
            df.to_csv(csv_path, index=False)
            print(f"\nSaved {len(trending_tweets)} tweets to {csv_path}")
        
        if output_format in ["json", "both"]:
            # Save as JSON
            json_path = os.path.join(output_folder, f"{filename}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(trending_tweets, f, ensure_ascii=False, indent=4)
            print(f"Saved {len(trending_tweets)} tweets to {json_path}")
        
        # Analyze the data
        print("\n" + "="*50)
        print("TRENDING TWEETS ANALYSIS")
        print("="*50)
        
        # Analyze hashtags
        analyze_top_hashtags(trending_tweets)
        
        # Analyze engagement
        analyze_engagement(trending_tweets)
    
    else:
        print("\n⚠️ No trending tweets were collected.")
        print("This could be due to:")
        print("- Twitter's explore page structure has changed")
        print("- You might not be properly logged in")
        print("- Twitter's systems might be temporarily unavailable")

def explore_specific_topics(scraper, output_format, output_folder):
    """Use the improved method to explore specific news topics"""
    print("\n" + "="*70)
    print("EXPLORE SPECIFIC NEWS TOPICS")
    print("="*70)
    
    # Default topics from user query
    default_topics = [
        "Trump's 10% Tariff",
        "Jaland Lowe Transfers to Kentucky",
        "iShowSpeed Experiences Advanced Tech in China"
    ]
    
    print("\nDefault topics to explore:")
    for i, topic in enumerate(default_topics, 1):
        print(f"{i}. {topic}")
    
    use_default = input("\nUse these default topics? (y/n): ").lower().startswith('y')
    
    if use_default:
        topics = default_topics
    else:
        # Get custom topics from user
        topics = []
        print("\nEnter topics to explore (one per line)")
        print("Press Enter on an empty line when done\n")
        
        while True:
            topic = input(f"Topic {len(topics)+1} (or press Enter to finish): ").strip()
            if not topic:
                break
            topics.append(topic)
        
        if not topics:
            print("\nNo topics entered, using default topics")
            topics = default_topics
    
    # Get number of tweets per topic
    try:
        limit_str = input("\nMaximum tweets per topic (default: 20): ").strip()
        limit_per_topic = int(limit_str) if limit_str else 20
    except ValueError:
        limit_per_topic = 20
        print("Invalid input, using default of 20 tweets per topic")
    
    # Explore the topics
    topic_tweets = scraper.explore_specific_topics(topics, limit_per_topic)
    
    if topic_tweets:
        # Flatten all tweets into a single list
        all_tweets = []
        for topic, tweets in topic_tweets.items():
            all_tweets.extend(tweets)
            
        # Save the collected tweets
        if all_tweets:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"specific_topics_{timestamp}"
            
            save_tweets(all_tweets, output_format, output_folder, "specific_topics")
            
            # Analyze the data
            print("\n" + "="*50)
            print("TOPIC ANALYSIS")
            print("="*50)
            
            # Analyze tweets by topic
            print("\nTweet counts by topic:")
            for topic, tweets in topic_tweets.items():
                print(f"- {topic}: {len(tweets)} tweets")
            
            # Analyze hashtags
            analyze_top_hashtags(all_tweets)
            
            # Analyze engagement
            analyze_engagement(all_tweets)
    else:
        print("\n⚠️ No tweets were collected from any topics")

def scrape_todays_news(scraper, limit, output_format, output_folder):
    """
    Scrape today's news stories from Twitter
    
    This function specifically targets Twitter's news tabs and uses multiple
    techniques to find and extract news stories
    """
    print("\n" + "="*70)
    print(" "*20 + "SCRAPING TODAY'S NEWS STORIES" + " "*20)
    print("="*70)
    
    # List of specific Twitter/X news tabs to try
    news_tabs = [
        {"url": "https://x.com/explore/tabs/news", "label": "X News Tab"},
        {"url": "https://x.com/explore/tabs/for_you", "label": "X For You Tab"},
        {"url": "https://x.com/explore", "label": "X Explore"},
        {"url": "https://x.com/explore/tabs/trending", "label": "X Trending Tab"},
        {"url": "https://x.com/home", "label": "X Home Timeline"},
        {"url": "https://x.com/search?q=Trump%20tariff&src=typed_query&f=top", "label": "Trump Tariff Search"}
    ]
    
    # Try different techniques to find Today's News section
    all_news_stories = []
    
    # 1. First try the direct tabs method - navigate to specific Twitter news tabs
    print("\nMethod 1: Navigating directly to X (Twitter) news tabs...")
    
    for tab in news_tabs:
        if len(all_news_stories) >= limit:
            break
            
        try:
            print(f"\nTrying {tab['label']} ({tab['url']})...")
            scraper.driver.get(tab['url'])
            time.sleep(5)  # Give more time for the tab to load
            
            # Check if we found any news stories
            remaining = limit - len(all_news_stories)
            stories = extract_news_stories(scraper.driver, remaining, tab['label'])
            
            if stories:
                all_news_stories.extend(stories)
                print(f"Found {len(stories)} news stories from {tab['label']}")
                
                # If we have enough stories, stop looking
                if len(all_news_stories) >= limit:
                    break
        except Exception as e:
            print(f"Error with {tab['label']}: {e}")
    
    # If we didn't find enough stories, try the search method
    if len(all_news_stories) < limit:
        try:
            # 2. Try using Twitter search with specific queries related to the topics of interest
            print("\nMethod 2: Using X search with specific queries...")
            remaining = limit - len(all_news_stories)
            
            # Try specific search queries including the tariff topic
            search_queries = [
                "Trump tariff",
                "global tariff economic debate",
                "trump 10% tariff news"
            ]
            
            for query in search_queries:
                if len(all_news_stories) >= limit:
                    break
                
                # Format the search URL
                encoded_query = query.replace(' ', '%20')
                search_url = f"https://x.com/search?q={encoded_query}&src=typed_query&f=top"
                
                print(f"Searching for '{query}'...")
                scraper.driver.get(search_url)
                time.sleep(3)
                
                # Look for tweets related to this query
                search_stories = extract_news_stories(scraper.driver, remaining, f"Search: {query}")
                if search_stories:
                    all_news_stories.extend(search_stories)
                    print(f"Found {len(search_stories)} news stories via '{query}' search")
                    remaining = limit - len(all_news_stories)
        except Exception as e:
            print(f"Error with specific search method: {e}")
    
    # If we still don't have enough stories, try the general news search method
    if len(all_news_stories) < limit:
        try:
            # 3. Try general news search terms
            print("\nMethod 3: Searching for general news keywords...")
            
            # List of news search terms to try
            news_terms = [
                "breaking news",
                "top stories",
                "today's headlines",
                "latest news",
                "trending news"
            ]
            
            for term in news_terms:
                if len(all_news_stories) >= limit:
                    break
                    
                try:
                    remaining = limit - len(all_news_stories)
                    search_url = f"https://x.com/search?q={term.replace(' ', '%20')}&src=typed_query&f=live"
                    
                    print(f"Searching for '{term}'...")
                    scraper.driver.get(search_url)
                    time.sleep(3)
                    
                    stories = extract_news_stories(scraper.driver, remaining, f"'{term}' Search")
                    if stories:
                        all_news_stories.extend(stories)
                        print(f"Found {len(stories)} news stories via '{term}' search")
                except Exception as e:
                    print(f"Error searching for '{term}': {e}")
        except Exception as e:
            print(f"Error with keyword search method: {e}")
    
    # Method 4: Direct content extraction as a fallback
    if len(all_news_stories) < limit:
        try:
            print("\nMethod 4: Extracting tweets directly from explore page (fallback)...")
            
            # Go to the main explore page
            scraper.driver.get("https://x.com/explore")
            time.sleep(5)
            
            remaining = limit - len(all_news_stories)
            # Try to get tweets directly without navigation
            stories = extract_tweets_directly(scraper.driver, remaining, "Direct Explore Feed")
            
            if stories:
                all_news_stories.extend(stories)
                print(f"Found {len(stories)} tweets via direct extraction")
        except Exception as e:
            print(f"Error with direct extraction method: {e}")
    
    # Process and save all collected news stories
    if all_news_stories:
        # Save the collected news stories
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_tweets(all_news_stories, output_format, output_folder, "todays_news")
        
        # Analyze the data
        print("\n" + "="*50)
        print("TODAY'S NEWS ANALYSIS")
        print("="*50)
        print(f"Total news stories collected: {len(all_news_stories)}")
        
        # Group stories by source
        sources = {}
        for story in all_news_stories:
            source = story.get('collection_method', 'Unknown')
            if source in sources:
                sources[source] += 1
            else:
                sources[source] = 1
        
        print("\nNews stories by source:")
        for source, count in sources.items():
            print(f"- {source}: {count} stories")
        
        # Analyze hashtags
        analyze_top_hashtags(all_news_stories)
        
        # Analyze engagement
        analyze_engagement(all_news_stories)
    else:
        print("\n⚠️ No news stories were found after trying all methods.")
        print("Twitter/X's layout may have changed significantly or there may be connectivity issues.")
        print("You might need to manually check Twitter's current structure and update the selectors.")

def extract_news_stories(driver, limit, source_label):
    """
    Extract news stories/tweets from the current view
    
    Args:
        driver: Selenium WebDriver instance
        limit: Maximum number of stories to extract
        source_label: Label for the source of these stories
        
    Returns:
        list: List of extracted news stories/tweets
    """
    print(f"Extracting stories from {source_label}...")
    
    # First check if there's a specific topic of interest on this page
    target_topics = [
        "Trump's 10% Global Tariff",
        "Trump's 10% Tariff",
        "Global Tariff",
        "Trump tariff"
    ]
    
    found_topic = False
    for topic in target_topics:
        try:
            script = f"""
            return Array.from(document.querySelectorAll('*')).some(
                el => el.textContent && el.textContent.includes('{topic}')
            );
            """
            if driver.execute_script(script):
                print(f"✓ Found target topic '{topic}' on this page!")
                found_topic = True
                break
        except:
            continue
    
    # First find all the news headers/trending topics
    headers = find_news_headers(driver)
    
    # If we found the target topic, prioritize it in results
    if found_topic:
        # Filter to prioritize target topic headers
        prioritized_headers = []
        for header in headers:
            header_text = header.get('text', '')
            if any(topic in header_text for topic in target_topics):
                header['priority'] = 'highest'
                prioritized_headers.insert(0, header)  # Add to beginning
            else:
                prioritized_headers.append(header)
                
        headers = prioritized_headers
        print(f"Prioritized {len([h for h in headers if h.get('priority') == 'highest'])} headers containing target topics")
    
    if headers:
        print(f"Found {len(headers)} news topic headers")
        return extract_tweets_from_headers(driver, headers, limit, source_label)
    else:
        print("No news headers found, looking for tweets directly...")
        return extract_tweets_directly(driver, limit, source_label)

def find_news_headers(driver):
    """Find all news headers/trending topics on the current page"""
    headers = []
    
    # Try different selectors for trending topics and news headers, prioritizing the specific trend elements
    selectors = [
        # Primary targets - these match the exact structure the user is interested in
        "div[data-testid='trend']",
        "div[data-testid='cellInnerDiv'] div[data-testid='trend']",
        "div[role='link'][data-testid='trend']",
        # CSS path based on the HTML snippet
        "div.css-175oi2r[data-testid='cellInnerDiv'] div[data-testid='trend']",
        # Secondary targets - other potential trend containers
        "a[href*='/explore/tabs/news/']",
        "a[href*='/explore/tabs/for-you/']",
        "article[role='article']",
        "div[role='link']",
        "div.css-1rynq56",
        "div.r-1udh08x"
    ]
    
    # First wait for the page to load fully
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main[role='main']"))
        )
        # Give extra time for dynamic content to load
        time.sleep(3)
    except Exception as e:
        print(f"Warning: Waiting for page load: {e}")
    
    # First try to find the exact trending topics the user is interested in
    try:
        # Use JavaScript to find elements with the specific text content
        specific_topics = [
            "Trump's 10% Global Tariff Sparks Economic Debate",
            "Trump's 10% Tariff",
            "Global Tariff"
        ]
        
        for topic in specific_topics:
            script = f"""
            return Array.from(document.querySelectorAll('*')).filter(
                el => el.textContent && el.textContent.includes('{topic}')
            );
            """
            elements = driver.execute_script(script)
            
            if elements:
                print(f"Found {len(elements)} elements containing '{topic}'")
                
                # For each element, find the closest trend container
                for elem in elements:
                    try:
                        # Try to find parent trend element
                        find_parent_script = """
                        function findParentWithAttribute(element, attribute, maxDepth = 5) {
                            let current = element;
                            let depth = 0;
                            
                            while (current && depth < maxDepth) {
                                if (current.getAttribute('data-testid') === 'trend' || 
                                    current.getAttribute('data-testid') === 'cellInnerDiv' ||
                                    current.getAttribute('role') === 'link') {
                                    return current;
                                }
                                current = current.parentElement;
                                depth++;
                            }
                            return element; // return original if no parent found
                        }
                        
                        return findParentWithAttribute(arguments[0], 'data-testid');
                        """
                        parent = driver.execute_script(find_parent_script, elem)
                        
                        # Extract the text and add to headers
                        text = driver.execute_script("return arguments[0].textContent", parent)
                        if text and len(text.strip()) > 5:
                            headers.append({
                                "element": parent,
                                "text": text,
                                "is_clickable": True,
                                "priority": "high",  # Mark as high priority - exact match
                                "topic": topic
                            })
                            print(f"Found specific news topic: '{topic}'")
                    except Exception as e:
                        print(f"Error processing specific topic element: {e}")
    except Exception as e:
        print(f"Error searching for specific topics: {e}")
    
    # Try to find headers with each selector
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"Found {len(elements)} potential headers with selector: {selector}")
                for elem in elements:
                    try:
                        # Get the text content to see if it looks like a news header
                        text = elem.text
                        
                        # Skip empty elements or very short text
                        if not text or len(text.strip()) < 3:
                            continue
                            
                        # Check if it contains certain patterns that suggest it's a news topic
                        if (text and 
                            ("Trending" in text or "News" in text or "hours ago" in text or "posts" in text or 
                             "Global Tariff" in text or "Trump" in text or
                             any(cat in text for cat in ["Business", "Sports", "Entertainment", "Politics", "Technology"]))):
                            
                            # Create a header object with element and text
                            headers.append({
                                "element": elem,
                                "text": text,
                                "is_clickable": elem.tag_name == "a" or "role='link'" in elem.get_attribute("outerHTML") or elem.get_attribute("role") == "link",
                                "priority": "medium"  # Standard priority
                            })
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    
    # If we didn't find any headers, try a more generic approach
    if not headers:
        print("No headers found with specific selectors, trying generic approach...")
        try:
            # Try to find any text that might be a news topic using JavaScript
            news_keywords = ["Trending", "News", "Today", "Breaking", "Top stories", "Tariff", "Trump", "Debate"]
            for keyword in news_keywords:
                script = f"""
                return Array.from(document.querySelectorAll('*')).filter(
                    el => el.textContent && el.textContent.includes('{keyword}') && 
                    el.textContent.length < 200 && el.offsetWidth > 0 && el.offsetHeight > 0
                );
                """
                elements = driver.execute_script(script)
                
                for elem in elements:
                    try:
                        text = driver.execute_script("return arguments[0].textContent", elem)
                        if text and len(text.strip()) > 5:
                            # Add this as a potential header
                            headers.append({
                                "element": elem,
                                "text": text,
                                "is_clickable": True,  # Assume it might be clickable
                                "priority": "low"  # Low priority - last resort
                            })
                    except:
                        continue
        except Exception as e:
            print(f"Error with generic header search: {e}")
    
    # Remove duplicates (based on text content)
    unique_headers = []
    seen_texts = set()
    
    # First add high priority items
    for header in sorted(headers, key=lambda x: 0 if x.get('priority') == 'high' else (1 if x.get('priority') == 'medium' else 2)):
        # Use the first line as a unique identifier
        text = header["text"].split('\n')[0] if '\n' in header["text"] else header["text"]
        if text not in seen_texts:
            seen_texts.add(text)
            unique_headers.append(header)
    
    print(f"Found {len(unique_headers)} unique news topic headers")
    return unique_headers

def extract_tweets_from_headers(driver, headers, limit, source_label):
    """Click on each header and extract tweets from the resulting page"""
    all_tweets = []
    max_tweets_per_header = max(5, limit // len(headers)) if headers else limit  # Distribute limit among headers
    
    # Keep track of URLs we've visited
    visited_urls = set()
    visited_urls.add(driver.current_url)
    original_url = driver.current_url
    
    # Create a snapshot of header information
    header_info = []
    for header in headers:
        try:
            header_text = header["text"]
            header_short = header_text.split('\n')[0] if '\n' in header_text else header_text
            if len(header_short) > 50:
                header_short = header_short[:47] + "..."
                
            # Save the text content for later search
            header_info.append({
                "full_text": header_text,
                "short_text": header_short
            })
        except Exception as e:
            # Skip headers we can't process
            print(f"Error extracting header info: {e}")
            continue
    
    # Process each header using the text snapshot, not the original elements
    for i, header_data in enumerate(header_info):
        if len(all_tweets) >= limit:
            break
            
        try:
            header_text = header_data["full_text"]
            header_short = header_data["short_text"]
            
            print(f"\nProcessing header {i+1}/{len(header_info)}: {header_short}")
            
            # Find this header element again using text search instead of stored reference
            try:
                # Use JavaScript to find the element by text content
                # Escape single quotes in the search text
                search_text = header_text.replace("'", "\\'")
                script = f"""
                return Array.from(document.querySelectorAll('*')).find(
                    el => el.textContent.includes('{search_text}')
                );
                """
                element = driver.execute_script(script)
                
                if not element:
                    print(f"Could not re-locate header element for '{header_short}', skipping")
                    continue
                
                # Scroll the element into view
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(1)
                
                # Try to click using JavaScript which is more reliable
                driver.execute_script("arguments[0].click();", element)
            except Exception as e:
                print(f"Could not click header {i+1}, error: {e}")
                continue
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if URL changed to avoid processing same page twice
            current_url = driver.current_url
            if current_url in visited_urls and current_url != original_url:
                print(f"Already visited {current_url}, skipping")
                driver.get(original_url)  # Go back to original page
                time.sleep(2)
                continue
                
            visited_urls.add(current_url)
            
            # Now extract tweets from this page
            print(f"Looking for tweets in '{header_short}'")
            remaining = min(max_tweets_per_header, limit - len(all_tweets))
            tweets = extract_tweets_directly(driver, remaining, f"{source_label} - {header_short}")
            
            if tweets:
                # Add the header info to each tweet
                for tweet in tweets:
                    tweet['topic'] = header_text
                    tweet['topic_source'] = source_label
                
                all_tweets.extend(tweets)
                print(f"Added {len(tweets)} tweets from '{header_short}'")
            else:
                print(f"No tweets found in '{header_short}'")
            
            # Go back to the original page for the next header
            driver.get(original_url)
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing header {i+1}: {e}")
            # Try to go back to the original page
            try:
                driver.get(original_url)
                time.sleep(2)
            except:
                pass
    
    return all_tweets

def extract_tweets_directly(driver, limit, source_label):
    """Extract tweets directly from the current page view"""
    tweets = []
    scroll_count = 0
    max_scrolls = 15
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    print("Scroll progress: ", end="", flush=True)
    
    # First wait for the page to properly load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main[role='main']"))
        )
        time.sleep(2)  # Additional wait for dynamic content
    except Exception as e:
        print(f"Warning while waiting for page to load: {e}")
    
    # Look for tweet elements
    while len(tweets) < limit and scroll_count < max_scrolls:
        # Find tweet articles - try multiple selectors in sequence
        tweet_elements = []
        selectors = [
            "article[data-testid='tweet']",
            "div[data-testid='cellInnerDiv']:has(div[data-testid='User-Name'])",
            "div.r-18u37iz:has(time)",
            "article",
            "div.css-1dbjc4n:has(div[data-testid='tweetText'])",
            "div[role='article']",
            "div[data-testid='cellInnerDiv']"
        ]
        
        for selector in selectors:
            try:
                found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if found_elements:
                    tweet_elements = found_elements
                    print(f"Found {len(tweet_elements)} elements using selector: {selector}")
                    break
            except Exception as e:
                continue
        
        # If no tweets found with CSS selectors, try JavaScript
        if not tweet_elements:
            try:
                script = """
                return Array.from(document.querySelectorAll('*')).filter(el => {
                    // Look for elements that might be tweets (has username, timestamp, or tweet text)
                    return (el.querySelector('time') || 
                           el.querySelector('[data-testid="User-Name"]') ||
                           el.querySelector('[data-testid="tweetText"]'))
                           && el.offsetWidth > 0 && el.offsetHeight > 0;
                });
                """
                tweet_elements = driver.execute_script(script)
                print(f"Found {len(tweet_elements)} tweet elements using JavaScript")
            except Exception as e:
                print(f"JavaScript tweet search failed: {e}")
        
        new_tweets_found = 0
        
        # Process found elements
        for elem in tweet_elements:
            try:
                # Get a unique identifier
                tweet_id = None
                try:
                    # Try several attributes that could serve as an ID
                    for attr in ["aria-labelledby", "id", "data-testid"]:
                        tweet_id = elem.get_attribute(attr)
                        if tweet_id:
                            break
                except:
                    pass
                
                # If no ID found, create a pseudo-ID from the content
                if not tweet_id:
                    try:
                        content = elem.text[:50]
                        tweet_id = f"pseudo-id-{len(tweets)}-{hash(content)}"
                    except:
                        tweet_id = f"pseudo-id-{len(tweets)}-{time.time()}"
                
                # Skip if we've already processed this tweet
                if any(t.get('id') == tweet_id for t in tweets):
                    continue
                
                # Extract user information
                username = ""
                user_handle = ""
                try:
                    try:
                        user_name_elem = elem.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']")
                        if user_name_elem:
                            name_text = user_name_elem.text
                            parts = name_text.split('\n')
                            if len(parts) >= 2:
                                username = parts[0]
                                user_handle = parts[1]
                    except NoSuchElementException:
                        # Try alternative method
                        possible_username = elem.find_elements(By.TAG_NAME, "span")
                        if possible_username:
                            for span in possible_username:
                                if '@' in span.text:
                                    user_handle = span.text
                                    break
                            # Try to find the username from nearby spans
                            if not username and possible_username:
                                username = possible_username[0].text
                except:
                    pass
                
                # Extract timestamp
                timestamp = ""
                try:
                    time_elems = elem.find_elements(By.TAG_NAME, "time")
                    if time_elems:
                        timestamp = time_elems[0].get_attribute("datetime")
                    else:
                        # Look for time-like text (e.g., "2h", "1d")
                        time_pattern = r'\b(\d+[hmd])\b'
                        matches = re.findall(time_pattern, elem.text)
                        if matches:
                            timestamp = matches[0]
                except:
                    pass
                
                # Extract tweet text
                tweet_text = ""
                try:
                    try:
                        text_elem = elem.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
                        tweet_text = text_elem.text
                    except NoSuchElementException:
                        # If we can't find the tweet text element, try to get any text
                        if username and user_handle:
                            full_text = elem.text
                            lines = full_text.split('\n')
                            # Skip first few lines that might contain user info
                            tweet_text = '\n'.join(lines[2:]) if len(lines) > 2 else full_text
                        else:
                            tweet_text = elem.text
                except:
                    pass
                
                # Skip if we couldn't extract any meaningful content
                if not tweet_text and not username:
                    continue
                
                # Get engagement metrics
                stats = {}
                try:
                    stats_elements = elem.find_elements(By.CSS_SELECTOR, "[data-testid$='-count']")
                    for stat_elem in stats_elements:
                        try:
                            stat_id = stat_elem.get_attribute("data-testid")
                            value = stat_elem.text
                            stats[stat_id] = value
                        except:
                            continue
                except:
                    pass
                
                # Get hashtags
                hashtags = []
                try:
                    if tweet_text:
                        hashtag_pattern = r'#(\w+)'
                        hashtags = re.findall(hashtag_pattern, tweet_text)
                except:
                    pass
                
                # Get image URLs
                image_urls = []
                try:
                    img_elements = elem.find_elements(By.CSS_SELECTOR, "img[alt='Image']")
                    for img in img_elements:
                        src = img.get_attribute("src")
                        if src and "https://" in src:
                            image_urls.append(src)
                except:
                    pass
                
                # Create the tweet data
                tweet_data = {
                    'id': tweet_id,
                    'username': username,
                    'user_handle': user_handle,
                    'timestamp': timestamp,
                    'text': tweet_text,
                    'stats': stats,
                    'hashtags': hashtags,
                    'image_urls': image_urls,
                    'collection_method': source_label
                }
                
                tweets.append(tweet_data)
                new_tweets_found += 1
                
                if len(tweets) >= limit:
                    break
            except Exception as e:
                # Silently continue if we can't extract this tweet
                continue
        
        if len(tweets) >= limit:
            break
        
        # Print progress
        print("▶", end="", flush=True)
        if new_tweets_found > 0:
            print(f"[+{new_tweets_found}]", end="", flush=True)
        
        # Scroll down
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Check if we've reached the end
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                print("(waiting...)", end="", flush=True)
                time.sleep(3)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    print("\nReached end of content")
                    break
            
            last_height = new_height
        except Exception as e:
            print(f"\nError scrolling: {e}")
            scroll_count += 1
    
    print(f"\nExtracted {len(tweets)} tweets")
    return tweets

def scrape_tariff_discussions(scraper, limit, output_format, output_folder):
    """
    Specifically target and scrape discussions about Trump's 10% Global Tariff
    
    This function focuses exclusively on finding and extracting content about
    the tariff topic the user is interested in
    """
    print("\n" + "="*70)
    print(" "*15 + "SCRAPING TRUMP'S 10% GLOBAL TARIFF DISCUSSIONS" + " "*15)
    print("="*70)
    
    # Direct search URLs for the target topic
    search_urls = [
        {"url": "https://x.com/search?q=Trump%20tariff&src=typed_query&f=top", "label": "Trump Tariff (Top)"},
        {"url": "https://x.com/search?q=Trump%2010%25%20tariff&src=typed_query&f=top", "label": "Trump 10% Tariff (Top)"},
        {"url": "https://x.com/search?q=Trump%20global%20tariff&src=typed_query&f=top", "label": "Trump Global Tariff (Top)"},
        {"url": "https://x.com/search?q=Trump%20tariff&src=typed_query&f=live", "label": "Trump Tariff (Live)"},
        {"url": "https://x.com/explore/tabs/news", "label": "X News Tab"}
    ]
    
    # Try different techniques to find tariff discussions
    all_tweets = []
    
    print("\nSearching specifically for Trump's tariff discussions...")
    
    # Try each search URL
    for search in search_urls:
        if len(all_tweets) >= limit:
            break
            
        try:
            print(f"\nTrying {search['label']} ({search['url']})...")
            scraper.driver.get(search['url'])
            time.sleep(5)  # Give more time for the page to load
            
            # Check if we found relevant tweets
            remaining = limit - len(all_tweets)
            tweets = extract_news_stories(scraper.driver, remaining, search['label'])
            
            if tweets:
                all_tweets.extend(tweets)
                print(f"Found {len(tweets)} tweets from {search['label']}")
                
                # If we have enough tweets, stop looking
                if len(all_tweets) >= limit:
                    break
        except Exception as e:
            print(f"Error with {search['label']}: {e}")
    
    # If we still don't have enough tweets, try looking at specific profiles
    if len(all_tweets) < limit:
        try:
            # Try specific profiles that might discuss the topic
            print("\nChecking relevant profiles...")
            profiles = [
                "https://x.com/EconPolicyWatch",
                "https://x.com/economics",
                "https://x.com/business",
                "https://x.com/markets"
            ]
            
            for profile in profiles:
                if len(all_tweets) >= limit:
                    break
                    
                try:
                    remaining = limit - len(all_tweets)
                    print(f"Checking {profile}...")
                    scraper.driver.get(profile)
                    time.sleep(3)
                    
                    # Look for tweets related to tariffs
                    profile_tweets = extract_tweets_directly(scraper.driver, remaining, f"Profile: {profile}")
                    
                    # Filter to only include tweets mentioning tariffs
                    tariff_tweets = []
                    tariff_terms = ["tariff", "trump", "trade", "economic", "tax", "import"]
                    
                    for tweet in profile_tweets:
                        tweet_text = tweet.get('text', '').lower()
                        if any(term in tweet_text for term in tariff_terms):
                            tariff_tweets.append(tweet)
                    
                    if tariff_tweets:
                        all_tweets.extend(tariff_tweets)
                        print(f"Found {len(tariff_tweets)} tariff-related tweets from {profile}")
                except Exception as e:
                    print(f"Error checking {profile}: {e}")
        except Exception as e:
            print(f"Error checking profiles: {e}")
    
    # Process and save all collected tweets
    if all_tweets:
        # Save the collected tweets
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_tweets(all_tweets, output_format, output_folder, "trump_tariff")
        
        # Analyze the data
        print("\n" + "="*50)
        print("TRUMP TARIFF ANALYSIS")
        print("="*50)
        print(f"Total tweets collected: {len(all_tweets)}")
        
        # Group tweets by source
        sources = {}
        for tweet in all_tweets:
            source = tweet.get('collection_method', 'Unknown')
            if source in sources:
                sources[source] += 1
            else:
                sources[source] = 1
        
        print("\nTweets by source:")
        for source, count in sources.items():
            print(f"- {source}: {count} tweets")
        
        # Analyze hashtags
        analyze_top_hashtags(all_tweets)
        
        # Analyze engagement
        analyze_engagement(all_tweets)
    else:
        print("\n⚠️ No tweets about Trump's tariff were found.")
        print("Try again later or check if the topic is still trending on X/Twitter.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")
    finally:
        print("\nGoodbye!") 