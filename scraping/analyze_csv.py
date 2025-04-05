import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os

def load_data(file_path):
    """Load the CSV file and return the DataFrame."""
    return pd.read_csv(file_path)

def analyze_country_codes(df):
    """Analyze country codes and return basic statistics."""
    # Get basic statistics
    total_records = len(df)
    null_values = df['CountryCode'].isnull().sum()
    
    # Split multiple country codes and get individual country frequencies
    all_countries = []
    for codes in df['CountryCode'].str.split(','):
        if isinstance(codes, list):
            all_countries.extend([code.strip() for code in codes])
        
    country_freq = Counter(all_countries)
    unique_countries = len(set(all_countries))
    
    return {
        'total_records': total_records,
        'null_values': null_values,
        'unique_countries': unique_countries,
        'country_frequencies': country_freq
    }

def plot_top_countries(country_freq, top_n=20, output_dir='data/statistics'):
    """Create a bar plot of top N countries."""
    plt.figure(figsize=(12, 6))
    countries, frequencies = zip(*country_freq.most_common(top_n))
    
    plt.bar(range(len(countries)), frequencies)
    plt.xticks(range(len(countries)), countries, rotation=45, ha='right')
    plt.title(f'Top {top_n} Countries by Frequency')
    plt.xlabel('Country Code')
    plt.ylabel('Frequency')
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, 'top_countries_distribution.png'))
    plt.close()

def analyze_country_combinations(df, output_dir='data/statistics'):
    """Analyze and save statistics about country combinations."""
    combinations = df['CountryCode'].value_counts()
    
    # Save top combinations to a CSV file
    os.makedirs(output_dir, exist_ok=True)
    combinations.head(50).to_csv(os.path.join(output_dir, 'top_country_combinations.csv'))
    
    return combinations

def main():
    # File paths
    input_file = 'data/gdelt_ggg_aggregated.csv'
    output_dir = 'data/statistics'
    
    # Load data
    print("Loading data...")
    df = load_data(input_file)
    
    # Analyze country codes
    print("\nAnalyzing country codes...")
    stats = analyze_country_codes(df)
    
    # Print basic statistics
    print("\nBasic Statistics:")
    print(f"Total records: {stats['total_records']}")
    print(f"Null values: {stats['null_values']}")
    print(f"Unique individual countries: {stats['unique_countries']}")
    
    # Print top 10 countries
    print("\nTop 10 Individual Countries:")
    for country, count in stats['country_frequencies'].most_common(10):
        print(f"{country}: {count}")
    
    # Create visualizations
    print("\nCreating visualizations...")
    plot_top_countries(stats['country_frequencies'])
    
    # Analyze country combinations
    print("\nAnalyzing country combinations...")
    combinations = analyze_country_combinations(df)
    
    print("\nTop 10 Country Combinations:")
    for combo, count in combinations.head(10).items():
        print(f"{combo}: {count}")
    
    print(f"\nResults have been saved to {output_dir}/")

if __name__ == "__main__":
    main()
