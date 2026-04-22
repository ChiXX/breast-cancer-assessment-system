import json
import os
import pickle
import numpy as np
import faiss
import dashscope
from dashscope import TextEmbedding
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# Configuration
DATA_PATH = Path("mcp/data/rag_documents.json")
VECTOR_STORE_DIR = Path("mcp/data/vector_store")
INDEX_PATH = VECTOR_STORE_DIR / "index.faiss"
DOC_MAP_PATH = VECTOR_STORE_DIR / "doc_map.pkl"

def build_index():
    # Ensure output directory exists
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load documents
    if not DATA_PATH.exists():
        print(f"Error: Data file {DATA_PATH} not found.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    documents = data.get("documents", [])
    if not documents:
        print("No documents found to index.")
        return

    # 2. Text Synthesis & 3. Embedding
    texts = []
    doc_map = {}
    
    for i, doc in enumerate(documents):
        # Concatenate category + keywords + questions
        synthesis_text = f"{doc.get('category', '')} "
        synthesis_text += " ".join(doc.get("symptom_keywords", [])) + " "
        synthesis_text += " ".join(doc.get("questions", []))
        
        texts.append(synthesis_text)
        doc_map[i] = doc

    print(f"Generated {len(texts)} synthesis texts. Requesting embeddings...")

    # Call DashScope API in batches (v3 limit is 10)
    batch_size = 10
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = TextEmbedding.call(
            model=TextEmbedding.Models.text_embedding_v3,
            input=batch
        )

        if resp.status_code != 200:
            print(f"Error calling DashScope at batch {i}: {resp.code} - {resp.message}")
            import sys
            sys.exit(1)
        
        batch_embeddings = [record['embedding'] for record in resp.output['embeddings']]
        all_embeddings.extend(batch_embeddings)

    embeddings_np = np.array(all_embeddings).astype('float32')

    # 4. Storage (FAISS)
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)

    # Save FAISS index
    faiss.write_index(index, str(INDEX_PATH))

    # Save Doc Map
    with open(DOC_MAP_PATH, "wb") as f:
        pickle.dump(doc_map, f)

    print(f"Index built successfully. Saved to {VECTOR_STORE_DIR}")

if __name__ == "__main__":
    build_index()
