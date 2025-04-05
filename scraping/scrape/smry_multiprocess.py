import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import urljoin, quote
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import random
from http.client import RemoteDisconnected

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Setup paths
INPUT_FILE = 'data/countries/all_countries_1d_20250405_150707.csv'
OUTPUT_DIR = 'data/smry_scrape'
BATCH_SIZE = 5  # Reduced from 20 to 5 like in the working version
MAX_WORKERS = 10  # Reduced from 20 to 10 to avoid overwhelming the server

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_session():
    """Create a requests session with simpler configuration"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # Reduced retries
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

def clean_url(url):
    """Clean URL string by removing brackets, quotes, and spaces"""
    url = url.strip("[]' ")
    return quote(url, safe=':/?=&%')

def get_smry_url(url):
    """Generate SMRY.AI URL"""
    return f"https://smry.ai/{clean_url(url)}"

def scrape_article_text(url, session):
    """Scrape article text with better error handling"""
    try:
        clean_source_url = clean_url(url)
        logging.info(f"Attempting to scrape URL: {clean_source_url}")
        
        # Use simpler headers like in the working version
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Use fixed delay like in the working version
        time.sleep(1)
        
        response = session.get(clean_source_url, timeout=10)
        logging.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Try to find the main article content
            article_containers = [
                soup.find('article'),
                soup.find('main'),
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
                            logging.info(f"Found article text: {text[:100]}...")
                            return text
            
            # Fallback: try to get all paragraphs from the page
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text().strip() for p in paragraphs])
                text = ' '.join(text.split())
                if len(text) > 100:
                    logging.info(f"Found text using fallback: {text[:100]}...")
                    return text
            
            logging.warning(f"No substantial text content found for {clean_source_url}")
            return ""
            
    except Exception as e:
        logging.error(f"Error scraping {url}: {str(e)}")
    return ""

def process_url(args):
    """Process a single URL with its associated row data"""
    url, row, session = args
    try:
        smry_url = get_smry_url(url)
        text = scrape_article_text(url, session)
        
        return {
            'URLs': url,
            'SMRY_URLs': smry_url,
            'DateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Title': row['titles'] if pd.notna(row['titles']) else '',
            'LangCode': 'en',
            'DocTone': row['normalized_score'] if pd.notna(row['normalized_score']) else 0.0,
            'Location': row['location_name'] if pd.notna(row['location_name']) else '',
            'CountryCode': row['country_code'] if pd.notna(row['country_code']) else '',
            'ContextualText': text
        }
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return None

def process_batch(batch_df, session):
    """Process a batch of URLs using ThreadPoolExecutor"""
    urls_with_rows = []
    for _, row in batch_df.iterrows():
        try:
            urls = [url.strip() for url in str(row['urls']).split(',') if url.strip()]
            for url in urls:
                urls_with_rows.append((url, row, session))
        except Exception as e:
            logging.error(f"Error processing row {row.name}: {str(e)}")
            continue
    
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_url, args) for args in urls_with_rows]
        
        # Use tqdm for progress tracking of individual URLs
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing URLs"):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logging.error(f"Error in future: {str(e)}")
    
    return pd.DataFrame(results) if results else pd.DataFrame()

def main():
    try:
        # Verify input file exists
        if not os.path.exists(INPUT_FILE):
            raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")
        
        # Read the CSV file in chunks to handle large files
        chunk_size = BATCH_SIZE * 10  # Process 10 batches at a time
        
        # Get timestamp for file naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(OUTPUT_DIR, f'scraped_articles_{timestamp}.csv')
        
        # Required columns for output
        required_columns = [
            'URLs', 'SMRY_URLs', 'DateTime', 'Title', 'LangCode',
            'DocTone', 'Location', 'CountryCode', 'ContextualText'
        ]
        
        # Process chunks
        first_chunk = True
        for chunk_num, df_chunk in enumerate(pd.read_csv(INPUT_FILE, chunksize=chunk_size)):
            logging.info(f"Processing chunk {chunk_num + 1}")
            
            # Calculate batches for this chunk
            total_rows = len(df_chunk)
            total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE
            
            # Create a new session for each chunk to avoid resource issues
            session = create_session()
            
            # Process batches within the chunk
            with tqdm(total=total_batches, desc=f"Processing chunk {chunk_num + 1}") as pbar:
                for batch_num in range(total_batches):
                    try:
                        start_idx = batch_num * BATCH_SIZE
                        end_idx = min((batch_num + 1) * BATCH_SIZE, total_rows)
                        
                        batch_df = df_chunk.iloc[start_idx:end_idx]
                        processed_batch = process_batch(batch_df, session)
                        
                        if not processed_batch.empty:
                            # Ensure columns are in the right order
                            processed_batch = processed_batch[required_columns]
                            
                            # Append to the CSV file
                            mode = 'w' if first_chunk and batch_num == 0 else 'a'
                            header = first_chunk and batch_num == 0
                            processed_batch.to_csv(output_file, mode=mode, header=header, 
                                                index=False, encoding='utf-8')
                        
                        pbar.update(1)
                        
                    except Exception as e:
                        logging.error(f"Error processing batch {batch_num} in chunk {chunk_num + 1}: {str(e)}")
                        continue
            
            first_chunk = False
            session.close()
        
        logging.info(f"Processing complete! Results saved to: {output_file}")
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()