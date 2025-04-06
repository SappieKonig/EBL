# helper_server.py - Run this in a separate process
# this is a workaround for an error where multiple cuda processes are being started
import json
import numpy as np
import spacy
from gensim.downloader import load as gensim_load
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load models once at startup
print("Loading models...")
model = gensim_load("glove-wiki-gigaword-100")
nlp = spacy.load("en_core_web_sm")
print("Models loaded successfully!")

@app.route('/is_named_entity', methods=['POST'])
def check_named_entity():
    data = request.json
    text = data['text']
    
    doc = nlp(text)
    result = False
    for ent in doc.ents:
        if ent.text.strip().lower() == text.strip().lower():
            result = True
            break
    
    return jsonify({'result': result})

@app.route('/expand_topic', methods=['POST'])
def expand_topic_endpoint():
    data = request.json
    topic = data['topic']
    topn = data.get('topn', 15)
    
    # Check if named entity
    doc = nlp(topic)
    is_entity = False
    for ent in doc.ents:
        if ent.text.strip().lower() == topic.strip().lower():
            is_entity = True
            break
    
    if is_entity:
        return jsonify({'expanded_topic': topic})
    
    # Expand the topic
    tokens = topic.lower().split()
    tokens_in_vocab = [token for token in tokens if token in model.key_to_index]
    extra_words = []
    
    if tokens_in_vocab:
        vectors = [model.get_vector(token) for token in tokens_in_vocab]
        avg_vector = np.mean(vectors, axis=0)
        similar = model.most_similar(positive=[avg_vector], topn=topn)
        extra_words = [word for word, score in similar]
    
    expanded_topic = topic + " " + " ".join(extra_words)
    return jsonify({'expanded_topic': expanded_topic})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)# helper_server.py - Run this in a separate process import json import numpy as np import spacy from gensim.downloader import load as gensim_load from flask import Flask, request, jsonify  app = Flask(__name__)  # Load models once at startup print("Loading models...") model = gensim_load("glove-wiki-gigaword-100") nlp = spacy.load("en_core_web_sm") print("Models loaded successfully!")  @app.route('/is_named_entity', methods=['POST']) def check_named_entity():     data = request.json     text = data['text']          doc = nlp(text)     result = False     for ent in doc.ents:         if ent.text.strip().lower() == text.strip().lower():             result = True             break          return jsonify({'result': result})  @app.route('/expand_topic', methods=['POST']) def expand_topic_endpoint():     data = request.json     topic = data['topic']     topn = data.get('topn', 15)          # Check if named entity     doc = nlp(topic)     is_entity = False     for ent in doc.ents:         if ent.text.strip().lower() == topic.strip().lower():             is_entity = True             break          if is_entity:         return jsonify({'expanded_topic': topic})          # Expand the topic     tokens = topic.lower().split()     tokens_in_vocab = [token for token in tokens if token in model.key_to_index]     extra_words = []          if tokens_in_vocab:         vectors = [model.get_vector(token) for token in tokens_in_vocab]         avg_vector = np.mean(vectors, axis=0)         similar = model.most_similar(positive=[avg_vector], topn=topn)         extra_words = [word for word, score in similar]          expanded_topic = topic + " " + " ".join(extra_words)     return jsonify({'expanded_topic': expanded_topic})  if __name__ == '__main__':     app.run(host='0.0.0.0', port=5000)

