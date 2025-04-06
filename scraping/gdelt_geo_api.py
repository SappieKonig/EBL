import requests
import json
import logging
import urllib.parse
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import time
import os
import pandas as pd
import geojson

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GDELTGeoAPI:
    """
    A class to interact with the GDELT GEO 2.0 API for geographic analysis of news.
    
    The GDELT GEO 2.0 API allows for querying and mapping of global news coverage
    based on geographic location, keywords, and various other parameters.
    """
    
    BASE_URL = "https://api.gdeltproject.org/api/v2/geo/geo"
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the GDELT GEO API client.
        
        Args:
            data_dir (str): Directory to store API response data
        """
        self.data_dir = Path(data_dir)
        self.geo_dir = self.data_dir / "geo"
        self.geo_dir.mkdir(exist_ok=True)
        
    def query(self, query: str, mode: str = "PointData", 
              output_format: str = "GeoJSON", timespan: str = "1d",
              geores: int = 0, maxpoints: int = 1000, 
              save_result: bool = True, filename: Optional[str] = None,
              sortby: Optional[str] = None) -> Dict:
        """
        Query the GDELT GEO API with specified parameters.
        
        Args:
            query (str): Search query (keywords, phrases, or GDELT operators)
            mode (str): Map mode (PointData, Country, ADM1, SourceCountry, etc.)
            output_format (str): Output format (GeoJSON, HTML, CSV, etc.)
            timespan (str): Time range to search (15m, 1h, 1d, etc. up to 7d)
            geores (int): Geographic resolution (0=all, 1=no countries, 2=only cities)
            maxpoints (int): Maximum number of points to return
            save_result (bool): Whether to save the result to a file
            filename (Optional[str]): Custom filename for saving results
            sortby (Optional[str]): Sort results (Date, ToneDesc, ToneAsc)
            
        Returns:
            Dict: The API response as a dictionary
        """
        # Build query parameters
        params = {
            "query": query,
            "mode": mode,
            "format": output_format,
            "timespan": timespan,
            "geores": geores,
            "maxpoints": maxpoints
        }
        
        # Add optional sortby parameter if provided
        if sortby:
            params["sortby"] = sortby
        
        # Build URL with encoded parameters
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            logger.info(f"Querying GDELT GEO API: {url}")
            response = requests.get(url)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse response based on format
            if output_format.lower() in ["geojson", "imagegeojson"]:
                result = response.json()
            elif output_format.lower() in ["csv", "imagecsv"]:
                # Save CSV to a temp file and then read it
                temp_file = self.geo_dir / f"temp_{int(time.time())}.csv"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                result = pd.read_csv(temp_file).to_dict(orient='records')
                os.remove(temp_file)
            else:
                # For HTML and other formats, just return the text
                result = {"raw_content": response.text}
            
            # Save the result if requested
            if save_result:
                self._save_result(result, query, mode, output_format, filename)
                
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying GDELT GEO API: {str(e)}")
            return {"error": str(e)}
    
    def keyword_map(self, keyword: str, mode: str = "Country", 
                   timespan: str = "1d", save_result: bool = True) -> Dict:
        """
        Create a map of locations related to a keyword or phrase.
        
        Args:
            keyword (str): Keyword or phrase to search for
            mode (str): Map mode (PointData, Country, ADM1, SourceCountry)
            timespan (str): Time range to search
            save_result (bool): Whether to save the result
            
        Returns:
            Dict: GeoJSON result containing locations
        """
        return self.query(
            query=keyword,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan,
            save_result=save_result
        )
    
    def coverage_by_location(self, location: str, 
                            timespan: str = "1d") -> Dict:
        """
        Find all news coverage mentioning a specific location.
        
        Args:
            location (str): Location name or code to search for
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result containing articles
        """
        # Use the location: operator to search for the location
        query = f'location:"{location}"'
        
        return self.query(
            query=query,
            mode="PointData",
            output_format="GeoJSON",
            timespan=timespan,
            maxpoints=1000
        )
    
    def coverage_by_source_country(self, country: str, 
                                  keyword: Optional[str] = None,
                                  timespan: str = "1d") -> Dict:
        """
        Find news coverage from a specific country's media.
        
        Args:
            country (str): Country name or code
            keyword (Optional[str]): Optional keyword to narrow results
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result containing articles
        """
        if keyword:
            query = f'sourcecountry:{country} {keyword}'
        else:
            query = f'sourcecountry:{country}'
            
        return self.query(
            query=query,
            mode="SourceCountry",
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def image_search(self, image_query: str, mode: str = "ImagePointData", 
                    timespan: str = "1d") -> Dict:
        """
        Search for images based on content, captions, or metadata.
        
        Args:
            image_query (str): Image search query
            mode (str): Map mode (ImagePointData, ImageCountry, etc.)
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result containing images
        """
        return self.query(
            query=image_query,
            mode=mode,
            output_format="ImageGeoJSON",
            timespan=timespan
        )
    
    def find_nearby_coverage(self, lat: float, lon: float, 
                            radius: int = 100, keyword: Optional[str] = None, 
                            timespan: str = "1d") -> Dict:
        """
        Find news coverage near a specific location.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            radius (int): Radius in miles (or append 'km' for kilometers)
            keyword (Optional[str]): Optional keyword to narrow results
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result containing nearby articles
        """
        # Construct the near: operator
        near_query = f'near:{lat},{lon},{radius}'
        
        if keyword:
            query = f'{near_query} {keyword}'
        else:
            query = near_query
            
        return self.query(
            query=query,
            mode="PointData",
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def tone_map(self, min_tone: Optional[float] = None, 
                max_tone: Optional[float] = None,
                keyword: Optional[str] = None,
                mode: str = "Country", timespan: str = "1d") -> Dict:
        """
        Create a map showing news tone (sentiment) by location.
        
        Args:
            min_tone (Optional[float]): Minimum tone score (negative for negative sentiment)
            max_tone (Optional[float]): Maximum tone score (positive for positive sentiment)
            keyword (Optional[str]): Optional keyword to narrow results
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result showing tone by location
        """
        # Construct tone filters
        tone_query = ""
        if min_tone is not None:
            tone_query += f" tone>{min_tone}"
        if max_tone is not None:
            tone_query += f" tone<{max_tone}"
            
        if keyword:
            query = f'{keyword}{tone_query}'
        else:
            query = tone_query.strip()
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def language_coverage(self, language: str, 
                         keyword: Optional[str] = None,
                         mode: str = "PointData", timespan: str = "1d") -> Dict:
        """
        Map coverage in a specific language.
        
        Args:
            language (str): Language name or code
            keyword (Optional[str]): Optional keyword to narrow results
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result showing coverage in the language
        """
        if keyword:
            query = f'sourcelang:{language} {keyword}'
        else:
            query = f'sourcelang:{language}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def _save_result(self, result: Any, query: str, mode: str, 
                   output_format: str, filename: Optional[str] = None) -> str:
        """
        Save API results to a file.
        
        Args:
            result (Any): API response
            query (str): Original query
            mode (str): Map mode used
            output_format (str): Output format
            filename (Optional[str]): Custom filename
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Generate filename if not provided
            if not filename:
                # Sanitize query for filename
                sanitized_query = "".join(c if c.isalnum() else "_" for c in query)[:50]
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{sanitized_query}_{mode}_{timestamp}"
            
            # Determine file extension
            if output_format.lower() in ["geojson", "imagegeojson"]:
                file_path = self.geo_dir / f"{filename}.geojson"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
            elif output_format.lower() in ["csv", "imagecsv"]:
                file_path = self.geo_dir / f"{filename}.csv"
                pd.DataFrame(result).to_csv(file_path, index=False)
            else:
                file_path = self.geo_dir / f"{filename}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(result.get("raw_content", "")))
                    
            logger.info(f"Saved GDELT GEO API result to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving GDELT GEO API result: {str(e)}")
            return ""
    
    def get_article_context(self, geo_result: Dict, include_content: bool = False) -> List[Dict]:
        """
        Extract article context information from a GDELT GEO API result.
        
        This method extracts valuable context information from GEO API results,
        including article URLs, titles, publication dates, tones, locations,
        and optionally article content.
        
        Args:
            geo_result (Dict): GeoJSON result from any GDELT GEO API query
            include_content (bool): Whether to include article content if available
            
        Returns:
            List[Dict]: List of articles with context information
        """
        articles = []
        
        try:
            if "features" not in geo_result:
                logger.error("Invalid GeoJSON format: no features found")
                return []
                
            for feature in geo_result["features"]:
                props = feature.get("properties", {})
                
                # Skip features without article information
                if not props:
                    continue
                
                # Handle different feature types based on mode
                if "articles" in props:
                    # PointData mode
                    for article in props.get("articles", []):
                        articles.append(self._extract_article_info(article, feature, include_content))
                elif "url" in props:
                    # Single article feature
                    articles.append(self._extract_article_info(props, feature, include_content))
                elif "name" in props and "count" in props:
                    # Country or ADM1 mode - aggregate information
                    location_info = {
                        "location_name": props.get("name", ""),
                        "mention_count": props.get("count", 0),
                        "normalized_score": props.get("normalized", 0),
                        "geometry": feature.get("geometry", {})
                    }
                    articles.append(location_info)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error extracting article context: {str(e)}")
            return []
    
    def _extract_article_info(self, article_props: Dict, feature: Dict, include_content: bool) -> Dict:
        """
        Extract information from a single article.
        
        Args:
            article_props (Dict): Article properties
            feature (Dict): GeoJSON feature containing the article
            include_content (bool): Whether to include article content
            
        Returns:
            Dict: Article with context information
        """
        article_info = {
            "url": article_props.get("url", ""),
            "title": article_props.get("title", ""),
            "seendate": article_props.get("seendate", ""),
            "domain": article_props.get("domain", ""),
            "language": article_props.get("language", ""),
            "tone": article_props.get("tone", 0),
            "location": {
                "name": article_props.get("name", ""),
                "lat": article_props.get("lat", 0),
                "lon": article_props.get("long", 0),
                "country_code": article_props.get("countrycode", ""),
                "adm1_code": article_props.get("adm1code", "")
            },
            "geometry": feature.get("geometry", {})
        }
        
        # Add image information if available
        if "socialimage" in article_props:
            article_info["image"] = {
                "url": article_props.get("socialimage", ""),
                "tags": article_props.get("imagetags", []),
                "web_tags": article_props.get("imagewebtags", []),
                "web_count": article_props.get("imagewebcount", 0),
                "face_tone": article_props.get("imagefacetone", 0),
                "num_faces": article_props.get("imagenumfaces", 0)
            }
        
        # Add article content if available and requested
        if include_content and "content" in article_props:
            article_info["content"] = article_props.get("content", "")
        
        # Add theme information if available
        if "themes" in article_props:
            article_info["themes"] = article_props.get("themes", [])
        
        return article_info
            
    def convert_to_features(self, geo_result: Dict) -> List[Dict]:
        """
        Convert GeoJSON result to a list of features with properties.
        
        Args:
            geo_result (Dict): GeoJSON result from the API
            
        Returns:
            List[Dict]: List of features with extracted properties
        """
        try:
            features = []
            
            if "features" not in geo_result:
                logger.error("Invalid GeoJSON format: no features found")
                return []
                
            for feature in geo_result["features"]:
                # Extract properties
                props = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                
                features.append({
                    "type": feature.get("type", ""),
                    "geometry": geometry,
                    "properties": props
                })
                
            return features
            
        except Exception as e:
            logger.error(f"Error converting GeoJSON to features: {str(e)}")
            return []
    
    def query_article_context(self, query: str, 
                            mode: str = "PointData", 
                            timespan: str = "1d",
                            sortby: Optional[str] = None,
                            include_content: bool = False) -> List[Dict]:
        """
        Query the GDELT GEO API and extract article context directly.
        
        This method combines querying and context extraction in one step.
        
        Args:
            query (str): Search query (supports all GDELT GEO API operators)
            mode (str): Map mode (PointData, Country, etc.)
            timespan (str): Time range to search
            sortby (Optional[str]): Sort results (Date, ToneDesc, ToneAsc)
            include_content (bool): Whether to include article content if available
            
        Returns:
            List[Dict]: List of articles with context information
        """
        # Build additional parameters if needed
        params = {}
        if sortby:
            params["sortby"] = sortby
            
        # Query the API
        result = self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan,
            **params
        )
        
        # Extract article context from results
        return self.get_article_context(result, include_content)
    
    def search_by_domain(self, domain: str, 
                       additional_query: Optional[str] = None,
                       mode: str = "PointData",
                       timespan: str = "1d") -> Dict:
        """
        Find all coverage from a specific domain/news outlet.
        
        Args:
            domain (str): Domain name (e.g., cnn.com)
            additional_query (Optional[str]): Additional search terms
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles from the domain
        """
        query = f'domain:{domain}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def search_by_exact_domain(self, domain: str, 
                             additional_query: Optional[str] = None,
                             mode: str = "PointData",
                             timespan: str = "1d") -> Dict:
        """
        Find all coverage from a specific domain with exact match.
        
        This uses the domainis: operator for exact domain matching.
        
        Args:
            domain (str): Domain name (e.g., un.org)
            additional_query (Optional[str]): Additional search terms
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles from the domain
        """
        query = f'domainis:{domain}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def search_by_theme(self, theme: str, 
                       additional_query: Optional[str] = None,
                       mode: str = "PointData",
                       timespan: str = "1d") -> Dict:
        """
        Find all coverage related to a specific GDELT theme.
        
        Args:
            theme (str): GDELT theme (e.g., TERROR, PROTEST, etc.)
            additional_query (Optional[str]): Additional search terms
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles related to the theme
        """
        query = f'theme:{theme}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def search_by_tone(self, tone_operator: str, 
                      tone_value: float,
                      additional_query: Optional[str] = None,
                      mode: str = "PointData",
                      timespan: str = "1d") -> Dict:
        """
        Find all coverage with a specific emotional tone.
        
        Args:
            tone_operator (str): Operator (>, <, =)
            tone_value (float): Tone threshold value
            additional_query (Optional[str]): Additional search terms
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles matching the tone
        """
        query = f'tone{tone_operator}{tone_value}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def search_by_absolute_tone(self, tone_operator: str, 
                               tone_value: float,
                               additional_query: Optional[str] = None,
                               mode: str = "PointData",
                               timespan: str = "1d") -> Dict:
        """
        Find all coverage with a specific absolute emotional tone magnitude.
        
        Args:
            tone_operator (str): Operator (>, <, =)
            tone_value (float): Absolute tone threshold value
            additional_query (Optional[str]): Additional search terms
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles matching the absolute tone
        """
        query = f'toneabs{tone_operator}{tone_value}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def search_images_by_tag(self, tag: str,
                           additional_query: Optional[str] = None,
                           mode: str = "ImagePointData",
                           timespan: str = "1d") -> Dict:
        """
        Find all images tagged with a specific object or scene.
        
        Args:
            tag (str): Image tag (e.g., "protest", "flood", etc.)
            additional_query (Optional[str]): Additional search terms
            mode (str): Image map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with images matching the tag
        """
        query = f'imagetag:"{tag}"'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="ImageGeoJSON",
            timespan=timespan
        )
    
    def search_images_by_web_tag(self, tag: str,
                               additional_query: Optional[str] = None,
                               mode: str = "ImagePointData",
                               timespan: str = "1d") -> Dict:
        """
        Find all images tagged with a specific web tag from across the internet.
        
        Args:
            tag (str): Web tag (e.g., "protest", "flood", etc.)
            additional_query (Optional[str]): Additional search terms
            mode (str): Image map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with images matching the web tag
        """
        query = f'imagewebtag:"{tag}"'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="ImageGeoJSON",
            timespan=timespan
        )
    
    def search_images_by_face_tone(self, tone_operator: str,
                                 tone_value: float,
                                 additional_query: Optional[str] = None,
                                 mode: str = "ImagePointData",
                                 timespan: str = "1d") -> Dict:
        """
        Find images with people showing specific facial emotions.
        
        Args:
            tone_operator (str): Operator (>, <, =)
            tone_value (float): Face tone threshold value
            additional_query (Optional[str]): Additional search terms
            mode (str): Image map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with images matching the facial tone
        """
        query = f'imagefacetone{tone_operator}{tone_value}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="ImageGeoJSON",
            timespan=timespan
        )
    
    def search_images_by_num_faces(self, num_operator: str,
                                 num_faces: int,
                                 additional_query: Optional[str] = None,
                                 mode: str = "ImagePointData",
                                 timespan: str = "1d") -> Dict:
        """
        Find images with a specific number of human faces.
        
        Args:
            num_operator (str): Operator (>, <, =)
            num_faces (int): Number of faces threshold
            additional_query (Optional[str]): Additional search terms
            mode (str): Image map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with images matching the face count
        """
        query = f'imagenumfaces{num_operator}{num_faces}'
        
        if additional_query:
            query = f'{query} {additional_query}'
            
        return self.query(
            query=query,
            mode=mode,
            output_format="ImageGeoJSON",
            timespan=timespan
        )
    
    def build_complex_query(self, query_parts: List[str], 
                          exclude_parts: Optional[List[str]] = None) -> str:
        """
        Build a complex query with multiple parts and exclusions.
        
        This utility helps construct queries with multiple operators and exclusions.
        
        Args:
            query_parts (List[str]): List of query parts to include
            exclude_parts (Optional[List[str]]): List of query parts to exclude
            
        Returns:
            str: Combined query string
        """
        # Join the main query parts with spaces
        query = " ".join(query_parts)
        
        # Add exclusion parts if provided
        if exclude_parts:
            exclusions = " ".join([f"-{part}" for part in exclude_parts])
            query = f"{query} {exclusions}"
            
        return query
    
    def build_or_query(self, or_parts: List[str]) -> str:
        """
        Build a query with OR logic between parts.
        
        Args:
            or_parts (List[str]): List of query parts to OR together
            
        Returns:
            str: OR query string
        """
        if not or_parts:
            return ""
            
        # Join the OR parts inside parentheses
        return f"({' OR '.join(or_parts)})"
    
    def search_article_themes(self, themes: List[str], 
                            location: Optional[str] = None,
                            exclude_themes: Optional[List[str]] = None,
                            mode: str = "PointData",
                            timespan: str = "1d") -> Dict:
        """
        Search for articles with multiple themes, optionally at a specific location.
        
        Args:
            themes (List[str]): List of GDELT themes to search for
            location (Optional[str]): Optional location to filter by
            exclude_themes (Optional[List[str]]): Themes to exclude
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles matching themes
        """
        # Build theme queries
        theme_queries = [f'theme:{theme}' for theme in themes]
        
        # Build OR query for themes
        theme_query = self.build_or_query(theme_queries)
        
        # Add location if provided
        if location:
            location_query = f'location:"{location}"'
            query = f"{theme_query} {location_query}"
        else:
            query = theme_query
            
        # Add exclusions if provided
        if exclude_themes:
            exclude_queries = [f'theme:{theme}' for theme in exclude_themes]
            exclusions = " ".join([f"-{part}" for part in exclude_queries])
            query = f"{query} {exclusions}"
            
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def search_complex_image_query(self, 
                                 image_tags: Optional[List[str]] = None,
                                 web_tags: Optional[List[str]] = None,
                                 min_faces: Optional[int] = None,
                                 max_faces: Optional[int] = None,
                                 min_face_tone: Optional[float] = None,
                                 max_face_tone: Optional[float] = None,
                                 location: Optional[str] = None,
                                 mode: str = "ImagePointData",
                                 timespan: str = "1d") -> Dict:
        """
        Perform a complex image search with multiple criteria.
        
        Args:
            image_tags (Optional[List[str]]): Image tags to search for
            web_tags (Optional[List[str]]): Web tags to search for
            min_faces (Optional[int]): Minimum number of faces
            max_faces (Optional[int]): Maximum number of faces
            min_face_tone (Optional[float]): Minimum face emotion tone
            max_face_tone (Optional[float]): Maximum face emotion tone
            location (Optional[str]): Location to filter by
            mode (str): Image map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with images matching criteria
        """
        query_parts = []
        
        # Add image tags
        if image_tags:
            image_tag_queries = [f'imagetag:"{tag}"' for tag in image_tags]
            if len(image_tag_queries) > 1:
                query_parts.append(self.build_or_query(image_tag_queries))
            else:
                query_parts.append(image_tag_queries[0])
                
        # Add web tags
        if web_tags:
            web_tag_queries = [f'imagewebtag:"{tag}"' for tag in web_tags]
            if len(web_tag_queries) > 1:
                query_parts.append(self.build_or_query(web_tag_queries))
            else:
                query_parts.append(web_tag_queries[0])
                
        # Add face count constraints
        if min_faces is not None:
            query_parts.append(f'imagenumfaces>{min_faces}')
        if max_faces is not None:
            query_parts.append(f'imagenumfaces<{max_faces}')
            
        # Add face tone constraints
        if min_face_tone is not None:
            query_parts.append(f'imagefacetone>{min_face_tone}')
        if max_face_tone is not None:
            query_parts.append(f'imagefacetone<{max_face_tone}')
            
        # Add location if provided
        if location:
            query_parts.append(f'location:"{location}"')
            
        # Build final query
        query = " ".join(query_parts)
        
        return self.query(
            query=query,
            mode=mode,
            output_format="ImageGeoJSON",
            timespan=timespan
        )
    
    def search_multi_country_topic(self, topic: str,
                                 countries: List[str],
                                 source_countries: Optional[List[str]] = None,
                                 language: Optional[str] = None,
                                 mode: str = "PointData",
                                 timespan: str = "1d") -> Dict:
        """
        Search for a topic across multiple countries with source filtering.
        
        This allows analysis of how a topic is covered in different countries
        or how specific countries' media cover a topic across multiple regions.
        
        Args:
            topic (str): The topic to search for
            countries (List[str]): List of countries to include in search
            source_countries (Optional[List[str]]): Countries whose media to search
            language (Optional[str]): Language to filter by
            mode (str): Map mode
            timespan (str): Time range to search
            
        Returns:
            Dict: GeoJSON result with articles matching criteria
        """
        query_parts = [topic]
        
        # Add country location constraints
        country_queries = []
        for country in countries:
            # Handle country codes or names
            if len(country) == 2:
                country_queries.append(f'locationcc:{country}')
            else:
                # For full country names
                country_name = country.replace(" ", "").lower()
                country_queries.append(f'locationcc:{country_name}')
                
        # Add OR query for countries
        query_parts.append(self.build_or_query(country_queries))
        
        # Add source country constraints if provided
        if source_countries:
            source_queries = []
            for country in source_countries:
                # Handle country codes or names
                if len(country) == 2:
                    source_queries.append(f'sourcecountry:{country}')
                else:
                    # For full country names
                    country_name = country.replace(" ", "").lower()
                    source_queries.append(f'sourcecountry:{country_name}')
                    
            # Add OR query for source countries
            query_parts.append(self.build_or_query(source_queries))
            
        # Add language constraint if provided
        if language:
            query_parts.append(f'sourcelang:{language}')
            
        # Build final query
        query = " ".join(query_parts)
        
        return self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
    
    def get_context_aware_analysis(self, query: str, 
                                 radius_km: int = 100,
                                 mode: str = "PointData",
                                 timespan: str = "7d",
                                 include_content: bool = True) -> Dict:
        """
        Perform a context-aware analysis of news coverage for a topic.
        
        This method returns not just articles but a comprehensive analysis
        including:
        - Articles matching the query
        - Extracted locations and context
        - Tone/sentiment analysis
        - Geographic distribution
        
        Args:
            query (str): Search query
            radius_km (int): Radius in km for nearby coverage
            mode (str): Map mode
            timespan (str): Time range to search
            include_content (bool): Whether to include article content
            
        Returns:
            Dict: Comprehensive analysis results
        """
        # Query articles
        result = self.query(
            query=query,
            mode=mode,
            output_format="GeoJSON",
            timespan=timespan
        )
        
        # Extract article contexts
        article_contexts = self.get_article_context(result, include_content)
        
        # Get locations mentioned
        locations = set()
        for article in article_contexts:
            if isinstance(article, dict) and "location" in article:
                location_name = article.get("location", {}).get("name", "")
                if location_name:
                    locations.add(location_name)
        
        # Calculate tone statistics
        tones = [article.get("tone", 0) for article in article_contexts 
                if isinstance(article, dict) and "tone" in article]
        
        avg_tone = sum(tones) / len(tones) if tones else 0
        min_tone = min(tones) if tones else 0
        max_tone = max(tones) if tones else 0
        
        # For each significant location, get nearby coverage
        nearby_coverage = {}
        for location in list(locations)[:5]:  # Limit to 5 locations to avoid too many API calls
            # Try to get lat/lon from an article mentioning this location
            loc_articles = [a for a in article_contexts 
                          if isinstance(a, dict) and 
                          a.get("location", {}).get("name", "") == location]
            
            if loc_articles:
                lat = loc_articles[0].get("location", {}).get("lat", 0)
                lon = loc_articles[0].get("location", {}).get("lon", 0)
                
                if lat and lon:
                    # Get nearby coverage
                    nearby = self.find_nearby_coverage(
                        lat=lat, 
                        lon=lon, 
                        radius=f"{radius_km}km"
                    )
                    nearby_contexts = self.get_article_context(nearby)
                    nearby_coverage[location] = nearby_contexts
        
        # Return comprehensive analysis
        return {
            "query": query,
            "timespan": timespan,
            "articles": article_contexts,
            "locations": list(locations),
            "tone_analysis": {
                "average": avg_tone,
                "minimum": min_tone,
                "maximum": max_tone
            },
            "nearby_coverage": nearby_coverage
        }
    
    def get_full_article_context(self, article_url: str) -> Dict:
        """
        Get full context information for a specific article by URL.
        
        This method searches for a specific article by URL and retrieves
        all available context information about it, including:
        - Content details
        - Geographic context
        - Source information
        - Tone analysis
        - Themes
        - Related imagery
        
        Args:
            article_url (str): URL of the article to analyze
            
        Returns:
            Dict: Full article context information
        """
        # Search for the exact article by domain and URL pattern
        domain = self._extract_domain(article_url)
        
        # Create a query that will find this specific article
        # Using the domain and a unique part of the URL
        url_parts = article_url.split('/')
        url_fragment = url_parts[-1] if len(url_parts) > 3 else ""
        
        query = f'domain:{domain}'
        if url_fragment:
            # Add URL fragment if available, but be careful with special characters
            # that might need to be escaped in the GDELT query
            clean_fragment = url_fragment.split('?')[0]  # Remove query parameters
            clean_fragment = clean_fragment.split('#')[0]  # Remove anchors
            if clean_fragment:
                query = f'{query} "{clean_fragment}"'
        
        logger.info(f"Searching for article with query: {query}")
        
        # Perform the query with extended timespan to ensure we find the article
        result = self.query(
            query=query,
            mode="PointData",
            output_format="GeoJSON",
            timespan="7d",  # Use longer timespan to increase chances of finding it
            maxpoints=100
        )
        
        # Extract contexts from all results
        article_contexts = self.get_article_context(result, include_content=True)
        
        # Find the exact article matching the URL
        target_article = None
        for article in article_contexts:
            if isinstance(article, dict) and article.get("url") == article_url:
                target_article = article
                break
        
        if not target_article:
            logger.warning(f"Article with URL {article_url} not found in GDELT data")
            return {"error": "Article not found", "url": article_url}
            
        # Enhance the article context with additional information
        enhanced_article = target_article.copy()
        
        # Get location information if available
        if "location" in enhanced_article and enhanced_article["location"].get("lat") and enhanced_article["location"].get("lon"):
            lat = enhanced_article["location"].get("lat")
            lon = enhanced_article["location"].get("lon")
            
            # Get nearby coverage
            nearby = self.find_nearby_coverage(
                lat=lat,
                lon=lon,
                radius="50km"  # Smaller radius for more relevant content
            )
            nearby_contexts = self.get_article_context(nearby)
            
            # Remove the target article itself from nearby contexts
            nearby_contexts = [a for a in nearby_contexts 
                             if isinstance(a, dict) and 
                             a.get("url") != article_url]
            
            enhanced_article["nearby_coverage"] = nearby_contexts[:5]  # Limit to 5 articles
        
        # Add source country information if available
        if "domain" in enhanced_article:
            domain = enhanced_article["domain"]
            enhanced_article["source_info"] = {
                "domain": domain
            }
        
        return enhanced_article
            
    def _extract_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url (str): Full URL
            
        Returns:
            str: Domain name
        """
        try:
            # Remove protocol
            domain = url.split('://')[-1]
            # Remove path and query parameters
            domain = domain.split('/')[0]
            # Remove port if present
            domain = domain.split(':')[0]
            return domain
        except:
            # Return original if extraction fails
            logger.error(f"Failed to extract domain from URL: {url}")
            return url
    
    def get_geographic_context(self, 
                             location_name: str,
                             topic: Optional[str] = None,
                             timespan: str = "7d",
                             radius_km: int = 100) -> Dict:
        """
        Get comprehensive geographic context for a location, optionally
        filtered by a topic.
        
        This method provides a deep geographic analysis of news coverage
        for a location, including:
        - Articles mentioning the location
        - Geographic positioning and hierarchy
        - Topics and themes associated with the location
        - Nearby coverage and related locations
        - Tone analysis specific to the location
        
        Args:
            location_name (str): Name of the location to analyze
            topic (Optional[str]): Optional topic to filter results
            timespan (str): Time range to search
            radius_km (int): Radius in km for nearby coverage
            
        Returns:
            Dict: Geographic context analysis
        """
        # Build query
        if topic:
            query = f'location:"{location_name}" {topic}'
        else:
            query = f'location:"{location_name}"'
            
        # Get direct coverage of the location
        location_coverage = self.query(
            query=query,
            mode="PointData",
            output_format="GeoJSON",
            timespan=timespan
        )
        
        # Extract article contexts
        article_contexts = self.get_article_context(location_coverage)
        
        # Get coordinates of the location from the results
        lat, lon = None, None
        for article in article_contexts:
            if isinstance(article, dict) and "location" in article:
                location = article.get("location", {})
                if location.get("name", "").lower() == location_name.lower():
                    lat = location.get("lat")
                    lon = location.get("lon")
                    break
        
        # Get nearby coverage if we found coordinates
        nearby_contexts = []
        if lat and lon:
            nearby_coverage = self.find_nearby_coverage(
                lat=lat,
                lon=lon,
                radius=f"{radius_km}km"
            )
            nearby_contexts = self.get_article_context(nearby_coverage)
        
        # Extract themes mentioned in relation to this location
        themes = set()
        for article in article_contexts:
            if isinstance(article, dict) and "themes" in article:
                article_themes = article.get("themes", [])
                if article_themes:
                    for theme in article_themes:
                        themes.add(theme)
        
        # Calculate tone statistics
        tones = [article.get("tone", 0) for article in article_contexts 
                if isinstance(article, dict) and "tone" in article]
        
        avg_tone = sum(tones) / len(tones) if tones else 0
        min_tone = min(tones) if tones else 0
        max_tone = max(tones) if tones else 0
        
        # Return comprehensive geographic context
        return {
            "location_name": location_name,
            "topic": topic,
            "timespan": timespan,
            "coordinates": {
                "lat": lat,
                "lon": lon
            },
            "articles": article_contexts,
            "nearby_coverage": nearby_contexts,
            "themes": list(themes),
            "tone_analysis": {
                "average": avg_tone,
                "minimum": min_tone,
                "maximum": max_tone
            }
        }
        
# Example usage
if __name__ == "__main__":
    # Initialize the API client
    geo_api = GDELTGeoAPI()
    
    try:
        # Example 1: Create a map of Trump-related coverage by country
        trump_map = geo_api.keyword_map("trump", mode="Country")
        print(f"Created map with {len(trump_map.get('features', []))} country features")
        
        # Example 2: Find all coverage mentioning Paris
        paris_coverage = geo_api.coverage_by_location("paris")
        print(f"Found {len(paris_coverage.get('features', []))} articles mentioning Paris")
        
        # Example 3: Find images of flooding
        flood_images = geo_api.image_search("(imagetag:\"flood\" OR imagewebtag:\"flood\")", 
                                          mode="ImageCountry")
        print(f"Found flood images from {len(flood_images.get('features', []))} countries")
        
        # Example 4: Find news coverage within 100km of London
        london_nearby = geo_api.find_nearby_coverage(51.5074, -0.1278, "100km")
        print(f"Found {len(london_nearby.get('features', []))} articles near London")
        
        # Example 5: Get article context from coverage by location
        paris_articles = geo_api.coverage_by_location("paris", timespan="1d")
        article_contexts = geo_api.get_article_context(paris_articles)
        print(f"Extracted context from {len(article_contexts)} articles mentioning Paris")
        
        # Example 6: Query article context directly for positive news about climate
        climate_positive = geo_api.query_article_context(
            query="climate tone>5",
            mode="PointData",
            timespan="3d",
            sortby="ToneDesc"
        )
        print(f"Found {len(climate_positive)} positive climate news articles")
        
        # Example 7: Get news from CNN about healthcare
        cnn_healthcare = geo_api.search_by_domain(
            domain="cnn.com",
            additional_query="healthcare",
            timespan="7d"
        )
        healthcare_context = geo_api.get_article_context(cnn_healthcare)
        print(f"Found {len(healthcare_context)} CNN articles about healthcare")
        
        # Example 8: Complex image search for protest photos with 10+ people
        protest_images = geo_api.search_complex_image_query(
            image_tags=["protest", "demonstration"],
            min_faces=10,
            timespan="7d"
        )
        print(f"Found {len(protest_images.get('features', []))} protest images with 10+ people")
        
        # Example 9: Multi-country analysis of climate change coverage
        climate_analysis = geo_api.search_multi_country_topic(
            topic="climate change",
            countries=["US", "GB", "FR", "DE", "CN"],
            source_countries=["US", "GB"],
            timespan="7d"
        )
        print(f"Analyzed climate change coverage across multiple countries with {len(climate_analysis.get('features', []))} features")
        
        # Example 10: Get full article context for a specific article
        # For demonstration purposes, use the first article from Paris coverage if available
        example_article = None
        if article_contexts and len(article_contexts) > 0:
            for article in article_contexts:
                if isinstance(article, dict) and "url" in article and article["url"]:
                    example_article = article["url"]
                    break
        
        if example_article:
            print(f"Using example article URL: {example_article}")
            article_context = geo_api.get_full_article_context(example_article)
            if "error" not in article_context:
                print(f"Retrieved full context for article: {article_context.get('title', '')}")
            else:
                print(f"Error: {article_context.get('error', '')}")
        else:
            print("No example article URL found to demonstrate get_full_article_context")
        
        # Example 11: Get geographic context for a location
        ukraine_context = geo_api.get_geographic_context(
            location_name="Kyiv",
            topic="conflict",
            timespan="7d"
        )
        print(f"Retrieved geographic context for Kyiv with {len(ukraine_context.get('articles', []))} articles")
        
    except Exception as e:
        import traceback
        print(f"Error running examples: {str(e)}")
        traceback.print_exc() 