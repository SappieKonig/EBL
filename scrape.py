import requests
from bs4 import BeautifulSoup
import datetime
import json
import time
import re

def extract_fox_article_content(soup):
    """Extract structured content from a Fox News article page"""
    result = {
        "title": "",
        "subtitle": "",
        "author": "",
        "date": "",
        "paragraphs": []
    }
    
    # Get article title and subtitle
    title = soup.find('h1', class_='headline')
    subtitle = soup.find('h2', class_='sub-headline')
    
    if title:
        result["title"] = title.text.strip()
    if subtitle:
        result["subtitle"] = subtitle.text.strip()
    
    # Get author and date
    author_byline = soup.find('div', class_='author-byline')
    if author_byline:
        author_links = author_byline.find_all('a')
        if author_links:
            result["author"] = author_links[0].text.strip()
    
    article_date = soup.find('span', class_='article-date')
    if article_date:
        result["date"] = article_date.text.strip()
    
    # Get article content
    article_body = soup.find('div', class_='article-body')
    if article_body:
        # Process paragraphs
        for p in article_body.find_all('p'):
            result["paragraphs"].append(p.get_text().strip())
    
    # Combine paragraphs into full content with proper spacing
    full_content = result["title"] + " - " + result["subtitle"] if result["subtitle"] else result["title"]
    full_content += "\n\nBy " + result["author"] if result["author"] else ""
    full_content += "\n" + result["date"] if result["date"] else ""
    full_content += "\n\n" + "\n\n".join(result["paragraphs"])
    
    return full_content

def get_full_text(url, headers):
    """Extract the full text content from an article URL"""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Fox News specific content extraction
        if "foxnews.com" in url:
            # Use specialized Fox News extraction
            content = extract_fox_article_content(soup)
            if content and len(content) > 200:  # Check if we got meaningful content
                return content
                
            # Fallbacks if the specialized extraction fails
            content_elements = soup.select('.article-body') or soup.select('.article-content') or soup.select('.content-article')
            
            if not content_elements:
                # Fallback to paragraph search in likely containers
                article_container = soup.select_one('.article-container') or soup.select_one('article') or soup
                content_elements = article_container.find_all('p')
        
        # MSNBC specific content extraction
        elif "msnbc.com" in url:
            # Try different article body selectors
            content_elements = soup.select('.article-body__content') or soup.select('.content-body') or soup.select('.article-body')
            
            if not content_elements:
                # Fallback to paragraph search in likely containers
                article_container = soup.select_one('article') or soup.select_one('.article-container') or soup
                content_elements = article_container.find_all('p')
        
        else:
            # Generic approach for other domains
            content_elements = soup.find_all('p')
        
        # Extract text from elements for fallback approaches
        content = ' '.join([elem.get_text().strip() for elem in content_elements])
        
        # Clean up text - remove excess whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # If content seems too short, try a more aggressive approach
        if len(content) < 100:
            # Get all text from the page body and clean it
            body = soup.find('body')
            if body:
                content = body.get_text()
                content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    except Exception as e:
        print(f"Error extracting full text from {url}: {e}")
        return "Failed to extract article content"

def scrape_fox_news():
    articles = []
    urls = [
        "https://www.foxnews.com/us",
        "https://www.foxnews.com/politics",
        "https://www.foxnews.com/media"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for base_url in urls:
        try:
            print(f"Fetching Fox News from {base_url}")
            response = requests.get(base_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Multiple selector strategies
            article_elements = (
                soup.select('.article') or 
                soup.select('.story') or 
                soup.select('.title-content') or
                soup.select('article')
            )
            
            if not article_elements:
                print(f"Fox News ({base_url}): Could not find article elements. Trying alternative approach.")
                article_elements = soup.find_all(['h2', 'h3', 'h4'], class_=lambda c: c and ('title' in c or 'headline' in c))
            
            for article in article_elements[:5]:  # Limit per section for testing
                try:
                    # Try different approaches to find title
                    title_element = None
                    if article.name in ['h2', 'h3', 'h4']:
                        title_element = article
                    else:
                        title_element = article.find(['h2', 'h3', 'h4'])
                    
                    title = title_element.text.strip() if title_element else "No title"
                    
                    # Find link - either in the title element or parent
                    link_element = title_element.find('a') if title_element else None
                    if not link_element and title_element:
                        link_element = title_element.parent.find('a')
                    if not link_element and article:
                        link_element = article.find('a')
                    
                    link = link_element['href'] if link_element and link_element.has_attr('href') else ""
                    if link and not link.startswith('http'):
                        link = "https://www.foxnews.com" + link
                    
                    # Skip if no valid link
                    if not link or not link.startswith('http'):
                        continue
                    
                    # Find published time if available
                    time_element = article.find('time') or article.find(class_=lambda c: c and ('time' in c or 'date' in c))
                    published_time = time_element.text.strip() if time_element else datetime.datetime.now().isoformat()
                    
                    # Get full article text
                    print(f"Getting full text for: {title[:40]}...")
                    content = get_full_text(link, headers)
                    
                    articles.append({
                        "source": "Fox News",
                        "title": title,
                        "url": link,
                        "published_at": published_time,
                        "content": content,
                        "retrieved_at": datetime.datetime.now().isoformat()
                    })
                    
                    print(f"Added Fox News article: {title[:40]}... ({len(content)} chars)")
                    
                except Exception as e:
                    print(f"Error processing Fox News article: {e}")
            
            # Avoid hitting the server too hard
            time.sleep(1)
                    
        except Exception as e:
            print(f"Error fetching Fox News from {base_url}: {e}")
        
    return articles

def scrape_msnbc():
    articles = []
    urls = [
        "https://www.msnbc.com/all",
        "https://www.msnbc.com/politics",
        "https://www.msnbc.com/opinion"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for base_url in urls:
        try:
            print(f"Fetching MSNBC from {base_url}")
            response = requests.get(base_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple potential selectors for MSNBC
            article_elements = (
                soup.select('.styles_content__xbcpl') or 
                soup.select('.styles_teaseCard__suh8k') or
                soup.select('.gsc-item') or
                soup.select('article') or
                soup.select('.styles_card__2oJKK')
            )
            
            if not article_elements:
                print(f"MSNBC ({base_url}): Could not find article elements. Trying alternative approach.")
                article_elements = soup.find_all(['h2', 'h3', 'h4'], class_=lambda c: c and ('title' in c or 'headline' in c))
            
            for article in article_elements[:5]:  # Limit per section for testing
                try:
                    # Try different approaches to find title
                    title_element = None
                    if article.name in ['h2', 'h3', 'h4']:
                        title_element = article
                    else:
                        title_element = article.find(['h2', 'h3', 'h4'])
                    
                    title = title_element.text.strip() if title_element else "No title"
                    
                    # Find link - multiple approaches
                    link_element = title_element.find('a') if title_element else None
                    if not link_element and title_element:
                        link_element = title_element.parent.find('a')
                    if not link_element and article:
                        link_element = article.find('a')
                    
                    link = link_element['href'] if link_element and link_element.has_attr('href') else ""
                    if link and not link.startswith('http'):
                        link = "https://www.msnbc.com" + link
                    
                    # Skip if no valid link
                    if not link or not link.startswith('http'):
                        continue
                    
                    # Find published time if available
                    time_element = article.find('time') or article.find(class_=lambda c: c and ('time' in c or 'date' in c))
                    published_time = time_element.text.strip() if time_element else datetime.datetime.now().isoformat()
                    
                    # Get full article text
                    print(f"Getting full text for: {title[:40]}...")
                    content = get_full_text(link, headers)
                    
                    articles.append({
                        "source": "MSNBC",
                        "title": title,
                        "url": link,
                        "published_at": published_time,
                        "content": content,
                        "retrieved_at": datetime.datetime.now().isoformat()
                    })
                    
                    print(f"Added MSNBC article: {title[:40]}... ({len(content)} chars)")
                    
                except Exception as e:
                    print(f"Error processing MSNBC article: {e}")
            
            # Avoid hitting the server too hard
            time.sleep(1)
                    
        except Exception as e:
            print(f"Error fetching MSNBC from {base_url}: {e}")
        
    return articles

def save_to_json(articles, filename="news_articles.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(articles)} articles to {filename}")

def process_single_url(url):
    """Process a single article URL and return its content"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Processing single article: {url}")
    content = get_full_text(url, headers)
    
    source = "Fox News" if "foxnews.com" in url else "MSNBC" if "msnbc.com" in url else "Unknown"
    
    article = {
        "source": source,
        "url": url,
        "content": content,
        "retrieved_at": datetime.datetime.now().isoformat()
    }
    
    print(f"Content length: {len(content)} characters")
    return article

def main():
    import sys
    
    # Check if a specific URL was provided
    if len(sys.argv) > 1 and sys.argv[1].startswith('http'):
        # Process single URL mode
        url = sys.argv[1]
        article = process_single_url(url)
        save_to_json([article], "single_article.json")
        return
    
    # Otherwise run the full scraper
    print("Scraping Fox News...")
    fox_articles = scrape_fox_news()
    print(f"Found {len(fox_articles)} Fox News articles")
    
    print("\nScraping MSNBC...")
    msnbc_articles = scrape_msnbc()
    print(f"Found {len(msnbc_articles)} MSNBC articles")
    
    all_articles = fox_articles + msnbc_articles
    
    print(f"\nFound {len(all_articles)} articles total")
    
    # Save to JSON
    save_to_json(all_articles, "recent_news.json")
    
    # Display a sample of what was found
    if all_articles:
        print("\nSample of articles found:")
        for i, article in enumerate(all_articles[:3]):
            print(f"{i+1}. {article['source']}: {article['title'][:50]}...")
            print(f"   Content length: {len(article['content'])} characters")
            print(f"   URL: {article['url']}")
            print()

if __name__ == "__main__":
    main()