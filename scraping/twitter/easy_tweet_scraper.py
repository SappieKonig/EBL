#!/usr/bin/env python3
"""
Easy Twitter Country Scraper
----------------------------
A simplified interface for running the Twitter country scraper.
This script provides a simple interactive interface so you don't
need to remember command-line arguments.
"""

import os
import sys
from twitter_country_scraper_advanced import TwitterCountryScraper

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the program header"""
    print("\n" + "="*70)
    print(" "*22 + "TWITTER COUNTRY SCRAPER" + " "*22)
    print("="*70)
    print("This tool will help you scrape tweets from specific countries")
    print("You will need to log in to Twitter/X manually when the browser opens")
    print("="*70 + "\n")

def get_countries():
    """Get the list of countries to scrape"""
    print("Enter the countries you want to scrape (one per line)")
    print("Press Enter on an empty line when done\n")
    
    countries = []
    while True:
        country = input(f"Country {len(countries)+1} (or press Enter to finish): ").strip()
        if not country:
            break
        countries.append(country)
    
    if not countries:
        print("\nNo countries entered, using default: United States")
        return ["United States"]
    
    return countries

def get_limit():
    """Get the maximum number of tweets to collect per country"""
    while True:
        try:
            limit = input("\nMaximum tweets per country (default: 100): ").strip()
            if not limit:
                return 100
            limit = int(limit)
            if limit <= 0:
                print("Please enter a positive number")
                continue
            return limit
        except ValueError:
            print("Please enter a valid number")

def get_language():
    """Get the language filter"""
    language = input("\nLanguage filter (e.g., 'en' for English, press Enter to skip): ").strip()
    return language if language else None

def get_keywords():
    """Get the keywords filter"""
    keywords = input("\nKeywords to filter by (e.g., 'climate change', press Enter to skip): ").strip()
    return keywords if keywords else None

def get_date_range():
    """Get the date range for tweets"""
    print("\nDate range (format: YYYY-MM-DD)")
    date_since = input("From date (press Enter to skip): ").strip()
    date_until = input("To date (press Enter to skip): ").strip()
    
    return date_since if date_since else None, date_until if date_until else None

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
    folder = input("\nOutput folder (default: data/twitter): ").strip()
    return folder if folder else "data/twitter"

def main():
    """Main function"""
    clear_screen()
    print_header()
    
    # Get user preferences
    countries = get_countries()
    limit = get_limit()
    language = get_language()
    keywords = get_keywords()
    date_since, date_until = get_date_range()
    output_format = get_output_format()
    output_folder = get_output_folder()
    
    # Confirm settings
    clear_screen()
    print("\n" + "="*50)
    print("SETTINGS SUMMARY")
    print("="*50)
    print(f"Countries: {', '.join(countries)}")
    print(f"Max tweets per country: {limit}")
    print(f"Language filter: {language if language else 'None'}")
    print(f"Keywords: {keywords if keywords else 'None'}")
    print(f"Date range: {date_since if date_since else 'Any'} to {date_until if date_until else 'Any'}")
    print(f"Output format: {output_format}")
    print(f"Output folder: {output_folder}")
    print("="*50)
    
    confirm = input("\nStart scraping with these settings? (y/n): ").lower()
    if not confirm.startswith('y'):
        print("Cancelled by user. Exiting...")
        sys.exit()
    
    # Initialize the scraper
    scraper = TwitterCountryScraper(data_folder=output_folder)
    
    try:
        # Setup browser and wait for manual login
        scraper.setup_browser()
        scraper.goto_twitter()
        
        # Scrape tweets for each country
        for country in countries:
            print(f"\nScraping tweets for {country}...")
            tweets = scraper.search_by_country(
                country_name=country,
                language=language,
                limit=limit,
                keywords=keywords,
                date_since=date_since,
                date_until=date_until
            )
            
            if tweets:
                # Save based on output format preference
                if output_format in ["csv", "both"]:
                    scraper.save_tweets(tweets, country, format="csv")
                if output_format in ["json", "both"]:
                    scraper.save_tweets(tweets, country, format="json")
        
        print("\n" + "="*50)
        print("SCRAPING COMPLETED")
        print("="*50)
        print(f"Data has been saved to: {output_folder}")
        print("="*50)
    
    finally:
        # Clean up resources
        scraper.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")
    finally:
        print("\nGoodbye!") 