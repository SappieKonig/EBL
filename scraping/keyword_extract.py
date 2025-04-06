"""
Extract the most common keywords and phrases from the ContextualText column in a CSV file,
including context around frequent keywords, and save them to CSV files.
"""
import pandas as pd
import re
import string
from collections import Counter
import csv
from tqdm import tqdm
import sys
import os
from datetime import datetime
import nltk
from nltk.util import ngrams
import json

# Download necessary NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Set chunk size for reading large CSV
CHUNK_SIZE = 10000

# Define stop words - common words to exclude from keyword analysis
STOP_WORDS = set([
    # English stop words
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for", 
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", 
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", 
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", 
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", 
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves", 
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", 
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", 
    "will", "with", "you", "your", "yours", "yourself", "yourselves", "ll", "ve", "m", "re", "d",
    
    # Spanish stop words
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "si", "no", "como", 
    "que", "cuando", "donde", "quien", "cual", "cuanto", "este", "esta", "estos", "estas", "ese", 
    "esa", "esos", "esas", "aquel", "aquella", "aquellos", "aquellas", "mi", "tu", "su", "nuestro", 
    "vuestro", "sus", "mis", "tus", "por", "para", "sin", "con", "contra", "porque", "pues", "ya",
    "más", "menos", "mejor", "peor", "bien", "mal", "ser", "estar", "tener", "hacer", "decir", "ir",
    "venir", "dar", "ver", "saber", "poder", "deber", "querer", "gustar", "hay", "está", "son", "somos",
    
    # French stop words
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "mais", "si", "ne", "pas", "comme", 
    "que", "quand", "où", "qui", "quel", "quelle", "quels", "quelles", "ce", "cette", "ces", "mon", 
    "ton", "son", "notre", "votre", "leur", "mes", "tes", "ses", "nos", "vos", "leurs", "pour", "sans", 
    "avec", "contre", "parce", "donc", "déjà", "plus", "moins", "mieux", "pire", "bien", "mal", "être", 
    "avoir", "faire", "dire", "aller", "venir", "donner", "voir", "savoir", "pouvoir", "devoir", "vouloir",
    
    # German stop words
    "der", "die", "das", "ein", "eine", "eines", "einem", "einen", "einer", "und", "oder", "aber", "wenn", 
    "nicht", "als", "wie", "dass", "wann", "wo", "wer", "welche", "welcher", "welches", "mein", "dein", 
    "sein", "unser", "euer", "ihr", "meine", "deine", "seine", "unsere", "eure", "ihre", "für", "ohne", 
    "mit", "gegen", "weil", "also", "schon", "mehr", "weniger", "besser", "schlechter", "gut", "schlecht", 
    "sein", "haben", "machen", "sagen", "gehen", "kommen", "geben", "sehen", "wissen", "können", "müssen", 
    "wollen", "mögen",
    
    # Italian stop words
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "e", "o", "ma", "se", "non", "come", 
    "che", "quando", "dove", "chi", "quale", "quanto", "questo", "questa", "questi", "queste", "quello", 
    "quella", "quelli", "quelle", "mio", "tuo", "suo", "nostro", "vostro", "loro", "miei", "tuoi", "suoi", 
    "nostri", "vostri", "per", "senza", "con", "contro", "perché", "dunque", "già", "più", "meno", "meglio", 
    "peggio", "bene", "male", "essere", "avere", "fare", "dire", "andare", "venire", "dare", "vedere", 
    "sapere", "potere", "dovere", "volere",
    
    # Portuguese stop words
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "e", "ou", "mas", "se", "não", "como", 
    "que", "quando", "onde", "quem", "qual", "quanto", "este", "esta", "estes", "estas", "esse", 
    "essa", "esses", "essas", "aquele", "aquela", "aqueles", "aquelas", "meu", "teu", "seu", "nosso", 
    "vosso", "minha", "tua", "sua", "nossa", "vossa", "por", "para", "sem", "com", "contra", "porque", 
    "pois", "já", "mais", "menos", "melhor", "pior", "bem", "mal", "ser", "estar", "ter", "fazer", 
    "dizer", "ir", "vir", "dar", "ver", "saber", "poder", "dever", "querer",
    
    # Arabic stop words (transliterated and common Arabic words)
    "من", "إلى", "عن", "على", "في", "فوق", "تحت", "بين", "و", "أو", "ثم", "لكن", "إذا", "لا", "مثل",
    "الذي", "التي", "الذين", "عندما", "أين", "من", "هذا", "هذه", "هؤلاء", "ذلك", "تلك", "أولئك", "أنا", 
    "أنت", "هو", "هي", "نحن", "أنتم", "هم", "لي", "لك", "له", "لها", "لنا", "لكم", "لهم", "كان", "كانت", 
    "كانوا", "يكون", "تكون", "يكونوا", "ماذا", "متى", "كيف", "لماذا", "كم", "أي", "نعم", "لا", "ربما", 
    "فقط", "قد", "إن", "كل", "بعض", "غير", "مع", "ضد", "لأن", "حتى", "مرة", "مرات", "هناك", "هنا",
    "wa", "fi", "min", "ila", "ala", "an", "hatha", "hathe", "thalek", "tilka", "al", "alathi", "alati",
    "fi", "la", "lan", "lam", "ma", "laysa", "laisa", "sawfa", "ana", "anta", "anti", "huwa", "hiya", 
    "nahnu", "antum", "antunna", "hum", "hunna", "hadha", "hadhihi", "dhalika", "tilka", "kan", "kanat",
    "kanu", "yakun", "takun", "yakunu", "kam", "ayy", "hal", "mata", "ayna", "kayfa", "idha"
])

def clean_text(text):
    """Clean and normalize text for keyword extraction"""
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_keywords(text):
    """Extract keywords from text, filtering out stop words and short words"""
    if not text:
        return []
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Split into words
    words = cleaned_text.split()
    
    # Filter out stop words and words less than 3 characters
    keywords = [word for word in words if word not in STOP_WORDS and len(word) >= 3]
    
    return keywords

def extract_phrases(text, n=2):
    """Extract n-gram phrases from text"""
    if not text:
        return []
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Tokenize the text
    tokens = cleaned_text.split()
    
    # Generate n-grams
    n_grams = list(ngrams(tokens, n))
    
    # Filter out n-grams that contain stop words or short words
    filtered_ngrams = []
    for gram in n_grams:
        if all(word not in STOP_WORDS and len(word) >= 3 for word in gram):
            filtered_ngrams.append(" ".join(gram))
    
    return filtered_ngrams

def extract_context(text, keyword, window_size=3):
    """
    Extract context around a keyword (words before and after)
    Returns a list of context windows containing the keyword
    """
    if not text or not keyword:
        return []
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Tokenize the text
    tokens = cleaned_text.split()
    
    # Find the keyword in the tokens
    contexts = []
    for i, token in enumerate(tokens):
        if token == keyword:
            # Get the window of words before and after the keyword
            start = max(0, i - window_size)
            end = min(len(tokens), i + window_size + 1)
            
            # Create a context window
            context = " ".join(tokens[start:end])
            contexts.append(context)
    
    return contexts

def main():
    # Define file paths
    input_file = "random_order_articles.csv"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"article_keywords_{timestamp}.csv"
    phrases_output_file = f"article_phrases_{timestamp}.csv"
    context_output_file = f"keyword_contexts_{timestamp}.json"
    
    # Create output directory if it doesn't exist
    os.makedirs("data/topics", exist_ok=True)
    output_path = os.path.join("data/topics", output_file)
    phrases_output_path = os.path.join("data/topics", phrases_output_file)
    context_output_path = os.path.join("data/topics", context_output_file)
    
    all_keywords = Counter()
    all_bigrams = Counter()
    all_trigrams = Counter()
    keyword_contexts = {}
    
    total_articles = 0
    articles_with_text = 0
    
    print(f"Processing {input_file}...")
    
    try:
        # Get an estimate of the total number of chunks
        with open(input_file, "r", encoding="utf-8") as f:
            # Count lines in the first 1MB to estimate total
            sample = f.read(1024*1024)  # Read first 1MB
            sample_lines = sample.count('\n')
            file_size = os.path.getsize(input_file)
            estimated_lines = int((file_size / (1024*1024)) * sample_lines)
            estimated_chunks = (estimated_lines // CHUNK_SIZE) + 1
        
        # Process the CSV file in chunks
        chunk_iter = pd.read_csv(input_file, chunksize=CHUNK_SIZE)
        for i, chunk in enumerate(tqdm(chunk_iter, total=estimated_chunks, desc="Processing chunks")):
            # Check if the ContextualText column exists
            if 'ContextualText' not in chunk.columns:
                print("Error: 'ContextualText' column not found in the CSV file.")
                sys.exit(1)
            
            # Process each row in the chunk
            for _, row in chunk.iterrows():
                total_articles += 1
                contextual_text = row.get('ContextualText', '')
                if isinstance(contextual_text, str) and contextual_text.strip():
                    articles_with_text += 1
                    
                    # Extract single keywords
                    keywords = extract_keywords(contextual_text)
                    all_keywords.update(keywords)
                    
                    # Extract bigrams (2-word phrases)
                    bigrams = extract_phrases(contextual_text, 2)
                    all_bigrams.update(bigrams)
                    
                    # Extract trigrams (3-word phrases)
                    trigrams = extract_phrases(contextual_text, 3)
                    all_trigrams.update(trigrams)
        
        # Get the top 100 keywords to extract context for
        top_keywords = [kw for kw, _ in all_keywords.most_common(100)]
        
        print(f"Extracting context for top {len(top_keywords)} keywords...")
        
        # Second pass to gather context for top keywords
        chunk_iter = pd.read_csv(input_file, chunksize=CHUNK_SIZE)
        for i, chunk in enumerate(tqdm(chunk_iter, total=estimated_chunks, desc="Extracting contexts")):
            for _, row in chunk.iterrows():
                contextual_text = row.get('ContextualText', '')
                if isinstance(contextual_text, str) and contextual_text.strip():
                    for keyword in top_keywords:
                        contexts = extract_context(contextual_text, keyword)
                        if contexts:
                            if keyword not in keyword_contexts:
                                keyword_contexts[keyword] = []
                            keyword_contexts[keyword].extend(contexts[:5])  # Limit to 5 contexts per article
        
        # Sort keywords by frequency (most common first)
        sorted_keywords = all_keywords.most_common()
        sorted_bigrams = all_bigrams.most_common()
        sorted_trigrams = all_trigrams.most_common()
        
        # Write keywords to CSV
        print(f"Writing {len(sorted_keywords)} keywords to {output_path}...")
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Keyword', 'Frequency'])
            writer.writerows(sorted_keywords)
        
        # Write phrases to CSV
        print(f"Writing {len(sorted_bigrams)} bigrams and {len(sorted_trigrams)} trigrams to {phrases_output_path}...")
        with open(phrases_output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Phrase', 'Words', 'Frequency'])
            
            # Write bigrams
            for phrase, count in sorted_bigrams:
                writer.writerow([phrase, 2, count])
            
            # Write trigrams
            for phrase, count in sorted_trigrams:
                writer.writerow([phrase, 3, count])
        
        # Write contexts to JSON
        print(f"Writing keyword contexts to {context_output_path}...")
        with open(context_output_path, 'w', encoding='utf-8') as jsonfile:
            # Limit the number of contexts per keyword to avoid massive file
            limited_contexts = {k: v[:20] for k, v in keyword_contexts.items()}
            json.dump(limited_contexts, jsonfile, ensure_ascii=False, indent=2)
        
        print(f"Done! Processed {total_articles} articles ({articles_with_text} had text)")
        print(f"Found {len(sorted_keywords)} unique keywords")
        print(f"Found {len(sorted_bigrams)} unique bigrams")
        print(f"Found {len(sorted_trigrams)} unique trigrams")
        print(f"Extracted context for {len(keyword_contexts)} top keywords")
        print(f"Results saved to:")
        print(f"- Keywords: {output_path}")
        print(f"- Phrases: {phrases_output_path}")
        print(f"- Contexts: {context_output_path}")
        
        # Display top keywords
        print(f"\nTop 20 keywords:")
        for keyword, count in sorted_keywords[:20]:
            print(f"  {keyword}: {count}")
        
        # Display top bigrams
        print(f"\nTop 20 bigrams:")
        for phrase, count in sorted_bigrams[:20]:
            print(f"  {phrase}: {count}")
        
        # Display top trigrams
        print(f"\nTop 20 trigrams:")
        for phrase, count in sorted_trigrams[:20]:
            print(f"  {phrase}: {count}")
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()