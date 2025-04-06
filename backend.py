import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from rate import DocumentRater
import numpy as np
import requests
import subprocess 
from retriever import Retriever
from code_to_name import code_to_name

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes and origins

# Load the GloVe model once at startup.
doc_rater = DocumentRater()
docs = pd.read_csv("filtered_articles.csv").to_dict(orient='records')
retriever = Retriever(docs)
SERVER_URL = "http://localhost:5000"

def is_named_entity(text):
    response = requests.post(f"{SERVER_URL}/is_named_entity", json={"text": text})
    return response.json()['result']

def expand_topic(topic, topn=15):
    response = requests.post(f"{SERVER_URL}/expand_topic", json={"topic": topic, "topn": topn})
    return response.json()['expanded_topic']

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route('/api/opinions', methods=['POST'])
def opinions():
    data = request.get_json()
    topic = data.get("topic", "Your topic here")
    positive_modifier = data.get("positiveModifier", "beneficial")
    negative_modifier = data.get("negativeModifier", "harmful")

    topic = topic.lower()

    # Expand the topic only if it isn't a named entity.
    expanded_topic = expand_topic(topic, topn=5)
    retrieved = retriever.get_documents_for_query(expanded_topic)
    retrieved = [doc[0] for doc in retrieved]
    # possible filtering
    articles = [doc['ContextualText'] for doc in retrieved]
    filtered_docs = []
    scores = doc_rater.rate_documents(articles, topic, negative_modifier, positive_modifier)
    for doc, score in zip(retrieved, scores):
        try:
            if score[0] == -1 or score[1] == -1:
                continue
            doc['Relevance'] = int(score[0])
            doc['Rating'] = int(score[1])
            filtered_docs.append(doc)
        except Exception:
            pass
    retrieved = filtered_docs
    df = pd.DataFrame(retrieved)
    relevance_cutoff = 7
    df = df[df['Relevance'] >= relevance_cutoff]

    average_sentiment_per_country = df.groupby('CountryCode')['Rating'].mean().reset_index()
    print(average_sentiment_per_country)
   
    response = {}

    formatted_sentiment = {}
    for code, group in df.groupby('CountryCode'):
        country_name = code_to_name.get(code, code)
        avg_score = group["Rating"].mean()
        top_articles = group.nlargest(3, "Rating")
        bottom_articles = group.nsmallest(3, "Rating")
        articles_list = []
        for _, row in top_articles.iterrows():
            articles_list.append({
                "title": row["Title"],
                "url": row["URLs"],
                "sentiment": positive_modifier
            })
        for _, row in bottom_articles.iterrows():
            articles_list.append({
                "title": row["Title"],
                "url": row["URLs"],
                "sentiment": negative_modifier
            })

        formatted_sentiment[country_name] = {
            "score": round(avg_score, 2),
            "topArticles": articles_list
        }

    response.update(formatted_sentiment) 
    print(response)

    return jsonify(response)

if __name__ == '__main__':
    subprocess.Popen(['.venv/bin/python', 'expand_query.py'])
    app.run(host='0.0.0.0', port=443, ssl_context=('cert.pem', 'key.pem'))
