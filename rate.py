import time
from vllm import LLM, SamplingParams

class DocumentRater:
    def __init__(self, model_name="google/gemma-3-4b-it", dtype="bfloat16", max_model_len=16000):
        self.llm = LLM(model=model_name, dtype=dtype, max_model_len=max_model_len)
        self.sampling_params = SamplingParams(n=1, max_tokens=50, temperature=0.0, top_p=1.0)

    def rate_document(self, article, topic, modifier1, modifier2):
        article = article[:35000]
        prompt_relevance = (
            f"SYSTEM: You are a document rating assistant. Your task is to evaluate the relevance of the provided article "
            f"with respect to the given topic and modifiers. Given the topic '{topic}' and modifiers '{modifier1}' and '{modifier2}', "
            "analyze the content of the article and provide a rating score between 1 (not relevant) and 10 (highly relevant). "
            "Output only the rating, nothing else.\n\n"
            f"Article:\n{article}\n\nRating:"
        )
        outputs_relevance = self.llm.generate([prompt_relevance], self.sampling_params)
        relevance_rating = outputs_relevance[0].outputs[0].text.strip()
        if len(relevance_rating) > 2:
            relevance_rating = "-1"

        prompt_range = (
            f"SYSTEM: You are a document rating assistant. Your task is to determine where the provided article lies on a spectrum "
            f"from '{modifier1}' to '{modifier2}'. Provide a score from 0 to 100 where 50 indicates a neutral position. "
            "Output only the score, nothing else.\n\n"
            f"Article:\n{article}\n\nScore:"
        )
        outputs_range = self.llm.generate([prompt_range], self.sampling_params)
        range_rating = outputs_range[0].outputs[0].text.strip()
        if len(range_rating) > 3:
            range_rating = "-1"

        return relevance_rating, range_rating

    def rate_documents(self, articles, topic, modifier1, modifier2, batch_size=8):
        results = []
        total_articles = len(articles)
        start_time = time.time()
        for i in range(0, total_articles, batch_size):
            batch_articles = [article[:35000] for article in articles[i:i+batch_size]]
            batch_prompts_relevance = [
                f"SYSTEM: You are a document rating assistant. Your task is to evaluate the relevance of the provided article "
                f"with respect to the given topic and modifiers. Given the topic '{topic}' and modifiers '{modifier1}' and '{modifier2}', "
                "analyze the content of the article and provide a rating score between 1 (not relevant) and 10 (highly relevant). "
                "Output only the rating, nothing else.\n\n"
                f"Article:\n{article}\n\nRating:" for article in batch_articles
            ]
            outputs_relevance = self.llm.generate(batch_prompts_relevance, self.sampling_params)
            batch_relevance = [
                output.outputs[0].text.strip() if len(output.outputs[0].text.strip()) <= 2 else "-1"
                for output in outputs_relevance
            ]

            batch_prompts_range = [
                f"SYSTEM: You are a document rating assistant. Your task is to determine where the provided article lies on a spectrum "
                f"from '{modifier1}' to '{modifier2}'. Provide a score from 0 to 100 where 50 indicates a neutral position. "
                "Output only the score, nothing else.\n\n"
                f"Article:\n{article}\n\nScore:" for article in batch_articles
            ]
            outputs_range = self.llm.generate(batch_prompts_range, self.sampling_params)
            batch_range = [
                output.outputs[0].text.strip() if len(output.outputs[0].text.strip()) <= 3 else "-1"
                for output in outputs_range
            ]

            results.extend(zip(batch_relevance, batch_range))
        total_time = time.time() - start_time
        print(f"Processed {total_articles} articles in {total_time:.2f} seconds (avg {(total_time/total_articles):.2f} sec/article)")
        return results

if __name__ == "__main__":
    sample_articles = [
        "Sample article text number 1.",
        "Another sample article text number 2."
    ]
    rater = DocumentRater()
    output = rater.rate_documents(sample_articles, "climate change", "good", "bad")
    print(output)
