import pandas as pd
from vllm import LLM, SamplingParams

def get_topics(text, llm, sampling_params):
    prompt = f"""This is an article:
{text}
List 5 topics that are talked about in this particle, like so:
<topics>
1. topic1
2. topic2
3. topic3
4. topic4
5. topic5
</topics>
With every topic described in 1-5 words"""
    message = [{
        'role': 'user',
        'content': prompt
    }]
    output = llm.chat(message, sampling_params=sampling_params)[0].outputs[0].text
    try:
        topics = output.split('<topics>')[1].split('</topics>')[0].strip()
        topics = [' '.join(line.split(' ')[1:]) for line in topics.split('\n')]
        return topics
    except Exception as e:
        print(e, output)
        return None

def generate_modifiers(topic, llm, sampling_params):
    prompt = f"""For the topic '{topic}', generate 3 distinct modifier pairs that represent contrasting perspectives or dimensions through which this topic is discussed in news media globally. Each modifier should be formatted as 'Dimension A vs Dimension B' where these represent opposing viewpoints or approaches. Go beyond basic sentiment (positive/negative) to capture nuanced political, economic, social, or strategic dimensions.

For each modifier pair, provide a brief explanation of why this dimension is significant in global discourse about the topic.

Examples:

For topic "Climate Change":
1. Urgent priority vs Overstated concern
   - This dimension captures the debate over the severity and immediacy of climate threats
2. Government regulation vs Market-based solutions 
   - This reflects competing approaches to addressing environmental challenges
3. Global responsibility vs National sovereignty
   - This highlights tensions between international cooperation and domestic priorities

For topic "Vaccines":
1. Public health necessity vs Personal freedom concern
   - This captures the tension between collective health benefits and individual choice
2. Scientific breakthrough vs Rushed development
   - This reflects contrasting views on the reliability and testing of medical innovations
3. Collective protection vs Individual risk
   - This highlights the balance between population-wide benefits and personal risk assessment"""
    
    message = [{
        'role': 'user',
        'content': prompt
    }]
    
    output = llm.chat(message, sampling_params=sampling_params)[0].outputs[0].text
    
    try:
        modifiers = []
        lines = output.strip().split('\n')
        
        for line in lines:
            for numbering in ['1.', '2.', '3.']:
                if numbering in line and 'vs.' in line:
                    modifiers = line.split(numbering)[1].strip(' *')
                    print(line, topic)
                    modifiers.append(modifiers.split("vs. "))
                
        return modifiers[:3]  # Limit to 3 modifiers
    except Exception as e:
        print(f"Error extracting modifiers: {e}")
        print(f"Raw output: {output}")
        return []

if __name__ == '__main__':
    llm = LLM(
        model="google/gemma-3-12b-it",
        dtype="bfloat16",
        tensor_parallel_size=2,
        gpu_memory_utilization=0.9,
        max_num_batched_tokens=8192,
        enable_chunked_prefill=True,
        block_size=16,
        max_num_seqs=1,
    )
    
    sampling_params = SamplingParams(
        temperature=0.7,
        max_tokens=1024,
        top_p=0.9,
    )
    
    file = pd.read_csv('gdelt_ggg.csv')
    docs = file['ContextualText']
    
    topic_modifier_pairs = []
    
    for i, doc in enumerate(docs):
        if i == 10:
            break
        topics = get_topics(doc, llm, sampling_params)
        if topics:
            for topic in topics:
                modifiers = generate_modifiers(topic, llm, sampling_params)
                for mod_left, mod_right in modifiers:
                    topic_modifier_pairs.append((topic, mod_left, mod_right))
                    print(f"Topic: {topic}, Modifier: {mod_left} vs {mod_right}")
    
    # Save results
    pd.DataFrame(topic_modifier_pairs, columns=['Topic', 'Mod_left', 'Mod_right']).to_csv('topic_modifiers.csv', index=False)
    exit()