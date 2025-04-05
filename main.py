import os
from rank_bm25 import BM25Okapi
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
import json
from google import genai
from time import time, sleep


class Gemini:
    def __init__(self, model_name: str):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs) -> str:
        start_time = time()
        while time() - start_time < 60:  # 60 seconds timeout
            try:
                output = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                ).text
                if output:
                    return output
            except genai.errors.ServerError:
                print("Server error, retrying...")
            sleep(10)
        return ''

# Download required NLTK resources
nltk.download('punkt', download_dir='.venv/nltk_data')
nltk.download('punkt_tab', download_dir='.venv/nltk_data')
nltk.download('stopwords', download_dir='.venv/nltk_data')

def preprocess_text(text):
    # Convert to lowercase and remove punctuation
    text = text.lower()
    text = ''.join([char for char in text if char not in string.punctuation])
    
    # Tokenize and remove stopwords
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    
    return tokens

def create_bm25_index(documents):
    # Preprocess all documents
    tokenized_docs = [preprocess_text(doc['content']) for doc in documents]
    
    # Create BM25 index
    bm25 = BM25Okapi(tokenized_docs)
    return bm25, tokenized_docs

def search(query, bm25_index, tokenized_docs, original_docs, top_k=5):
    # Preprocess query
    tokenized_query = preprocess_text(query)
    
    # Get scores for each document
    doc_scores = bm25_index.get_scores(tokenized_query)
    
    # Get top-k documents
    top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:top_k]
    results = [(original_docs[i], doc_scores[i]) for i in top_indices]
    
    return results


def rate_article(article, query):
    gemini = Gemini(model_name="gemini-2.0-flash-thinking-exp")
    prompt = f"""This is a news article:
{article['content']}

Please rate how positive the article is with respect to the following subject:
{query}

Please rate the article on a scale of 1 to 10, where 1 is very negative and 10 is very positive.

Format your response as follows:

'any thinking you did'
<rating>'score'</rating>
"""
    response = gemini.generate(prompt)
    rating = response.split('<rating>')[1].split('</rating>')[0]
    return float(rating)


if __name__ == "__main__":
    with open('recent_news.json', 'r') as f:
        data = json.load(f)

    bm25, tokenized_docs = create_bm25_index(data)
    results = search("tariff", bm25, tokenized_docs, data, top_k=5)
    for doc, score in results:
        print(doc['title'], doc['source'], score)
        rating = rate_article(doc, "tariff")
        print(rating)
