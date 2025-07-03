import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance
from typing import List
from pathlib import Path

# Load environment variables
load_dotenv()

# ------------------------------------
# CONFIGURATION
# ------------------------------------
QDRANT_URL = os.getenv("QDRANT_URL").strip('"') if os.getenv("QDRANT_URL") else None
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "jurisol-legal-embeddings"
VECTOR_SIZE = 1024  #lace with your mistral_embed output dimension

# Directory containing all 6 JSON law files
LAW_FILES_DIR = os.path.join(os.path.dirname(__file__), "Law Bare Acts Json")

# ------------------------------------
# Connect to Qdrant
# ------------------------------------
print(f"Connecting to Qdrant at: {QDRANT_URL}")
try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print("Successfully connected to Qdrant")
except Exception as e:
    print(f"Error connecting to Qdrant: {str(e)}")
    raise


# --- AUTONOMOUS: SCAN ALL FILES FOR METADATA KEYS ---
all_keys = set()

law_dir = Path(LAW_FILES_DIR)
for file in law_dir.glob("*.json"):
    try:
        with open(file, encoding="utf-8") as f:
            docs = json.load(f)
            for doc in docs:
                all_keys.update(doc.keys())
    except Exception as e:
        print(f"Error reading {file.name}: {e}")
print(f"Discovered metadata fields: {sorted(all_keys)}")

# --- DELETE AND RECREATE COLLECTION WITH ALL INDEXES ---
try:
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"Deleted old collection: {COLLECTION_NAME}")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )
    # Add payload indexes for all fields
    for k in all_keys:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=k,
                field_schema="keyword"
            )
        except Exception as e:
            print(f"Error creating index for {k}: {e}")
    print(f"Recreated collection: {COLLECTION_NAME} with keyword indexes for fields: {sorted(all_keys)}")
except Exception as e:
    print(f"Error creating collection: {str(e)}")
    raise

# ------------------------------------
# Your embedding model
# ------------------------------------


from langchain_mistralai import MistralAIEmbeddings

embeddings_model = MistralAIEmbeddings(
    model="mistral-embed",
    mistral_api_key=os.getenv("MISTRAL_API_KEY")
)

def mistral_embed(text: str) -> List[float]:
    """Generate embeddings using Mistral's embedding model."""
    try:
        # Get embeddings from Mistral API via LangChain
        embedding = embeddings_model.embed_query(text)
        return embedding
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        raise

# ------------------------------------
# Utility to ingest one JSON file
# ------------------------------------

# ------------------------------------
# Utility to ingest one JSON file (per law)
# ------------------------------------


def ingest_json_file(file_path: Path, start_id=1):
    print(f"\nProcessing file: {file_path.name}")
    with open(file_path, 'r', encoding='utf-8') as f:
        law_sections = json.load(f)
    BATCH_SIZE = 50 # small batches to be gentle to the embedding LLM
    total_sections = len(law_sections)
    next_id = start_id
    for i in range(0, total_sections, BATCH_SIZE):
        batch = law_sections[i:i+BATCH_SIZE]
        points = []
        for section in batch:
            # Use all key-value pairs for embedding text
            section_text = " | ".join(f"{k}: {v}" for k, v in section.items())
            vector = mistral_embed(section_text)
            payload = {k: str(v) if not isinstance(v, str) else v for k, v in section.items()}
            points.append({
                "id": next_id,
                "vector": vector,
                "payload": payload
            })
            next_id += 1
        print(f"Uploading batch {i//BATCH_SIZE + 1} ({len(points)} vectors) from {file_path.name}...")
        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
        # Wait 2 seconds between batches to avoid overloading the embedding LLM
        import time
        time.sleep(2)
    return next_id

# ------------------------------------
# Process all 6 files
# ------------------------------------

def process_all_laws():
    law_dir = Path(LAW_FILES_DIR)
    next_id = 1
    for file in law_dir.glob("*.json"):
        next_id = ingest_json_file(file, start_id=next_id)

# Run the full ingestion
if __name__ == "__main__":
    process_all_laws()
    print("✅ All law files embedded and uploaded to Qdrant.")
