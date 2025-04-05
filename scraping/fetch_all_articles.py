from gdelt_geo_api import GDELTGeoAPI
import pandas as pd
from pathlib import Path
import logging
import datetime
import time
import json
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COUNTRY_CODES = {
    'AF': 'Afghanistan', 'AL': 'Albania', 'AG': 'Algeria', 'AO': 'Angola', 'AR': 'Argentina',
    'AM': 'Armenia', 'AS': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan', 'BS': 'Bahamas',
    'BH': 'Bahrain', 'BD': 'Bangladesh', 'BY': 'Belarus', 'BE': 'Belgium', 'BO': 'Bolivia',
    'BA': 'Bosnia-Herzegovina', 'BR': 'Brazil', 'BG': 'Bulgaria', 'KH': 'Cambodia', 'CM': 'Cameroon',
    'CA': 'Canada', 'CL': 'Chile', 'CN': 'China', 'CO': 'Colombia', 'CR': 'Costa Rica',
    'HR': 'Croatia', 'CU': 'Cuba', 'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark',
    'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador', 'EE': 'Estonia',
    'ET': 'Ethiopia', 'FI': 'Finland', 'FR': 'France', 'GE': 'Georgia', 'DE': 'Germany',
    'GH': 'Ghana', 'GR': 'Greece', 'GT': 'Guatemala', 'HT': 'Haiti', 'HN': 'Honduras',
    'HK': 'Hong Kong', 'HU': 'Hungary', 'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia',
    'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland', 'IL': 'Israel', 'IT': 'Italy',
    'JM': 'Jamaica', 'JP': 'Japan', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya',
    'KR': 'South Korea', 'KW': 'Kuwait', 'LV': 'Latvia', 'LB': 'Lebanon', 'LY': 'Libya',
    'LT': 'Lithuania', 'LU': 'Luxembourg', 'MK': 'Macedonia', 'MY': 'Malaysia', 'MT': 'Malta',
    'MX': 'Mexico', 'MD': 'Moldova', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MA': 'Morocco',
    'NP': 'Nepal', 'NL': 'Netherlands', 'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NG': 'Nigeria',
    'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan', 'PS': 'Palestine', 'PA': 'Panama',
    'PY': 'Paraguay', 'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland', 'PT': 'Portugal',
    'QA': 'Qatar', 'RO': 'Romania', 'RU': 'Russia', 'SA': 'Saudi Arabia', 'RS': 'Serbia',
    'SG': 'Singapore', 'SK': 'Slovakia', 'SI': 'Slovenia', 'ZA': 'South Africa', 'ES': 'Spain',
    'LK': 'Sri Lanka', 'SE': 'Sweden', 'CH': 'Switzerland', 'SY': 'Syria', 'TW': 'Taiwan',
    'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand', 'TN': 'Tunisia', 'TR': 'Turkey',
    'UG': 'Uganda', 'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom',
    'US': 'United States', 'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VE': 'Venezuela', 'VN': 'Vietnam',
    'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
}

def get_comprehensive_query() -> str:
    """
    Create a comprehensive query that captures all articles by using
    fewer major countries to avoid query length issues.
    """
    # Use fewer major countries to avoid query length issues
    countries = ["US", "GB", "FR"]
    query = "(" + " OR ".join([f"sourcecountry:{c}" for c in countries]) + ")"
    logger.info(f"Using query: {query}")  # Print the query being used
    return query

def fetch_articles_for_timespan(geo_api: GDELTGeoAPI, 
                              hours: int,
                              max_retries: int = 3) -> Optional[List[Dict]]:
    """
    Fetch articles for a specific timespan with retries.
    
    Args:
        geo_api (GDELTGeoAPI): API client
        hours (int): Number of hours to fetch
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        Optional[List[Dict]]: List of article contexts or None if failed
    """
    for attempt in range(max_retries):
        try:
            # Query with ArtList mode to get article details
            result = geo_api.query(
                query=get_comprehensive_query(),
                mode="ArtList",  # Use ArtList mode to get article details
                output_format="GeoJSON",
                timespan=f"{hours}h",
                maxpoints=250,
                sortby="DateDesc"
            )
            
            # Print the raw JSON response
            logger.info("API Response:")
            logger.info(json.dumps(result, indent=2))
            
            if not result or "features" not in result:
                logger.warning(f"No features found for timespan {hours} hours")
                return None
                
            # Extract article contexts with content
            articles = []
            for feature in result.get("features", []):
                props = feature.get("properties", {})
                article = {
                    "location_name": props.get("name", ""),
                    "mention_count": props.get("count", 0),
                    "normalized_score": 0,  # Default score
                    "geometry": feature.get("geometry", {}),
                    "urls": [],  # List to store article URLs
                    "titles": [],  # List to store article titles
                    "content": ""  # Store article content/snippets
                }
                
                # Parse HTML content to extract URLs and titles
                html_content = props.get("html", "")
                if html_content:
                    # Simple HTML parsing to extract links and titles
                    import re
                    links = re.findall(r'href="([^"]+)"', html_content)
                    titles = re.findall(r'title="([^"]+)"', html_content)
                    article["urls"] = links
                    article["titles"] = titles
                    article["content"] = html_content  # Store the full HTML content
                
                articles.append(article)
            
            # Print article count
            if articles:
                logger.info(f"Found {len(articles)} articles")
                # Print first article as sample
                if len(articles) > 0:
                    logger.info("Sample article:")
                    logger.info(json.dumps(articles[0], indent=2))
            
            return articles
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch articles after {max_retries} attempts: {str(e)}")
                return None

def save_articles_batch(articles: List[Dict], output_path: Path, mode: str = 'a') -> None:
    """
    Save a batch of articles to CSV.
    
    Args:
        articles (List[Dict]): Articles to save
        output_path (Path): Path to save to
        mode (str): File mode ('a' for append, 'w' for write)
    """
    if not articles:
        return
        
    # Convert articles to DataFrame
    df = pd.json_normalize(articles)
    
    # Ensure we have all the important columns
    required_columns = [
        'location_name', 
        'mention_count', 
        'normalized_score',
        'geometry.type', 
        'geometry.coordinates',
        'urls',  # Article URLs
        'titles',  # Article titles
        'content'  # Article content/snippets
    ]
    
    # Add missing columns with empty values
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
            
    # Save to CSV with all fields
    df.to_csv(output_path, mode=mode, header=(mode=='w'), index=False, encoding='utf-8')
    logger.info(f"Saved batch of {len(df)} articles")

def get_country_query(country: str) -> str:
    """
    Create a query for a specific country.
    
    Args:
        country (str): Country code (e.g., 'US', 'GB')
        
    Returns:
        str: Query string for the country
    """
    query = f"sourcecountry:{country}"
    logger.info(f"Using query for {country}: {query}")
    return query

def fetch_articles_by_country(days: int = 1, slice_hours: int = 12) -> str:
    """
    Fetch articles country by country and save them to a CSV file.
    
    Args:
        days (int): Number of days of data to fetch
        slice_hours (int): Size of each time slice in hours
        
    Returns:
        str: Path to the saved CSV file
    """
    # Initialize the API client
    geo_api = GDELTGeoAPI()
    
    try:
        # Create output directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data") / "countries"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main output file
        filename = f"all_countries_{days}d_{timestamp}.csv"
        output_path = output_dir / filename
        
        total_articles = 0
        country_stats = []  # To keep track of articles per country
        
        # Process each country
        for code, name in COUNTRY_CODES.items():
            logger.info(f"Processing articles from {name} ({code})")
            
            # Calculate number of slices
            total_hours = days * 24
            num_slices = total_hours // slice_hours
            
            country_articles = []
            country_article_count = 0
            
            # Process each time slice for the country
            for i in range(num_slices):
                current_hours = slice_hours
                if i == num_slices - 1:  # Last slice
                    current_hours = total_hours - (i * slice_hours)
                    
                logger.info(f"Processing {name} slice {i+1}/{num_slices}: {current_hours} hours")
                
                try:
                    # Query with ArtList mode to get article details
                    result = geo_api.query(
                        query=get_country_query(code),
                        mode="ArtList",
                        output_format="GeoJSON",
                        timespan=f"{current_hours}h",
                        maxpoints=250,
                        sortby="DateDesc"
                    )
                    
                    if result and "features" in result:
                        # Extract article data
                        for feature in result.get("features", []):
                            props = feature.get("properties", {})
                            article = {
                                "country_code": code,
                                "country_name": name,
                                "location_name": props.get("name", ""),
                                "mention_count": props.get("count", 0),
                                "normalized_score": 0,
                                "geometry": feature.get("geometry", {}),
                                "urls": [],
                                "titles": [],
                                "content": ""
                            }
                            
                            # Parse HTML content to extract URLs and titles
                            html_content = props.get("html", "")
                            if html_content:
                                import re
                                links = re.findall(r'href="([^"]+)"', html_content)
                                titles = re.findall(r'title="([^"]+)"', html_content)
                                article["urls"] = links
                                article["titles"] = titles
                                article["content"] = html_content
                            
                            country_articles.append(article)
                            country_article_count += 1
                    
                    # Small delay between requests
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing {name} slice {i+1}: {str(e)}")
                    continue
            
            # Save country articles
            if country_articles:
                df = pd.json_normalize(country_articles)
                mode = 'w' if total_articles == 0 else 'a'
                df.to_csv(output_path, mode=mode, header=(mode=='w'), index=False, encoding='utf-8')
                
                total_articles += len(country_articles)
                logger.info(f"Saved {len(country_articles)} articles from {name}")
                
                # Record country statistics
                country_stats.append({
                    'country_code': code,
                    'country_name': name,
                    'articles_found': country_article_count
                })
            
            # Save country statistics
            stats_df = pd.DataFrame(country_stats)
            stats_df.to_csv(output_dir / f"country_stats_{timestamp}.csv", index=False)
        
        logger.info(f"Successfully saved {total_articles} articles from {len(COUNTRY_CODES)} countries to {output_path}")
        logger.info(f"Country statistics saved to {output_dir}/country_stats_{timestamp}.csv")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error in fetch_articles_by_country: {str(e)}")
        raise

if __name__ == "__main__":
    # Fetch last day of articles by country
    fetch_articles_by_country(days=1, slice_hours=1) #decrease slice_hours to get more articles, now max 250 articles per slice