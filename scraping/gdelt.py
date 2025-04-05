import pandas as pd
import requests
from io import StringIO
from typing import Optional, Dict, List, Union, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum
import zipfile
import io
import os
import pathlib

class GDELTFileType(Enum):
    EVENTS = "export.CSV"
    MENTIONS = "mentions.CSV"
    GKG = "gkg.csv"

class QuadClass(Enum):
    VERBAL_COOPERATION = 1
    MATERIAL_COOPERATION = 2
    VERBAL_CONFLICT = 3
    MATERIAL_CONFLICT = 4

@dataclass
class GDELTEvent:
    """Data class representing a GDELT event record"""
    global_event_id: int
    sql_date: int
    month_year: int
    year: int
    fraction_date: float
    actor1_code: str
    actor1_name: str
    actor1_country_code: str
    actor1_known_group_code: str
    actor1_ethnic_code: str
    actor1_religion1_code: str
    actor1_religion2_code: str
    actor1_type1_code: str
    actor1_type2_code: str
    actor1_type3_code: str
    actor2_code: str
    actor2_name: str
    actor2_country_code: str
    actor2_known_group_code: str
    actor2_ethnic_code: str
    actor2_religion1_code: str
    actor2_religion2_code: str
    actor2_type1_code: str
    actor2_type2_code: str
    actor2_type3_code: str
    is_root_event: int
    event_code: str
    event_base_code: str
    event_root_code: str
    quad_class: int
    goldstein_scale: float
    num_mentions: int
    num_sources: int
    num_articles: int
    avg_tone: float
    actor1_geo_type: int
    actor1_geo_fullname: str
    actor1_geo_country_code: str
    actor1_geo_adm1_code: str
    actor1_geo_lat: float
    actor1_geo_long: float
    actor2_geo_type: int
    actor2_geo_fullname: str
    actor2_geo_country_code: str
    actor2_geo_adm1_code: str
    actor2_geo_lat: float
    actor2_geo_long: float
    action_geo_type: int
    action_geo_fullname: str
    action_geo_country_code: str
    action_geo_adm1_code: str
    action_geo_lat: float
    action_geo_long: float
    date_added: int
    source_url: str

@dataclass
class GDELTMention:
    """Data class representing a GDELT mention record"""
    global_event_id: int
    event_time_date: int
    mention_time_date: int
    mention_type: int
    mention_source_name: str
    mention_identifier: str
    sentence_id: int
    actor1_char_offset: int
    actor2_char_offset: int
    action_char_offset: int
    in_raw_text: int
    confidence: int
    mention_doc_len: int
    mention_doc_tone: float
    mention_doc_translation_info: str
    extras: str

class GDELT:
    """
    A class to handle GDELT data fetching and processing.
    Supports Events, Mentions, and GKG data sources.
    """
    
    # GDELT column names based on the codebook
    EVENT_COLUMNS = [
        'GLOBALEVENTID', 'SQLDATE', 'MonthYear', 'Year', 'FractionDate',
        'Actor1Code', 'Actor1Name', 'Actor1CountryCode', 'Actor1KnownGroupCode',
        'Actor1EthnicCode', 'Actor1Religion1Code', 'Actor1Religion2Code',
        'Actor1Type1Code', 'Actor1Type2Code', 'Actor1Type3Code',
        'Actor2Code', 'Actor2Name', 'Actor2CountryCode', 'Actor2KnownGroupCode',
        'Actor2EthnicCode', 'Actor2Religion1Code', 'Actor2Religion2Code',
        'Actor2Type1Code', 'Actor2Type2Code', 'Actor2Type3Code',
        'IsRootEvent', 'EventCode', 'EventBaseCode', 'EventRootCode',
        'QuadClass', 'GoldsteinScale', 'NumMentions', 'NumSources', 'NumArticles',
        'AvgTone', 'Actor1Geo_Type', 'Actor1Geo_FullName', 'Actor1Geo_CountryCode',
        'Actor1Geo_ADM1Code', 'Actor1Geo_Lat', 'Actor1Geo_Long',
        'Actor2Geo_Type', 'Actor2Geo_FullName', 'Actor2Geo_CountryCode',
        'Actor2Geo_ADM1Code', 'Actor2Geo_Lat', 'Actor2Geo_Long',
        'ActionGeo_Type', 'ActionGeo_FullName', 'ActionGeo_CountryCode',
        'ActionGeo_ADM1Code', 'ActionGeo_Lat', 'ActionGeo_Long', 'DATEADDED',
        'SOURCEURL'
    ]

    MENTION_COLUMNS = [
        'GlobalEventID', 'EventTimeDate', 'MentionTimeDate', 'MentionType',
        'MentionSourceName', 'MentionIdentifier', 'SentenceID', 'Actor1CharOffset',
        'Actor2CharOffset', 'ActionCharOffset', 'InRawText', 'Confidence',
        'MentionDocLen', 'MentionDocTone', 'MentionDocTranslationInfo', 'Extras'
    ]

    def __init__(self, data_dir: str = "data"):
        """
        Initialize GDELT with a data directory for saving files.
        
        Args:
            data_dir (str): Directory to save downloaded and processed data
        """
        self.base_url = "http://data.gdeltproject.org/gdeltv2"
        self.logger = logging.getLogger(__name__)
        
        # Set up data directory structure
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different file types
        self.events_dir = self.data_dir / "events"
        self.mentions_dir = self.data_dir / "mentions"
        self.gkg_dir = self.data_dir / "gkg"
        self.processed_dir = self.data_dir / "processed"
        
        for dir_path in [self.events_dir, self.mentions_dir, self.gkg_dir, self.processed_dir]:
            dir_path.mkdir(exist_ok=True)
            
        self.logger.info(f"Initialized GDELT with data directory: {self.data_dir.absolute()}")

    def _save_csv(self, content: str, timestamp: str, file_type: GDELTFileType) -> str:
        """
        Save CSV content to a file with column headers.
        
        Args:
            content (str): CSV content to save
            timestamp (str): Timestamp of the data
            file_type (GDELTFileType): Type of GDELT file
            
        Returns:
            str: Path to the saved file
        """
        # Determine the appropriate directory based on file type
        if file_type == GDELTFileType.EVENTS:
            save_dir = self.events_dir
            columns = self.EVENT_COLUMNS
        elif file_type == GDELTFileType.MENTIONS:
            save_dir = self.mentions_dir
            columns = self.MENTION_COLUMNS
        else:
            save_dir = self.gkg_dir
            columns = []  # GKG columns will be added when implemented
            
        # Create filename
        filename = f"{timestamp}.{file_type.value}"
        filepath = save_dir / filename
        
        # Add column headers to the content
        header = '\t'.join(columns) + '\n'
        content_with_header = header + content
        
        # Save the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_with_header)
            
        self.logger.info(f"Saved {file_type.name} data to {filepath}")
        return str(filepath)

    def _save_dataframe(self, df: pd.DataFrame, timestamp: str, 
                       file_type: GDELTFileType, suffix: str = "") -> str:
        """
        Save a processed DataFrame to CSV with headers.
        
        Args:
            df (pd.DataFrame): DataFrame to save
            timestamp (str): Timestamp of the data
            file_type (GDELTFileType): Type of GDELT file
            suffix (str): Optional suffix for the filename
            
        Returns:
            str: Path to the saved file
        """
        filename = f"{timestamp}.{file_type.value}"
        if suffix:
            filename = f"{filename[:-4]}_{suffix}.csv"
            
        filepath = self.processed_dir / filename
        
        # Save with headers and using tab delimiter for consistency
        df.to_csv(filepath, index=False, sep='\t')
        self.logger.info(f"Saved processed {file_type.name} data to {filepath}")
        return str(filepath)

    def _fetch_and_extract_zip(self, url: str) -> Optional[str]:
        """
        Fetch a zip file from GDELT and extract its contents.
        
        Args:
            url (str): URL of the zip file
            
        Returns:
            Optional[str]: Extracted CSV content or None if failed
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Get the first file in the zip (there should only be one)
                csv_filename = z.namelist()[0]
                return z.read(csv_filename).decode('utf-8')
                
        except Exception as e:
            self.logger.error(f"Failed to fetch/extract zip file: {str(e)}")
            return None

    def fetch_data(self, timestamp: str, file_type: GDELTFileType) -> Optional[pd.DataFrame]:
        """
        Fetch GDELT data for a specific timestamp and file type.
        
        Args:
            timestamp (str): Timestamp in YYYYMMDDHHMMSS format
            file_type (GDELTFileType): Type of GDELT file to fetch
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing the data
        """
        try:
            filename = f"{timestamp}.{file_type.value}.zip"
            url = f"{self.base_url}/{filename}"
            
            self.logger.info(f"Fetching GDELT {file_type.name} data from {url}")
            csv_content = self._fetch_and_extract_zip(url)
            
            if csv_content is None:
                return None
                
            # Save the raw CSV content
            self._save_csv(csv_content, timestamp, file_type)
            
            # Parse the CSV content
            data = StringIO(csv_content)
            columns = self.EVENT_COLUMNS if file_type == GDELTFileType.EVENTS else self.MENTION_COLUMNS
            df = pd.read_csv(data, sep='\t', header=None, names=columns)
            
            # Convert numeric columns based on file type
            if file_type == GDELTFileType.EVENTS:
                self._convert_event_numeric_columns(df)
            elif file_type == GDELTFileType.MENTIONS:
                self._convert_mention_numeric_columns(df)
            
            # Save the processed DataFrame
            self._save_dataframe(df, timestamp, file_type, "processed")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing GDELT data: {str(e)}")
            return None

    def _convert_event_numeric_columns(self, df: pd.DataFrame) -> None:
        """Convert numeric columns in event data"""
        numeric_columns = ['GLOBALEVENTID', 'SQLDATE', 'MonthYear', 'Year', 'FractionDate',
                         'IsRootEvent', 'QuadClass', 'GoldsteinScale', 'NumMentions', 
                         'NumSources', 'NumArticles', 'AvgTone']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert geographic coordinates
        geo_lat_cols = ['Actor1Geo_Lat', 'Actor2Geo_Lat', 'ActionGeo_Lat']
        geo_long_cols = ['Actor1Geo_Long', 'Actor2Geo_Long', 'ActionGeo_Long']
        for col in geo_lat_cols + geo_long_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    def _convert_mention_numeric_columns(self, df: pd.DataFrame) -> None:
        """Convert numeric columns in mention data"""
        numeric_columns = ['GlobalEventID', 'EventTimeDate', 'MentionTimeDate', 'MentionType',
                         'SentenceID', 'Actor1CharOffset', 'Actor2CharOffset', 'ActionCharOffset',
                         'InRawText', 'Confidence', 'MentionDocLen', 'MentionDocTone']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    def get_events_with_mentions(self, events_df: pd.DataFrame, 
                               mentions_df: pd.DataFrame,
                               min_confidence: int = 50,
                               timestamp: Optional[str] = None) -> pd.DataFrame:
        """
        Get events that have mentions with high confidence.
        
        Args:
            events_df (pd.DataFrame): Events DataFrame
            mentions_df (pd.DataFrame): Mentions DataFrame
            min_confidence (int): Minimum confidence score for mentions
            timestamp (str, optional): Timestamp for saving the filtered data
            
        Returns:
            pd.DataFrame: Filtered events DataFrame
        """
        # Get event IDs with high confidence mentions
        high_confidence_mentions = mentions_df[mentions_df['Confidence'] >= min_confidence]
        high_confidence_event_ids = high_confidence_mentions['GlobalEventID'].unique()
        
        # Filter events
        filtered_events = events_df[events_df['GLOBALEVENTID'].isin(high_confidence_event_ids)]
        
        # Save the filtered events if timestamp is provided
        if timestamp:
            self._save_dataframe(filtered_events, timestamp, GDELTFileType.EVENTS, 
                               f"high_confidence_{min_confidence}")
        
        return filtered_events

    def get_top_events(self, df: pd.DataFrame, n: int = 10) -> pd.Series:
        """
        Get the most common event types.
        
        Args:
            df (pd.DataFrame): GDELT events DataFrame
            n (int): Number of top events to return
            
        Returns:
            pd.Series: Series containing event counts
        """
        return df['EventCode'].value_counts().head(n)

    def get_top_countries(self, df: pd.DataFrame, n: int = 10) -> pd.Series:
        """
        Get the most common countries in the events.
        
        Args:
            df (pd.DataFrame): GDELT events DataFrame
            n (int): Number of top countries to return
            
        Returns:
            pd.Series: Series containing country counts
        """
        return df['ActionGeo_CountryCode'].value_counts().head(n)

    def get_average_tone_by_country(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate average tone by country.
        
        Args:
            df (pd.DataFrame): GDELT events DataFrame
            
        Returns:
            pd.DataFrame: DataFrame with average tone by country
        """
        return df.groupby('ActionGeo_CountryCode')['AvgTone'].mean().sort_values(ascending=False)

    def get_events_by_quad_class(self, df: pd.DataFrame) -> Dict[QuadClass, pd.DataFrame]:
        """
        Get events grouped by their quad class (Verbal Cooperation, Material Cooperation, etc.)
        
        Args:
            df (pd.DataFrame): GDELT events DataFrame
            
        Returns:
            Dict[QuadClass, pd.DataFrame]: Dictionary mapping quad classes to their events
        """
        return {quad_class: df[df['QuadClass'] == quad_class.value] 
                for quad_class in QuadClass}

    def get_events_by_location(self, df: pd.DataFrame, 
                             country_code: Optional[str] = None,
                             city: Optional[str] = None) -> pd.DataFrame:
        """
        Filter events by location (country or city)
        
        Args:
            df (pd.DataFrame): GDELT events DataFrame
            country_code (str, optional): Two-letter country code
            city (str, optional): City name
            
        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        if country_code:
            return df[
                (df['ActionGeo_CountryCode'] == country_code) |
                (df['Actor1Geo_CountryCode'] == country_code) |
                (df['Actor2Geo_CountryCode'] == country_code)
            ]
        elif city:
            return df[
                (df['ActionGeo_FullName'].str.contains(city, case=False, na=False)) |
                (df['Actor1Geo_FullName'].str.contains(city, case=False, na=False)) |
                (df['Actor2Geo_FullName'].str.contains(city, case=False, na=False))
            ]
        return df

    def get_events_by_actor(self, df: pd.DataFrame, 
                          actor_name: str,
                          actor_type: Optional[str] = None) -> pd.DataFrame:
        """
        Filter events by actor name and optionally actor type
        
        Args:
            df (pd.DataFrame): GDELT events DataFrame
            actor_name (str): Name of the actor to search for
            actor_type (str, optional): Type code of the actor
            
        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        mask = (
            (df['Actor1Name'].str.contains(actor_name, case=False, na=False)) |
            (df['Actor2Name'].str.contains(actor_name, case=False, na=False))
        )
        
        if actor_type:
            mask &= (
                (df['Actor1Type1Code'] == actor_type) |
                (df['Actor1Type2Code'] == actor_type) |
                (df['Actor1Type3Code'] == actor_type) |
                (df['Actor2Type1Code'] == actor_type) |
                (df['Actor2Type2Code'] == actor_type) |
                (df['Actor2Type3Code'] == actor_type)
            )
            
        return df[mask]

# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize GDELT with default data directory
    gdelt = GDELT()
    
    # Example timestamp (using a recent one from your list)
    timestamp = "20250405083000"
    
    # Fetch both events and mentions
    print(f"Fetching GDELT data for timestamp {timestamp}...")
    events_df = gdelt.fetch_data(timestamp, GDELTFileType.EVENTS)
    mentions_df = gdelt.fetch_data(timestamp, GDELTFileType.MENTIONS)
    print(len(events_df))
    print(len(mentions_df))
    if events_df is not None and mentions_df is not None:
        print(f"\nSuccessfully fetched {len(events_df)} events and {len(mentions_df)} mentions")
        
        # Get events with high confidence mentions
        high_confidence_events = gdelt.get_events_with_mentions(
            events_df, mentions_df, min_confidence=50, timestamp=timestamp
        )
        print(f"\nFound {len(high_confidence_events)} events with high confidence mentions")
        
        # Print some basic statistics
        print("\nTop Event Types:")
        print(gdelt.get_top_events(events_df))
        
        print("\nTop Countries:")
        print(gdelt.get_top_countries(events_df))
        
        print("\nAverage Tone by Country:")
        print(gdelt.get_average_tone_by_country(events_df))
        
        # Example of getting events by quad class
        print("\nEvents by Quad Class:")
        for quad_class, events_df in gdelt.get_events_by_quad_class(events_df).items():
            print(f"{quad_class.name}: {len(events_df)} events")
    else:
        print("\nNo data available. You can try:")
        print("1. Using a different timestamp")
        print("2. Checking the GDELT website for data availability")
        print("3. Using the GDELT BigQuery dataset for historical data")
