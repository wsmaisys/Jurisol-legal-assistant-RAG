import os
from dotenv import load_dotenv
load_dotenv()

from langchain_mistralai import MistralAIEmbeddings
import chromadb
from chromadb.config import Settings



# Chroma vector store path
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_legal_index")

embeddings_model = MistralAIEmbeddings(model="mistral-embed", mistral_api_key=os.getenv("MISTRAL_API_KEY"))

def chroma_search_with_score(query: str, top_k: int = 5, metadata_filter: dict = None):
    """
    Search the Chroma vector store for relevant legal documents and provisions, returning relevance scores.
    """
    # Get embedding for the query
    query_embedding = embeddings_model.embed_query(query)
    # Connect to ChromaDB persistent client
    client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(allow_reset=True))
    collection = client.get_or_create_collection("langchain")
    # Prepare filter
    where = metadata_filter if metadata_filter else None
    # Query ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"]
    )
    # Return raw results from ChromaDB
    return results


# Example usage:
if __name__ == "__main__":
    query = "culpable homicide"
    print(f"[TEST] Searching Chroma vector store for: {query}")
    results = chroma_search_with_score(query, top_k=5)
    for i, res in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Content: {res['content']}")
        print(f"Metadata: {res['metadata']}")
        print(f"Relevance Score: {res['relevance_score']:.4f}")

