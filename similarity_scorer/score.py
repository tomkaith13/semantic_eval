from sentence_transformers import SentenceTransformer, util

# Load a pre-trained model
# model = SentenceTransformer('all-MiniLM-L6-v2')
model = SentenceTransformer("all-mpnet-base-v2")

# Define two example strings
text1 = "A cat is sitting on a rug."
text2 = "A feline is resting on a mat."
text3 = "The car is parked outside."


def score_similarity(str1=text1, str2=text2):
    # Generate embeddings for the strings
    embedding1 = model.encode(str1, convert_to_tensor=True)
    embedding2 = model.encode(str2, convert_to_tensor=True)

    # Compute cosine-similarity score
    cosine_score = util.pytorch_cos_sim(embedding1, embedding2)
    print(f"Similarity score between '{str1}' and '{str2}': {cosine_score.item():.4f}")
    return cosine_score.item()
