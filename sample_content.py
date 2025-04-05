import json

with open('recent_news.json', 'r') as f:
    data = json.load(f)

article = data[0]
print(article['content'])