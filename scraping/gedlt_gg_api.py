import requests
import gzip
import json
import os
from pathlib import Path

def download_and_extract_gdelt_gz():
    """
    Downloads the GDELT Global Geographic Graph GZ file and saves it as JSONL.
    Each line of the file is a separate JSON object.
    """
    # URL of the GDELT Global Geographic Graph GZ file
    url = "http://data.gdeltproject.org/gdeltv3/ggg/20250404.ggg.v1.english.json.gz"
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Output JSON file path
    output_file = data_dir / "gdelt_ggg_data.jsonl"
    
    print(f"Downloading GDELT data from {url}...")
    
    try:
        # Download the GZ file
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Track count of processed records
        record_count = 0
        
        # Write the decompressed content line by line
        with gzip.GzipFile(fileobj=response.raw) as gz_file, open(output_file, 'wb') as out_file:
            # Process and write the file line by line
            for line in gz_file:
                out_file.write(line)
                record_count += 1
                
                # Print progress every 10000 records
                if record_count % 10000 == 0:
                    print(f"Processed {record_count} records...")
                
        print(f"Data successfully extracted and saved to {output_file}")
        print(f"Total records: {record_count}")
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return False

if __name__ == "__main__":
    download_and_extract_gdelt_gz() 