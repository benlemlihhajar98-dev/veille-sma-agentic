
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

def search_internal_knowledge(question):

    print("\nQuestion :", question)

    # Vectorisation de la question
    question_embedding = model.encode([question])

    # Calcul des similarités
    scores = cosine_similarity(
        question_embedding,
        embeddings
    )[0]

    # Meilleur résultat
    best_index = np.argmax(scores)

    best_score = scores[best_index]

    best_chunk = chunks[best_index]

    # Affichage
    print("\n--- MEILLEUR RÉSULTAT ---")
    print(f"Score : {best_score:.4f}")

    print("\nContenu :")
    print(best_chunk.page_content)

    print("\nSource :")
    print(best_chunk.metadata.get("source"))

# -----------------------------------
# Question utilisateur
# -----------------------------------

question = input("\nPosez votre question : ")

search_internal_knowledge(question)