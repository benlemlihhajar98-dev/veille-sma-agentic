
import os
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -----------------------------------
# Chargement des documents
# -----------------------------------

documents = []

docs_path = "internal_docs"

for file in os.listdir(docs_path):

    if file.endswith(".txt"):

        loader = TextLoader(
            os.path.join(docs_path, file),
            encoding="utf-8"
        )

        documents.extend(loader.load())

print(f"{len(documents)} documents chargés.")

# -----------------------------------
# Chunking
# -----------------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50
)

chunks = splitter.split_documents(documents)

print(f"{len(chunks)} chunks créés.")

# -----------------------------------
# Chargement du modèle MiniLM
# -----------------------------------

print("Chargement du modèle MiniLM...")

model = SentenceTransformer('all-MiniLM-L6-v2')

# -----------------------------------
# Préparation des textes
# -----------------------------------

chunk_texts = [chunk.page_content for chunk in chunks]

# -----------------------------------
# Génération des embeddings
# -----------------------------------

embeddings = model.encode(chunk_texts)

print("Embeddings générés avec succès.")

# -----------------------------------
# Fonction de recherche
# -----------------------------------

def search_internal_knowledge(question: str) -> dict:
    """Retourne un dict structuré pour que HAJAR/WAFAE puissent l'utiliser."""

    question_embedding = model.encode([question])
    scores = cosine_similarity(question_embedding, embeddings)[0]

    # Top 3 résultats (pas juste le meilleur)
    top_indices = scores.argsort()[-3:][::-1]

    results = []
    for idx in top_indices:
        results.append({
            "score":   round(float(scores[idx]), 4),
            "source":  chunks[idx].metadata.get("source", "inconnu"),
            "content": chunks[idx].page_content,
        })

    return {
        "question": question,
        "best_score": results[0]["score"],
        "best_source": results[0]["source"],
        "best_content": results[0]["content"],
        "all_results": results,
    }

# -----------------------------------
# Question utilisateur
# -----------------------------------

question = input("\nPosez votre question : ")

search_internal_knowledge(question)