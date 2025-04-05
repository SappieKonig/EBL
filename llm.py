from vllm import LLM, SamplingParams
from prompt_utils import get_rating_prompt, create_bm25_index, search, get_rating


def process_batch(prompts, llm, sampling_params):
    print("Processing batch...")
    # Process all prompts in a single batch
    outputs = llm.generate(prompts, sampling_params)
    
    # Extract results
    results = [output.outputs[0].text for output in outputs]
    return results


if __name__ == "__main__":
    llm = LLM(
        model="google/gemma-3-1b-it",
        dtype="float16",
        gpu_memory_utilization=0.9,  # Slightly reduced
        max_num_batched_tokens=8192,  # Reduced from 16384
        enable_chunked_prefill=True,
        block_size=8,  # Reduced from 16 to 8
        max_num_seqs=128,  # Reduced from 256
    )

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=128,
        top_p=1.0
    )
    top_k = 5

    import json
    with open('recent_news.json', 'r') as f:
        data = json.load(f)

    bm25, tokenized_docs = create_bm25_index(data)
    results = search("tariff", bm25, tokenized_docs, data, top_k=top_k)
    print(results)
    prompts = [get_rating_prompt(result[0], "tariff") for result in results]
    llm_answers = process_batch(prompts, llm, sampling_params)
    ratings = [get_rating(result) for result in llm_answers]
    print(ratings)