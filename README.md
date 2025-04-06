# EBL - European Builders League
As part of the hackathon of EBL in Delft, we built this tool to help users understand geographical bias and sentiment differences in news reporting across countries. The system collects and analyzes news articles from various sources globally and provides insights on how different countries report on specific topics.

Key features:
- Multi-language topic search with automatic translation
- Sentiment analysis of news articles
- Country-specific sentiment scoring
- Visualization of sentiment on maps
- Retrieval of supporting articles that represent varying viewpoints

## System Architecture

The system consists of several components:

### Backend Services
- **API Server**: Flask-based REST API that handles user queries and returns country-based sentiment analysis
- **Query Expansion**: Enhances user queries using semantic models for better document retrieval
- **Document Retrieval**: BM25-based document search with multilingual support
- **Document Rating**: LLM-based sentiment analysis using Gemma 4B
- **Named Entity Recognition**: Identifies if topics are named entities to improve search accuracy

### Data Collection
- **Web Scraping**: Tools for collecting news articles from various sources globally
- **GDELT Integration**: Integration with the GDELT Project for global news data
- **Data Processing**: Cleaning, filtering, and preparing articles for search and analysis


