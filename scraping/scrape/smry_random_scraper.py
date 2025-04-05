import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import urljoin, quote, urlparse
import logging
import os
import random
import concurrent.futures
import hashlib
import pickle
from functools import lru_cache
import re

# Configure logging - reduce logging output for speed
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Reduce requests/urllib3 logging noise
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Setup paths
INPUT_FILE = 'data/countries/all_countries_1d_20250405_171515.csv'
PREVIOUS_SCRAPE_FILE = 'data/smry_scrape/scraped_articles_20250405_170700.csv'
OUTPUT_DIR = 'data/smry_scrape'
BATCH_SIZE = 20  # Increased batch size for speed
MAX_THREADS = 15  # Increased concurrency
MAX_RETRIES = 2   # Maximum retry attempts for failed requests
CACHE_DIR = os.path.join(OUTPUT_DIR, 'cache')
REQUEST_TIMEOUT = 6  # Reduced timeout for faster failure

# Create necessary directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Set up a session for connection pooling and reuse
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=MAX_THREADS,
    pool_maxsize=MAX_THREADS*2,
    max_retries=MAX_RETRIES
)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
})

def get_cache_path(url):
    """Generate a unique cache file path based on URL"""
    hash_obj = hashlib.md5(url.encode('utf-8'))
    return os.path.join(CACHE_DIR, f"{hash_obj.hexdigest()}.pkl")

def clean_url(url):
    """Clean URL string by removing brackets, quotes, and spaces"""
    url = url.strip("[]' ")
    # Ensure URL is properly encoded
    return quote(url, safe=':/?=&%')

def get_smry_url(url):
    """Generate SMRY.AI URL"""
    return f"https://smry.ai/{clean_url(url)}"

@lru_cache(maxsize=1000)  # Cache results to avoid repeated scraping
def scrape_article_text(url):
    """Scrape article text with caching and optimization"""
    cache_path = get_cache_path(url)
    
    # Check cache first
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
                logging.info(f"Using cached data for: {url}")
                return cached_data
        except Exception as e:
            logging.warning(f"Cache read error for {url}: {str(e)}")
    
    try:
        clean_source_url = clean_url(url)
        
        # Skip obvious non-article URLs (like image files, PDFs, etc.)
        parsed_url = urlparse(clean_source_url)
        if parsed_url.path:
            ext = os.path.splitext(parsed_url.path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.mp4', '.mp3', '.zip']:
                logging.info(f"Skipping non-article URL: {clean_source_url}")
                return ""
        
        # Fast scraping with reduced logging
        response = session.get(clean_source_url, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            # Use lxml parser for speed
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Quick removal of unwanted elements
            for tag in ['script', 'style', 'nav', 'header', 'footer', 'iframe']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Optimized extraction of text using selective targeting
            article_containers = [
                soup.find('article'),
                soup.find('main'),
                soup.find(class_=re.compile(r'article|content|post|entry|story', re.I)),
                soup.find(id=re.compile(r'article|content|post|entry|story', re.I)),
                soup.find('div', class_='article-content'),
                soup.find('div', class_='story-content'),
                soup.find('div', {'role': 'main'}),
                soup.find('div', class_='content')
            ]
            
            for container in article_containers:
                if container:
                    paragraphs = container.find_all('p')
                    if paragraphs:
                        text = ' '.join([p.get_text().strip() for p in paragraphs])
                        text = ' '.join(text.split())
                        if len(text) > 100:
                            # Cache successful results
                            try:
                                with open(cache_path, 'wb') as f:
                                    pickle.dump(text, f)
                            except Exception as e:
                                logging.warning(f"Failed to cache {url}: {str(e)}")
                            return text
            
            # Fallback with minimal processing
            paragraphs = soup.find_all('p')[:20]  # Limit to first 20 paragraphs for speed
            if paragraphs:
                text = ' '.join([p.get_text().strip() for p in paragraphs])
                text = ' '.join(text.split())
                if len(text) > 100:
                    # Cache successful results
                    try:
                        with open(cache_path, 'wb') as f:
                            pickle.dump(text, f)
                    except Exception as e:
                        logging.warning(f"Failed to cache {url}: {str(e)}")
                    return text
            
            # Last resort: get text directly from body
            body = soup.find('body')
            if body:
                text = ' '.join(body.get_text().strip().split())
                if len(text) > 100:
                    return text[:5000]  # Limit text length
            
            return ""
            
    except requests.Timeout:
        logging.warning(f"Timeout scraping {url}")
    except Exception as e:
        logging.warning(f"Error scraping {url}: {str(e)}")
    
    return ""

def process_url(url_data):
    """Process a single URL and return a data row if successful"""
    url, row = url_data
    try:
        clean_url_str = clean_url(url)
        if not clean_url_str:
            return None
        
        smry_url = get_smry_url(clean_url_str)
        
        # Fast processing option for URLs we can't scrape properly
        parsed_url = urlparse(clean_url_str)
        if parsed_url.netloc in ['twitter.com', 'instagram.com', 'facebook.com', 't.co']:
            # For social media, don't waste time trying to scrape full content
            context_text = ""
        else:
            context_text = scrape_article_text(clean_url_str)
        
        new_row = {
            'URLs': clean_url_str,
            'SMRY_URLs': smry_url,
            'DateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Title': row['titles'] if pd.notna(row['titles']) else '',
            'LangCode': 'en',
            'DocTone': row['normalized_score'] if pd.notna(row['normalized_score']) else 0.0,
            'Location': row['location_name'] if pd.notna(row['location_name']) else '',
            'CountryCode': row['country_code'] if pd.notna(row['country_code']) else '',
            'ContextualText': context_text
        }
        
        return new_row
    except Exception as e:
        logging.warning(f"Error processing URL {url}: {str(e)}")
        return None

def load_already_scraped_urls():
    """Load URLs that were already scraped"""
    try:
        if os.path.exists(PREVIOUS_SCRAPE_FILE):
            df = pd.read_csv(PREVIOUS_SCRAPE_FILE)
            urls = set(df['URLs'].tolist())
            logging.info(f"Loaded {len(urls)} previously scraped URLs")
            return urls, df
        else:
            logging.warning(f"Previous scrape file not found: {PREVIOUS_SCRAPE_FILE}")
            return set(), None
    except Exception as e:
        logging.error(f"Error loading previously scraped URLs: {str(e)}")
        return set(), None

def extract_urls_from_str(urls_str):
    """Extract URLs from different string formats"""
    if not urls_str or pd.isna(urls_str):
        return []
    
    urls_str = str(urls_str)
    
    # Handle different URL formats
    if urls_str.startswith('[') and urls_str.endswith(']'):
        # List-like format
        try:
            # Try to eval as a literal list if properly formatted
            import ast
            url_list = ast.literal_eval(urls_str)
            if isinstance(url_list, list):
                return [url.strip() for url in url_list if url.strip()]
        except:
            # Fallback: manual parsing
            url_list = urls_str.strip('[]').replace("'", "").replace('"', "").split(',')
            return [url.strip() for url in url_list if url.strip()]
    else:
        # Comma-separated format
        url_list = urls_str.split(',')
        return [url.strip() for url in url_list if url.strip()]

def main():
    start_time = time.time()
    
    # Load previously scraped URLs to avoid duplicates
    already_scraped_urls, existing_df = load_already_scraped_urls()
    
    # Read the input CSV file using optimized pandas
    logging.info(f"Reading input file: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, dtype={'urls': str, 'titles': str})
    logging.info(f"Loaded {len(df)} rows from the input file")
    
    # Extract all URLs from the input data more efficiently
    all_urls = []
    for index, row in df.iterrows():
        if pd.notna(row['urls']) and row['urls']:
            try:
                url_list = extract_urls_from_str(row['urls'])
                for url in url_list:
                    if url and clean_url(url) not in already_scraped_urls:
                        all_urls.append((url, row))
            except Exception as e:
                logging.error(f"Error parsing URLs in row {index}: {str(e)}")
    
    logging.info(f"Found {len(all_urls)} new URLs to process")
    
    # Shuffle URLs for random processing
    random.shuffle(all_urls)
    
    # Get timestamp for file naming
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f'scraped_articles_{timestamp}.csv')
    
    # Create new dataframe with previously scraped URLs
    if existing_df is not None:
        output_df = existing_df.copy()
        logging.info(f"Copied {len(output_df)} existing rows to the new output file")
    else:
        # Define output columns if starting fresh
        output_df = pd.DataFrame(columns=[
            'URLs', 'SMRY_URLs', 'DateTime', 'Title', 'LangCode', 
            'DocTone', 'Location', 'CountryCode', 'ContextualText'
        ])
    
    # Process URLs in batches with improved ThreadPoolExecutor
    batch_num = 0
    total_batches = (len(all_urls) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_start in range(0, len(all_urls), BATCH_SIZE):
        batch_num += 1
        batch_end = min(batch_start + BATCH_SIZE, len(all_urls))
        batch = all_urls[batch_start:batch_end]
        
        logging.info(f"\nProcessing batch {batch_num}/{total_batches}")
        
        # Process batch with ThreadPoolExecutor
        new_rows = []
        
        # Advanced executor with optimized thread management
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            # Submit all tasks to get futures
            future_to_url = {executor.submit(process_url, url_data): url_data for url_data in batch}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url, _ = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        new_rows.append(result)
                except Exception as e:
                    logging.warning(f"Exception processing {url}: {str(e)}")
        
        # Create DataFrame for the batch results - only if we have data
        if new_rows:
            # Use optimized DataFrame creation
            batch_df = pd.DataFrame(new_rows)
            
            # Append to the main DataFrame efficiently
            output_df = pd.concat([output_df, batch_df], ignore_index=True)
            
            # Save to CSV file after each batch
            output_df.to_csv(output_file, index=False, encoding='utf-8')
            logging.info(f"Updated results in: {output_file}, total rows: {len(output_df)}")
        
        # Calculate progress and speed
        elapsed_time = time.time() - start_time
        urls_processed = batch_num * BATCH_SIZE
        if elapsed_time > 0:
            urls_per_second = urls_processed / elapsed_time
            logging.info(f"Speed: {urls_per_second:.2f} URLs/second")
        
        logging.info(f"Completed batch {batch_num}/{total_batches}")
    
    # Final processing time calculation
    total_time = time.time() - start_time
    urls_processed = min(len(all_urls), batch_num * BATCH_SIZE)
    if urls_processed > 0 and total_time > 0:
        avg_speed = urls_processed / total_time
        logging.info(f"\nProcessing complete in {total_time:.2f} seconds!")
        logging.info(f"Average speed: {avg_speed:.2f} URLs/second")
    
    logging.info(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main() 