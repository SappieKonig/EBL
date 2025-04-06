import pandas as pd
import os
import json
import time
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
import string
from google import genai

class Gemini:
    def __init__(self, model_name: str):
        self.client = genai.Client(api_key=os.env['GEMINI_API_KEY'])
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs) -> str:
        start = time.time()
        while True:
            try:
                output = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                ).text
                return output
            except Exception as e:
                print(e)
                time.sleep(10)
                if time.time() - start > 60:
                    raise e

# Download required NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

def preprocess_text(text):
    # Convert to lowercase and remove punctuation
    text = text.lower()
    text = ''.join([char for char in text if char not in string.punctuation])
    
    # Tokenize and remove stopwords
    tokens = word_tokenize(text)
    
    return tokens

def create_bm25_index(documents):
    # Preprocess all documents
    tokenized_docs = [preprocess_text(doc['ContextualText']) for doc in documents]
    
    # Create BM25 index
    bm25 = BM25Okapi(tokenized_docs)
    return bm25

def search(query, bm25_index, original_docs, top_k=5):
    # Preprocess query
    tokenized_query = preprocess_text(query)
    
    # Get scores for each document
    doc_scores = bm25_index.get_scores(tokenized_query)
    
    # Get top-k documents
    top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:top_k]
    results = [(original_docs[i], float(doc_scores[i])) for i in top_indices]
    
    return results


def translate_query(query, all_languages):
    all_languages_not_english = [lang for lang in all_languages if lang != 'en']
    prompt = f"""Translate this query: '{query}' to the following languages: {', '.join(all_languages_not_english)}
    Return the query in the following format:
    TranslatedQuery:
      Language: string
      Query: string
    Return:
      List[TranslatedQuery]
    """
    llm = Gemini("gemini-2.0-flash")
    output = llm.generate(prompt)
    try:
        json_output = json.loads(output.split("```json")[1].split("```")[0])
    except Exception as e:
        try:
            json_output = json.loads(output)
        except Exception as e:
            return None
    parsed_output = {'en': query}
    for query in json_output:
        parsed_output[query["TranslatedQuery"]["Language"]] = query["TranslatedQuery"]["Query"]
    return parsed_output


class Retriever:
    def __init__(self, docs, llm='gemini-2.0-flash'):
        self.llm = Gemini(llm)
        self.all_languages = ['sq', 'fr', 'ar', 'es', 'et', 'ru', 'nl', 'de', 'pt', 'bn', 'zh-cn', 'it', 'pl', 'sv', 'ml', 'id', 'el', 'ta', 'hi', 'hr', 'ne', 'da', 'ur', 'ko', 'th', 'hu', 'mk', 'ro', 'fa', 'sl', 'vi', 'fi', 'pa', 'gu', 'zh-tw', 'mr', 'he', 'tr', 'no']
        country_codes = set([doc['CountryCode'] for doc in docs])
        self.docs = {}
        self.databases = {}
        self.dominant_languages = {'MY': 'en', 'FI': 'fi', 'AM': 'et', 'EC': 'es', 'KZ': 'en', 'PK': 'en', 'NI': 'en', 'BE': 'fr', 'CO': 'es', 'AS': 'en', 'SY': 'ar', 'MD': 'ro', 'BG': 'en', 'CA': 'en', 'CH': 'zh-cn', 'TW': 'ko', 'BA': 'ar', 'HU': 'hu', 'RS': 'ru', 'NO': 'no', 'NP': 'ne', 'SA': 'ar', 'AE': 'en', 'ES': 'es', 'BH': 'en', 'PL': 'pl', 'FR': 'fr', 'CU': 'en', 'SI': 'sl', 'MK': 'mk', 'CM': 'fr', 'NL': 'nl', 'MX': 'es', 'ID': 'id', 'EG': 'ar', 'RO': 'ro', 'SG': 'fr', 'VE': 'es', 'GH': 'en', 'PE': 'es', 'BR': 'pt', 'IS': 'ar', 'US': 'en', 'GT': 'es', 'UG': 'en', 'GR': 'el', 'IT': 'it', 'CY': 'el', 'AG': 'fr', 'MT': 'en', 'BD': 'en', 'PA': 'es', 'AF': 'en', 'IN': 'en', 'JM': 'en', 'HR': 'hr', 'LU': 'fr', 'IR': 'fa', 'AL': 'sq', 'TH': 'th', 'AR': 'es', 'BY': 'fr', 'BO': 'ru'}
        for country_code in country_codes:
            country_docs = [doc for doc in docs if doc['CountryCode'] == country_code]
            self.docs[country_code] = country_docs
            self.databases[country_code] = create_bm25_index(country_docs)

    def get_documents_for_query(self, query, top_k=20):
        translated_queries = translate_query(query, self.all_languages)
        print("Translated queries")
        if translated_queries is None:
            return None
        all_results = []
        for country_code, db in self.databases.items():
            language = self.dominant_languages[country_code]
            query = translated_queries[language]
            results = search(query, db, self.docs[country_code], top_k)
            if results is not None:
                all_results.extend(results)
        return all_results
    
if __name__ == "__main__":
    # Load news data
    docs = pd.read_csv("filtered_articles.csv").to_dict(orient='records')
    retriever = Retriever(docs)
    print(len(retriever.get_documents_for_query("What is the weather in Tokyo?")))

