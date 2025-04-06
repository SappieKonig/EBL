import pandas as pd
import sys

try:
    # Read the files with explicit encoding
    mentions_df = pd.read_csv('data/mentions/20250405083000.mentions.CSV', encoding='utf-8')
    print("Successfully read mentions file")
    
    events_df = pd.read_csv('data/events/20250405083000.export.CSV', encoding='utf-8')
    print("Successfully read events file")

    # Get unique URLs and their corresponding data
    mentions_subset = mentions_df[['GlobalEventID', 'MentionIdentifier', 'MentionTimeDate', 'MentionDocTone']].drop_duplicates()
    mentions_subset = mentions_subset.rename(columns={
        'MentionIdentifier': 'URLs',
        'MentionTimeDate': 'DateTime',
        'MentionDocTone': 'DocTone'
    })

    # Merge with events data
    events_subset = events_df[['GlobalEventID', 'ActionGeo_CountryCode', 'ActionGeo_FullName', 'SOURCEURL', 'Title', 'LangCode', 'ContextualText']]
    events_subset = events_subset.rename(columns={
        'ActionGeo_CountryCode': 'CountryCode',
        'ActionGeo_FullName': 'Location'
    })

    # Merge the dataframes
    result = pd.merge(mentions_subset, events_subset, on='GlobalEventID', how='left')

    # Select and reorder final columns
    final_columns = ['URLs', 'DateTime', 'Title', 'LangCode', 'DocTone', 'Location', 'CountryCode', 'ContextualText']
    result = result[final_columns].drop_duplicates()

    # Save to CSV
    result.to_csv('data/combined_articles.csv', index=False, encoding='utf-8')
    print('Created combined_articles.csv with shape:', result.shape)
    print('\nFirst few rows preview:')
    print(result.head().to_string())

except Exception as e:
    print(f"An error occurred: {str(e)}", file=sys.stderr)
    print(f"Error type: {type(e).__name__}", file=sys.stderr) 