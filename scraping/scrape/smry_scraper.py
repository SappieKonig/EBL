import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import urljoin, quote
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Input file path
input_file = 'data/countries/all_countries_1d_20250405_150707.csv'

# Read the CSV file
logging.info(f"Reading input file: {input_file}")
df = pd.read_csv(input_file)
logging.info(f"Loaded {len(df)} rows from the input file")

def clean_url(url):
    """Clean URL string by removing brackets, quotes, and spaces"""
    url = url.strip("[]' ")
    # Ensure URL is properly encoded
    return quote(url, safe=':/?=&%')

def get_smry_url(url):
    """Generate SMRY.AI URL"""
    return f"https://smry.ai/{clean_url(url)}"

# Function to scrape article text directly from source
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
                    # Get all paragraphs from the container
                    paragraphs = container.find_all('p')
                    if paragraphs:
                        # Join paragraphs and clean the text
                        text = ' '.join([p.get_text().strip() for p in paragraphs])
                        text = ' '.join(text.split())  # Normalize whitespace
                        if len(text) > 100:  # Only return if we found substantial text
                            logging.info(f"Found article text: {text[:100]}...")
                            return text  # Remove the 1000 character limit
            
            # Fallback: try to get all paragraphs from the page
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text().strip() for p in paragraphs])
                text = ' '.join(text.split())
                if len(text) > 100:
                    logging.info(f"Found text using fallback: {text[:100]}...")
                    return text  # Remove the 1000 character limit
            
            logging.warning(f"No substantial text content found for {clean_source_url}")
            return ""
            
    except Exception as e:
        logging.error(f"Error scraping {url}: {str(e)}")
    return ""

# Create a list to store new rows
new_rows = []

# Randomly sample 5 rows from the DataFrame
logging.info("Selecting 5 random rows from the dataset")
sampled_df = df #.sample(n=5, random_state=42)  # random_state for reproducibility
logging.info(f"Selected {len(sampled_df)} random rows")

# Process each row from the random sample
for index, row in sampled_df.iterrows():
    logging.info(f"Processing row {index + 1}/5")
    # Split URLs if multiple exist and clean them
    urls = [clean_url(url.strip()) for url in str(row['urls']).split(',')]
    logging.info(f"Found {len(urls)} URLs in this row")
    
    for url_index, url in enumerate(urls, 1):
        if url:  # Only process non-empty URLs
            logging.info(f"Processing URL {url_index}/{len(urls)}: {url}")
            smry_url = get_smry_url(url)
            # Create a new row with the required columns
            new_row = {
                'URLs': url,  # Original URL
                'SMRY_URLs': smry_url,  # Add SMRY.AI URL
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
            # Add a small delay to avoid overwhelming servers
            logging.info("Waiting 1 second before next request...")
            time.sleep(1)

# Create new DataFrame with processed data
logging.info("Creating final DataFrame")
new_df = pd.DataFrame(new_rows)

# These are the required columns in the exact order we want
required_columns = [
    'URLs',
    'SMRY_URLs',  # Add SMRY.AI URL column
    'DateTime',
    'Title',
    'LangCode',
    'DocTone',
    'Location',
    'CountryCode',
    'ContextualText'
]

# Ensure the DataFrame has all required columns in the correct order
final_df = new_df[required_columns]
logging.info(f"Final DataFrame created with {len(final_df)} rows")

# Save the processed data
output_file = input_file.replace('.csv', '_processed_sample.csv')
logging.info(f"Saving results to: {output_file}")
final_df.to_csv(output_file, index=False, encoding='utf-8')
logging.info("Processing complete!")











