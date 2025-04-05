import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import json
from country_codes import get_country_name

class GDELTAnalysis:
    """
    A class to analyze GDELT data and generate statistics.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the analysis with data directory.
        
        Args:
            data_dir (str): Directory containing GDELT data
        """
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(__name__)
        
        # Set up directories
        self.events_dir = self.data_dir / "events"
        self.mentions_dir = self.data_dir / "mentions"
        self.processed_dir = self.data_dir / "processed"
        self.stats_dir = self.data_dir / "statistics"
        self.stats_dir.mkdir(exist_ok=True)
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_theme()

    def _get_country_name(self, code: str) -> str:
        """
        Get country name from GDELT country code.
        
        Args:
            code (str): GDELT country code
            
        Returns:
            str: Country name or original code if not found
        """
        return get_country_name(code)

    def load_latest_data(self) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Load the most recent events and mentions data.
        
        Returns:
            Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]: Events and mentions DataFrames
        """
        try:
            # Get latest event file
            event_files = list(self.events_dir.glob("*.export.CSV"))
            if not event_files:
                self.logger.error("No event files found")
                return None, None
                
            latest_event = max(event_files, key=lambda x: x.stat().st_mtime)
            events_df = pd.read_csv(latest_event, sep='\t')
            
            # Get latest mentions file
            mention_files = list(self.mentions_dir.glob("*.mentions.CSV"))
            if not mention_files:
                self.logger.error("No mention files found")
                return events_df, None
                
            latest_mention = max(mention_files, key=lambda x: x.stat().st_mtime)
            mentions_df = pd.read_csv(latest_mention, sep='\t')
            
            return events_df, mentions_df
            
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            return None, None

    def generate_basic_statistics(self, events_df: pd.DataFrame, 
                                mentions_df: Optional[pd.DataFrame] = None) -> Dict:
        """
        Generate basic statistics about the dataset.
        
        Args:
            events_df (pd.DataFrame): Events DataFrame
            mentions_df (Optional[pd.DataFrame]): Mentions DataFrame
            
        Returns:
            Dict: Dictionary containing statistics
        """
        try:
            # Convert SQLDATE to numeric if it's not already
            if 'SQLDATE' in events_df.columns:
                events_df['SQLDATE'] = pd.to_numeric(events_df['SQLDATE'], errors='coerce')
            
            # Get all country counts and convert codes to names
            country_counts = events_df['ActionGeo_CountryCode'].value_counts()
            country_stats = {
                f"{self._get_country_name(code)} ({code})": count 
                for code, count in country_counts.items()
            }
            
            # Get top 10 countries separately for display
            top_countries = dict(list(country_stats.items())[:10])
            
            stats = {
                "total_events": len(events_df),
                "date_range": {
                    "start": events_df['SQLDATE'].min() if not pd.isna(events_df['SQLDATE'].min()) else "N/A",
                    "end": events_df['SQLDATE'].max() if not pd.isna(events_df['SQLDATE'].max()) else "N/A"
                },
                "top_countries": top_countries,
                "all_countries": country_stats,  # Include all country counts
                "event_types": {
                    "verbal_cooperation": len(events_df[events_df['QuadClass'] == 1]),
                    "material_cooperation": len(events_df[events_df['QuadClass'] == 2]),
                    "verbal_conflict": len(events_df[events_df['QuadClass'] == 3]),
                    "material_conflict": len(events_df[events_df['QuadClass'] == 4])
                }
            }
            
            # Add tone statistics if AvgTone column exists and is numeric
            if 'AvgTone' in events_df.columns:
                events_df['AvgTone'] = pd.to_numeric(events_df['AvgTone'], errors='coerce')
                stats["tone_statistics"] = {
                    "mean": events_df['AvgTone'].mean(),
                    "median": events_df['AvgTone'].median(),
                    "std": events_df['AvgTone'].std(),
                    "min": events_df['AvgTone'].min(),
                    "max": events_df['AvgTone'].max()
                }
            
            if mentions_df is not None:
                # Convert Confidence to numeric if it exists
                if 'Confidence' in mentions_df.columns:
                    mentions_df['Confidence'] = pd.to_numeric(mentions_df['Confidence'], errors='coerce')
                
                # Get all source distributions
                all_sources = mentions_df['MentionSourceName'].value_counts().to_dict() if 'MentionSourceName' in mentions_df.columns else {}
                top_sources = dict(list(all_sources.items())[:10])  # Get top 10 for display
                
                stats["mentions"] = {
                    "total_mentions": len(mentions_df),
                    "avg_confidence": mentions_df['Confidence'].mean() if 'Confidence' in mentions_df.columns else None,
                    "high_confidence_mentions": len(mentions_df[mentions_df['Confidence'] >= 75]) if 'Confidence' in mentions_df.columns else None,
                    "top_sources": top_sources,  # Top 10 sources
                    "all_sources": all_sources  # All sources
                }
                
            return stats
            
        except Exception as e:
            self.logger.error(f"Error generating statistics: {str(e)}")
            return {
                "error": f"Failed to generate statistics: {str(e)}",
                "total_events": len(events_df) if events_df is not None else 0
            }

    def plot_event_distribution(self, events_df: pd.DataFrame, save_path: Optional[str] = None):
        """
        Plot distribution of events by quad class.
        
        Args:
            events_df (pd.DataFrame): Events DataFrame
            save_path (Optional[str]): Path to save the plot
        """
        plt.figure(figsize=(10, 6))
        
        quad_classes = {
            1: "Verbal Cooperation",
            2: "Material Cooperation",
            3: "Verbal Conflict",
            4: "Material Conflict"
        }
        
        events_df['QuadClass'].value_counts().plot(kind='bar')
        plt.title('Distribution of Events by Quad Class')
        plt.xlabel('Quad Class')
        plt.ylabel('Number of Events')
        plt.xticks(range(4), [quad_classes[i] for i in range(1, 5)], rotation=45)
        
        if save_path:
            plt.savefig(save_path)
        plt.close()

    def plot_tone_distribution(self, events_df: pd.DataFrame, save_path: Optional[str] = None):
        """
        Plot distribution of event tones.
        
        Args:
            events_df (pd.DataFrame): Events DataFrame
            save_path (Optional[str]): Path to save the plot
        """
        plt.figure(figsize=(10, 6))
        sns.histplot(data=events_df, x='AvgTone', bins=50)
        plt.title('Distribution of Event Tones')
        plt.xlabel('Average Tone')
        plt.ylabel('Count')
        
        if save_path:
            plt.savefig(save_path)
        plt.close()

    def plot_top_countries(self, events_df: pd.DataFrame, save_path: Optional[str] = None):
        """
        Plot top countries by event count.
        
        Args:
            events_df (pd.DataFrame): Events DataFrame
            save_path (Optional[str]): Path to save the plot
        """
        plt.figure(figsize=(12, 6))
        top_countries = events_df['ActionGeo_CountryCode'].value_counts().head(10)
        
        # Convert country codes to names for plotting
        country_names = [self._get_country_name(code) for code in top_countries.index]
        
        plt.bar(country_names, top_countries.values)
        plt.title('Top 10 Countries by Event Count')
        plt.xlabel('Country')
        plt.ylabel('Number of Events')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        plt.close()

    def generate_report(self, timestamp: Optional[str] = None) -> Dict:
        """
        Generate a comprehensive analysis report.
        
        Args:
            timestamp (Optional[str]): Specific timestamp to analyze
            
        Returns:
            Dict: Dictionary containing the analysis report
        """
        # Load data
        events_df, mentions_df = self.load_latest_data()
        if events_df is None:
            return {"error": "No data available"}
            
        # Generate statistics
        stats = self.generate_basic_statistics(events_df, mentions_df)
        
        # Generate plots
        timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        plot_paths = {
            "event_distribution": str(self.stats_dir / f"{timestamp}_event_distribution.png"),
            "tone_distribution": str(self.stats_dir / f"{timestamp}_tone_distribution.png"),
            "top_countries": str(self.stats_dir / f"{timestamp}_top_countries.png")
        }
        
        self.plot_event_distribution(events_df, plot_paths["event_distribution"])
        self.plot_tone_distribution(events_df, plot_paths["tone_distribution"])
        self.plot_top_countries(events_df, plot_paths["top_countries"])
        
        # Save statistics to JSON
        stats_path = self.stats_dir / f"{timestamp}_statistics.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
            
        return {
            "statistics": stats,
            "plots": plot_paths,
            "statistics_file": str(stats_path)
        }

# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize analysis
    analysis = GDELTAnalysis()
    
    # Generate report
    report = analysis.generate_report()
    
    # Print summary
    if "error" in report:
        print(f"Error: {report['error']}")
    else:
        stats = report["statistics"]
        print("\nGDELT Dataset Analysis Summary:")
        print(f"Total Events: {stats['total_events']}")
        print(f"Date Range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        print("\nTop 5 Countries:")
        for country, count in list(stats['top_countries'].items())[:5]:
            print(f"  {country}: {count}")
        print("\nEvent Types:")
        for event_type, count in stats['event_types'].items():
            print(f"  {event_type}: {count}")
        print("\nTone Statistics:")
        for stat, value in stats['tone_statistics'].items():
            print(f"  {stat}: {value:.2f}")
            
        if "mentions" in stats:
            print("\nMentions Statistics:")
            print(f"  Total Mentions: {stats['mentions']['total_mentions']}")
            print(f"  Average Confidence: {stats['mentions']['avg_confidence']:.2f}")
            print(f"  High Confidence Mentions: {stats['mentions']['high_confidence_mentions']}")
            
        print(f"\nAnalysis files saved in: {report['statistics_file']}")
        print("Plots saved in:")
        for plot_name, plot_path in report["plots"].items():
            print(f"  {plot_name}: {plot_path}") 