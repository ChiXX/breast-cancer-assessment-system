import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Iterator, Optional
from langsmith import traceable
from mcp.agents.base import BaseMedicalAgent
from mcp.agents.config import EXPERT_MODEL, get_llm_cfg
from dashscope import TextEmbedding
from qwen_agent.tools.base import BaseTool, register_tool
from typing import Union

class RAGAgent(BaseMedicalAgent):
    """
    RAGAgent is a specialized medical knowledge agent.
    It uses the rag_query_tool to retrieve information from medical guidelines.
    """
    
    def __init__(self, llm_cfg: Optional[dict] = None, name: str = 'RAG_Expert'):
        llm_cfg = llm_cfg or get_llm_cfg(EXPERT_MODEL)
        
        
        system_prompt = (
            f"你是一个专业的乳腺癌副作用评估专家。你的职责是调用 'rag_vector_search_tool' 检索指南，并严格按 JSON 格式回答。\n\n"
            f"### 【评估标准映射】\n"
            "1. **HIGH** + **立即线下就医** + **Grade 1**\n"
            "2. **HIGH** + **24小时内联系团队** + **Grade 2**\n"
            "3. **MEDIUM** + **联系团队** + **Grade 3**\n"
            "4. **MEDIUM** + **密切观察** + **Grade 4**\n"
            "5. **LOW** + **继续观察与记录** + **Grade 5**\n\n"
            "### 输出格式：\n"
            "```json\n"
            "{\n"
            "  \"risk_level\": \"HIGH\",\n"
            "  \"action_required\": \"立即线下就医\",\n"
            "  \"ctcae_grade\": \"Grade 1\",\n"
            "  \"advice\": \"建议立即前往急诊...\",\n"
            "  \"contact_team\": true,\n"
            "  \"evidence\": \"根据 CTCAE v5.0 指南...\",\n"
            "  \"rule_id\": \"QA-H-001\"\n"
            "}\n"
            "```\n"
            "原则：\n"
            "- `rag_vector_search_tool` 每次会召回 3 个候选答案。你的核心任务是判断召回的内容中是否有可以回答患者问题的。\n"
            "- 必须选择**最相关的一个**答案作为依据进行评估，**严禁融合多个答案**的内容。\n"
            "- 必须基于选出的这单一检索结果进行判断，禁止凭空捏造，将多个答案进行融合。\n"
            "- 如果检索工具未返回相关内容，或 3 个答案都无法支持判断，必须回复：`{\"status\": \"not_found\"}`。"
        )
        
        super().__init__(
            llm_cfg=llm_cfg,
            name=name,
            system_prompt=system_prompt,
            tools=['rag_vector_search_tool']
        )

    @traceable(name="RAGAgent Run")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Run the RAG agent with messages.
        """
        for chunk in self.agent.run(messages):
            yield chunk

    @traceable(name="RAGAgent Chat")
    def chat(self, user_input: str, history: Optional[List[dict]] = None) -> str:
        """
        Synchronous chat helper.
        """
        return super().chat(user_input, history)


VECTOR_STORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vector_store')
INDEX_PATH = f"{VECTOR_STORE_DIR}/index.faiss"
DOC_MAP_PATH = f"{VECTOR_STORE_DIR}/doc_map.pkl"

@register_tool('rag_vector_search_tool')
class RAGVectorSearchTool(BaseTool):
    description = 'Query the local FAISS medical guidelines index for side effect assessment and advice.'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': 'The medical symptom or condition to query'
            }
        },
        'required': ['query']
    }

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.index = None
        self.doc_map = None
        if os.path.exists(INDEX_PATH) and os.path.exists(DOC_MAP_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            with open(DOC_MAP_PATH, "rb") as f:
                self.doc_map = pickle.load(f)

    @traceable(name="RAG Vector Search Tool Call")
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
            from mcp.utils.event_logger import eventlog
            eventlog("RAG_QUERY", f"Querying Guidelines: {query}", {"query": query})
            resp = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v3,
                input=[query]
            )
            if resp.status_code != 200:
                eventlog("ERROR", f"Embedding error: {resp.message}", {"query": query, "error": resp.message})
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
                        "contact_team": doc.get('contact_team', doc.get('risk_level') in ['HIGH', 'MEDIUM']),
                        "rule_id": doc.get('id')
                    })
            
            if not results:
                eventlog("RAG_QUERY", f"No relevant results found for: {query}", {"query": query, "status": "not_found"})
                return json.dumps({"status": "not_found", "message": "No relevant information found."}, ensure_ascii=False)
            
            return json.dumps(results, ensure_ascii=False, indent=2)
            
        except Exception as e:
            from mcp.utils.event_logger import eventlog
            eventlog("ERROR", f"Error during query: {str(e)}", {"query": query, "exception": str(e)})
            return f"Error during query: {str(e)}"
