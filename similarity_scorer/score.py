from sentence_transformers import SentenceTransformer, util
from typing import Any

# Load a pre-trained model
# model = SentenceTransformer('all-MiniLM-L6-v2')
model = SentenceTransformer("all-mpnet-base-v2")

# Define two example strings
TEXT_1 = "A cat is sitting on a rug."
TEXT_2 = "A feline is resting on a mat."
TEXT_3 = "The car is parked outside."


def score_similarity(result_ans: str = TEXT_1, golden_ans: str = TEXT_2) -> float:
    # Generate embeddings for the strings
    embedding1 = model.encode(result_ans, convert_to_tensor=True)
    embedding2 = model.encode(golden_ans, convert_to_tensor=True)

    # Compute cosine-similarity score
    cosine_score = util.pytorch_cos_sim(embedding1, embedding2)
    print(
        f"Similarity score between \n Obtained answer: '{result_ans}' \n\nAND\n\n Golden answer: '{golden_ans}' \n\nis\n\n{cosine_score.item():.4f}"
    )
    return float(cosine_score.item())


def rouge_score(result_ans: str = TEXT_1, golden_ans: str = TEXT_2) -> Any:
    from rouge_score import rouge_scorer

    scorer = rouge_scorer.RougeScorer(["rouge1"], use_stemmer=True)
    scores = scorer.score(golden_ans, result_ans)
    return scores
