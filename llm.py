from vllm import LLM, SamplingParams
from prompt_utils import get_rating_prompt, create_bm25_index, search, get_rating


def process_batch(prompts, llm, sampling_params):
    print("Processing batch...")
    # Process all prompts in a single batch
    messages = [[{
        'role': 'user',
        'content': prompt,
    }] for prompt in prompts]
    outputs = llm.chat(messages, sampling_params)
    
    # Extract results
    results = [output.outputs[0].text for output in outputs]
    return results


if __name__ == "__main__":
    subject = 'trump'
    top_k = 5

    llm = LLM(
        model="google/gemma-3-12b-it",
        dtype="bfloat16",
        tensor_parallel_size=2,
        gpu_memory_utilization=0.9,  # Slightly reduced
        max_num_batched_tokens=8192,  # Reduced from 16384
        enable_chunked_prefill=True,
        block_size=16,  # Reduced from 16 to 8
        max_num_seqs=128,  # Reduced from 256
    )

    sampling_params = SamplingParams(
        temperature=0.7,
        max_tokens=1024,
        top_p=0.9,
    )

    import json
    with open('recent_news.json', 'r') as f:
        data = json.load(f)

    bm25, tokenized_docs = create_bm25_index(data)
    results = search(subject, bm25, tokenized_docs, data, top_k=top_k)
    prompts = [get_rating_prompt(result[0], subject) for result in results]
    llm_answers = process_batch(prompts, llm, sampling_params)
    ratings = [get_rating(result) for result in llm_answers]
    for result, rating in zip(results, ratings):
        print(result[0]['title'], result[0]['source'], rating)