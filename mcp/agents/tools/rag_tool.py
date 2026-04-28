import os
import json
import pickle
import numpy as np
import faiss
import dashscope
from dashscope import TextEmbedding
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable
from typing import Union

VECTOR_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'vector_store')
INDEX_PATH = f"{VECTOR_STORE_DIR}/index.faiss"
DOC_MAP_PATH = f"{VECTOR_STORE_DIR}/doc_map.pkl"

@register_tool('rag_query_tool')
class RAGQueryTool(BaseTool):
    description = 'Query the local FAISS medical guidelines index for side effect assessment and advice.'
    parameters = [{
        'name': 'query',
        'type': 'string',
        'description': 'The medical symptom or condition to query',
        'required': True
    }]

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.index = None
        self.doc_map = None
        if os.path.exists(INDEX_PATH) and os.path.exists(DOC_MAP_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            with open(DOC_MAP_PATH, "rb") as f:
                self.doc_map = pickle.load(f)

    @traceable(name="RAG Query Tool Call")
    def call(self, params: Union[str, dict], **kwargs) -> str:
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                query = params
            else:
                query = params.get('query', '')
        else:
            query = params.get('query', '')
            
        if not query:
            return "No query provided."
        
        if not self.index or not self.doc_map:
            return "Knowledge base not initialized or missing."

        try:
            resp = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v3,
                input=[query]
            )
            if resp.status_code != 200:
                return f"Embedding error: {resp.message}"
            
            embedding = resp.output['embeddings'][0]['embedding']
            embedding_np = np.array([embedding]).astype('float32')
            
            # Query top 3
            D, I = self.index.search(embedding_np, 3)
            
            results = []
            for idx in I[0]:
                if idx in self.doc_map:
                    doc = self.doc_map[idx]
                    results.append({
                        "id": doc.get('id', 'N/A'),
                        "risk_level": doc.get('risk_level'),
                        "risk_label": doc.get('risk_label'),
                        "action_required": doc.get('action_required'),
                        "ctcae_grade": doc.get('ctcae_grade'),
                        "advice": doc.get('answer'), # 'answer' in DB is used as advice
                        "rule_id": doc.get('id')
                    })
            
            if not results:
                return json.dumps({"status": "not_found", "message": "No relevant information found."}, ensure_ascii=False)
            
            return json.dumps(results, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"Error during query: {str(e)}"
