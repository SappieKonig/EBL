import requests
import gzip
import json
import csv
import os
from pathlib import Path
from tqdm import tqdm

def download_and_extract_gdelt_gz():
    """
    Downloads the GDELT Global Geographic Graph GZ file, extracts it, and saves as two CSV files:
    1. Main CSV with URL and ContextualText as first columns
    2. Aggregated CSV with unique ContextualText entries and their associated URLs,
       based on first deduplicating by URL and then comparing context.
    """
    # URL of the GDELT Global Geographic Graph GZ file
    url = "http://data.gdeltproject.org/gdeltv3/ggg/20250404.ggg.v1.english.json.gz"
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Output file paths
    output_file = data_dir / "gdelt_ggg_data.csv"
    aggregated_file = data_dir / "gdelt_ggg_aggregated.csv"
    
    print(f"Downloading GDELT data from {url}...")
    
    try:
        # Download the GZ file with progress bar
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get total file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        # Process the JSONL data line by line
        # Define the order of the first two columns
        primary_fields = ['URL', 'ContextualText']
        # Other fields we want to ensure are included
        essential_fields = set(['DateTime', 'Title', 'Location', 'CountryCode', 'GeoType', 'Lat', 'Lon'])
        field_names = set(primary_fields) | essential_fields
        unique_entries = {}  # Dictionary to store entries by URL
        
        # First pass: collect all field names and combine entries with same URL
        print("\nProcessing downloaded data...")
        downloaded_lines = []
        
        # Download and decompress with progress bar
        with tqdm(total=total_size, unit='iB', unit_scale=True, desc="Downloading") as pbar:
            with gzip.GzipFile(fileobj=response.raw) as gz_file:
                for chunk in gz_file:
                    downloaded_lines.append(chunk.decode('utf-8').strip())
                    pbar.update(len(chunk))
        
        # Process lines with progress bar
        with tqdm(total=len(downloaded_lines), desc="Processing entries") as pbar:
            for line in downloaded_lines:
                try:
                    if not line:
                        continue
                        
                    entry = json.loads(line)
                    if not isinstance(entry, dict):
                        continue
                        
                    url_key = entry.get('URL', '')
                    context = entry.get('ContextualText', '').strip()
                    if not url_key or not context:  # Skip entries without URL or context
                        continue
                        
                    field_names.update(entry.keys())
                    
                    if url_key in unique_entries:
                        # Combine entries with the same URL
                        existing_entry = unique_entries[url_key]
                        for key, value in entry.items():
                            if not value:  # Skip empty values
                                continue
                                
                            if key == 'ContextualText':
                                # For ContextualText, combine sentences and remove duplicates
                                existing_text = existing_entry.get(key, '')
                                if existing_text:
                                    # Split by sentence endings and clean
                                    current_texts = {s.strip() for s in existing_text.split('.')}
                                    new_texts = {s.strip() for s in value.split('.')}
                                    # Combine and filter empty strings
                                    combined_texts = {s for s in current_texts.union(new_texts) if s}
                                    # Join back with proper punctuation
                                    existing_entry[key] = '. '.join(combined_texts) + ('.' if combined_texts else '')
                                else:
                                    existing_entry[key] = value
                            elif key not in existing_entry:
                                existing_entry[key] = value
                            elif value != existing_entry[key] and key not in ['DateTime', 'Title', 'URL']:
                                # For other fields with different values (except unique identifiers), combine with comma
                                existing_value = str(existing_entry[key])
                                new_value = str(value)
                                values = {v.strip() for v in existing_value.split(',') + new_value.split(',')}
                                existing_entry[key] = ','.join(filter(None, values))
                    else:
                        # New unique URL entry
                        unique_entries[url_key] = entry
                        
                except json.JSONDecodeError as e:
                    if line.strip():  # Only report error for non-empty lines
                        print(f"Warning: Skipping invalid JSON line: {e}")
                    continue
                finally:
                    pbar.update(1)
        
        if not unique_entries:
            print("Error: No valid entries found in the data")
            return False
            
        # Create ordered list of field names with URL and ContextualText first
        ordered_fields = primary_fields + sorted(list(field_names - set(primary_fields)))
        
        # Write main CSV file
        print("\nWriting main CSV file...")
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ordered_fields)
            writer.writeheader()
            for entry in tqdm(unique_entries.values(), desc="Writing entries"):
                writer.writerow(entry)
        
        # Now process unique entries to find similar context
        print("\nProcessing similar contexts...")
        context_to_urls = {}
        
        # Pre-process all contexts first
        processed_contexts = []
        for url_key, entry in unique_entries.items():
            context = entry.get('ContextualText', '').strip()
            if context:
                # Clean and normalize the context
                sentences = frozenset(s.strip() for s in context.split('.') if s.strip())
                if sentences:  # Only add non-empty sentence sets
                    processed_contexts.append((url_key, sentences))

        # Sort contexts by length for more efficient matching
        processed_contexts.sort(key=lambda x: len(x[1]))
        
        # Process contexts in batches for better performance
        batch_size = 1000
        with tqdm(total=len(processed_contexts), desc="Comparing contexts") as pbar:
            for i, (url_key, sentences) in enumerate(processed_contexts):
                if not sentences:
                    pbar.update(1)
                    continue
                
                # Find the normalized context string
                normalized_context = '. '.join(sentences) + '.'
                
                # Look for matches only in nearby contexts by length
                # This optimization assumes similar texts have similar lengths
                min_len = len(sentences) * 0.8  # 80% of current length
                max_len = len(sentences) * 1.25  # 125% of current length
                
                found_match = False
                # Only compare with existing contexts that are within our length bounds
                for existing_context, existing_urls in context_to_urls.items():
                    existing_sentences = frozenset(s.strip() for s in existing_context.split('.') if s.strip())
                    
                    if not (min_len <= len(existing_sentences) <= max_len):
                        continue
                        
                    # Use set intersection for faster comparison
                    overlap = len(sentences & existing_sentences)
                    min_size = min(len(sentences), len(existing_sentences))
                    
                    if overlap >= 0.8 * min_size:  # 80% or more similarity
                        existing_urls.add(url_key)
                        found_match = True
                        break
                
                if not found_match:
                    context_to_urls[normalized_context] = {url_key}
                
                pbar.update(1)
                
                # Periodically clear memory by removing contexts that are too small
                if i % batch_size == 0 and i > 0:
                    current_len = len(sentences)
                    context_to_urls = {
                        k: v for k, v in context_to_urls.items() 
                        if len(k.split('.')) >= current_len * 0.7
                    }

        # Write aggregated CSV file with unique ContextualText entries
        print("\nWriting aggregated CSV file...")
        with open(aggregated_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Update header with new fields
            writer.writerow(['URLs', 'DateTime', 'Title', 'LangCode', 'DocTone', 'Location', 'CountryCode', 'ContextualText'])
            
            for context, urls in tqdm(context_to_urls.items(), desc="Writing unique contexts"):
                # Get the first URL's entry to extract additional fields
                first_url = next(iter(urls))
                entry = unique_entries[first_url]
                
                # Extract fields, using empty string as default if not present
                datetime = entry.get('DateTime', '')
                title = entry.get('Title', '')
                langcode = entry.get('LangCode', '')
                doctone = entry.get('DocTone', '')
                location = entry.get('Location', '')
                countrycode = entry.get('CountryCode', '')
                
                # Write row with all fields
                writer.writerow([
                    '|'.join(sorted(urls)),
                    datetime,
                    title,
                    langcode,
                    doctone,
                    location,
                    countrycode,
                    context
                ])
                
        print(f"\nData successfully extracted and saved to:")
        print(f"1. Main file: {output_file}")
        print(f"2. Aggregated file: {aggregated_file}")
        print(f"Processed {len(unique_entries)} unique URLs and {len(context_to_urls)} unique context entries")
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return False

if __name__ == "__main__":
    download_and_extract_gdelt_gz()
