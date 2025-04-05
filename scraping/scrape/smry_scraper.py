import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import urljoin, quote
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Setup paths
INPUT_FILE = 'data/countries/all_countries_1d_20250405_150707.csv'
OUTPUT_DIR = 'data/smry_scrape'
BATCH_SIZE = 5  # Process 5 rows at a time

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_url(url):
    """Clean URL string by removing brackets, quotes, and spaces"""
    url = url.strip("[]' ")
    # Ensure URL is properly encoded
    return quote(url, safe=':/?=&%')

def get_smry_url(url):
    """Generate SMRY.AI URL"""
    return f"https://smry.ai/{clean_url(url)}"

def scrape_article_text(url):
    try:
        clean_source_url = clean_url(url)
        logging.info(f"Attempting to scrape URL: {clean_source_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(clean_source_url, headers=headers, timeout=10)
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

def process_batch(batch_df, batch_num, total_batches):
    new_rows = []
    logging.info(f"Processing batch {batch_num}/{total_batches}")
    
    for index, row in batch_df.iterrows():
        logging.info(f"Processing row {index}")
        urls = [clean_url(url.strip()) for url in str(row['urls']).split(',')]
        logging.info(f"Found {len(urls)} URLs in this row")
        
        for url_index, url in enumerate(urls, 1):
            if url:
                logging.info(f"Processing URL {url_index}/{len(urls)}: {url}")
                smry_url = get_smry_url(url)
                new_row = {
                    'URLs': url,
                    'SMRY_URLs': smry_url,
                    'DateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Title': row['titles'] if pd.notna(row['titles']) else '',
                    'LangCode': 'en',
                    'DocTone': row['normalized_score'] if pd.notna(row['normalized_score']) else 0.0,
                    'Location': row['location_name'] if pd.notna(row['location_name']) else '',
                    'CountryCode': row['country_code'] if pd.notna(row['country_code']) else '',
                    'ContextualText': scrape_article_text(url)
                }
                new_rows.append(new_row)
                logging.info(f"Successfully processed URL: {url}")
                time.sleep(1)
    
    return pd.DataFrame(new_rows)

def main():
    # Read the CSV file
    logging.info(f"Reading input file: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    logging.info(f"Loaded {len(df)} rows from the input file")
    
    # Calculate number of batches
    total_rows = len(df)
    total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE
    logging.info(f"Processing {total_rows} rows in {total_batches} batches of {BATCH_SIZE}")
    
    # Required columns for output
    required_columns = [
        'URLs',
        'SMRY_URLs',
        'DateTime',
        'Title',
        'LangCode',
        'DocTone',
        'Location',
        'CountryCode',
        'ContextualText'
    ]
    
    # Get timestamp for file naming
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f'scraped_articles_{timestamp}.csv')
    
    # Process in batches
    for batch_num in range(total_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min((batch_num + 1) * BATCH_SIZE, total_rows)
        
        logging.info(f"\nStarting batch {batch_num + 1}/{total_batches}")
        logging.info(f"Processing rows {start_idx} to {end_idx}")
        
        batch_df = df.iloc[start_idx:end_idx]
        processed_batch = process_batch(batch_df, batch_num + 1, total_batches)
        
        # Ensure columns are in the right order
        processed_batch = processed_batch[required_columns]
        
        # Append to the CSV file (create if first batch, append if subsequent)
        mode = 'w' if batch_num == 0 else 'a'
        header = batch_num == 0
        processed_batch.to_csv(output_file, mode=mode, header=header, index=False, encoding='utf-8')
        logging.info(f"Updated results in: {output_file}")
        
        logging.info(f"Completed batch {batch_num + 1}/{total_batches}")
    
    logging.info(f"\nProcessing complete! Results saved to: {output_file}")

if __name__ == "__main__":
    main()











