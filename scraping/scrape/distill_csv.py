import pandas as pd
import os
from datetime import datetime

def clean_location(loc):
    """Clean location data, handling NaN and converting to string"""
    if pd.isna(loc):
        return None
    return str(loc)

def combine_csv_files():
    # Read the CSV files with tab delimiter
    events_path = 'data/events/20250405083000.export.CSV'
    mentions_path = 'data/mentions/20250405083000.mentions.CSV'
    existing_aggregated = 'data/gdelt_ggg_aggregated.csv'
    
    # Read existing aggregated data to ensure consistent format
    existing_df = pd.read_csv(existing_aggregated)
    
    events_df = pd.read_csv(events_path, delimiter='\t', encoding='utf-8', on_bad_lines='skip')
    mentions_df = pd.read_csv(mentions_path, delimiter='\t', encoding='utf-8', on_bad_lines='skip')
    
    # Group mentions by URL
    mentions_grouped = mentions_df.groupby('MentionIdentifier').agg({
        'MentionTimeDate': lambda x: sorted(list(set(x)))[0],  # Take earliest mention time
        'MentionSourceName': lambda x: sorted(list(set(x)))[0],  # Take first source name
        'MentionDocTone': 'mean',  # Average tone
        'MentionDocLen': 'first'  # Take first doc length
    }).reset_index()
    
    # Create new dataframe with desired columns
    combined_data = []
    
    for _, row in mentions_grouped.iterrows():
        url = row['MentionIdentifier']
        
        # Get corresponding event data if it exists
        event_data = events_df[events_df['SOURCEURL'] == url].iloc[0] if len(events_df[events_df['SOURCEURL'] == url]) > 0 else None
        
        # Convert YYYYMMDDHHMMSS to datetime
        date_str = str(row['MentionTimeDate'])
        try:
            date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
            formatted_date = date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        except:
            formatted_date = None
            
        # Get locations and country codes from event data
        locations = []
        country_codes = []
        if event_data is not None:
            # Add Actor1 location
            if pd.notna(event_data['Actor1Geo_FullName']):
                loc = clean_location(event_data['Actor1Geo_FullName'])
                if loc:
                    locations.append(loc)
            if pd.notna(event_data['Actor1Geo_CountryCode']):
                code = clean_location(event_data['Actor1Geo_CountryCode'])
                if code:
                    country_codes.append(code)
                
            # Add Actor2 location
            if pd.notna(event_data['Actor2Geo_FullName']):
                loc = clean_location(event_data['Actor2Geo_FullName'])
                if loc:
                    locations.append(loc)
            if pd.notna(event_data['Actor2Geo_CountryCode']):
                code = clean_location(event_data['Actor2Geo_CountryCode'])
                if code:
                    country_codes.append(code)
                
            # Add Action location
            if pd.notna(event_data['ActionGeo_FullName']):
                loc = clean_location(event_data['ActionGeo_FullName'])
                if loc:
                    locations.append(loc)
            if pd.notna(event_data['ActionGeo_CountryCode']):
                code = clean_location(event_data['ActionGeo_CountryCode'])
                if code:
                    country_codes.append(code)
        
        # Remove duplicates while preserving order
        locations = list(dict.fromkeys(locations))
        country_codes = list(dict.fromkeys(country_codes))
        
        combined_data.append({
            'URLs': url,
            'DateTime': formatted_date,
            'Title': '',  # We don't have title information in the original data
            'LangCode': 'eng',  # Assuming English as default
            'DocTone': row['MentionDocTone'],
            'Location': ','.join(locations) if locations else None,
            'CountryCode': ','.join(country_codes) if country_codes else None,
            'ContextualText': ''  # We don't have contextual text in the original data
        })
    
    # Create DataFrame and combine with existing data
    new_df = pd.DataFrame(combined_data)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # Remove duplicates based on URLs
    combined_df = combined_df.drop_duplicates(subset=['URLs'], keep='first')
    
    # Sort by DateTime
    combined_df = combined_df.sort_values('DateTime', na_position='last')
    
    # Save the combined data
    output_path = 'data/gdelt_ggg_aggregated.csv'
    combined_df.to_csv(output_path, index=False)
    
    print(f"\nStatistics:")
    print(f"Number of existing records: {len(existing_df)}")
    print(f"Number of new records: {len(new_df)}")
    print(f"Total unique records after combining: {len(combined_df)}")
    print(f"\nOutput saved to: {output_path}")

def extract_links():
    # Read the CSV files with tab delimiter
    events_path = 'data/events/20250405083000.export.CSV'
    mentions_path = 'data/mentions/20250405083000.mentions.CSV'
    existing_aggregated = 'data/gdelt_ggg_aggregated.csv'
    
    # Read all data sources
    events_df = pd.read_csv(events_path, delimiter='\t', encoding='utf-8', on_bad_lines='skip')
    mentions_df = pd.read_csv(mentions_path, delimiter='\t', encoding='utf-8', on_bad_lines='skip')
    existing_df = pd.read_csv(existing_aggregated)
    
    # Collect all unique URLs
    urls = set()
    
    # Add URLs from events
    urls.update(events_df['SOURCEURL'].dropna().unique())
    
    # Add URLs from mentions
    urls.update(mentions_df['MentionIdentifier'].dropna().unique())
    
    # Add URLs from existing aggregated data
    urls.update(existing_df['URLs'].dropna().unique())
    
    # Convert to DataFrame
    urls_df = pd.DataFrame({'URL': sorted(urls)})
    
    # Save to CSV
    output_path = 'data/links.csv'
    urls_df.to_csv(output_path, index=False)
    
    print(f"\nStatistics:")
    print(f"Total unique URLs: {len(urls)}")
    print(f"\nOutput saved to: {output_path}")

if __name__ == "__main__":
    extract_links()
