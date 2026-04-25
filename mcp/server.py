import os
import re
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from mcp.agents.master import MedicalMaster
from mcp.agents.tools import get_all_skill_metadata
from mcp.agents.tools.memory_tools import ReadMemoryList, ReadMemoryDetail
from mcp.agents.learning_agent import LearningAgent
from mcp.agents.config import MASTER_MODEL, get_llm_cfg

app = FastAPI(title="Breast Cancer Side Effect Assessment System MCP")

# --- Models ---

class EvaluateRequest(BaseModel):
    user_input: str
    session_id: str
    history: Optional[List[Dict[str, str]]] = []

class EvaluateResponse(BaseModel):
    risk_level: str
    advice: str
    contact_team: bool
    evidence: str
    rule_id: str

class MemoryItem(BaseModel):
    clue: str
    summary: str
    learned: bool

class SessionResponse(BaseModel):
    memories: List[MemoryItem]
    context: str

class KnowledgeLearnResponse(BaseModel):
    status: str

# --- Helpers ---

def parse_agent_response(text: str) -> EvaluateResponse:
    """
    Parses the structured response from MedicalMaster.
    """
    risk_level = "未知"
    advice = text
    contact_team = False
    evidence = ""
    rule_id = ""

    # Patterns for extraction - supporting both full-width and half-width colons, and markdown bolding
    risk_match = re.search(r"风险等级\s*\**\s*[：:]\s*(.*)", text)
    advice_match = re.search(r"下一步建议\s*\**\s*[：:]\s*(.*)", text)
    contact_match = re.search(r"是否建议联系团队\s*\**\s*[：:]\s*(.*)", text)
    evidence_match = re.search(r"参考依据和说明\s*\**\s*[：:]\s*(.*)", text)

    if risk_match:
        risk_level = risk_match.group(1).split('\n')[0].strip()
    
    if advice_match:
        # Advice might span multiple lines until the next header
        advice_text = advice_match.group(1)
        next_header = re.search(r"\n\s*[-*]\s+\*\*|是否建议联系团队|参考依据和说明", advice_text)
        if next_header:
            advice = advice_text[:next_header.start()].strip()
        else:
            advice = advice_text.strip()
    
    if contact_match:
        contact_val = contact_match.group(1).split('\n')[0].strip().lower()
        contact_team = any(word in contact_val for word in ["是", "yes", "true", "建议"])
    
    if evidence_match:
        evidence = evidence_match.group(1).strip()
        # Extract rule_id from evidence if present (e.g., [ID: 001] or QA-M-005)
        rule_id_match = re.search(r"ID\s*[：:]\s*([A-Za-z0-9_-]+)|(QA-[A-Z]-[0-9]+)", evidence)
        if rule_id_match:
            rule_id = next(g for g in rule_id_match.groups() if g is not None)

    return EvaluateResponse(
        risk_level=risk_level,
        advice=advice,
        contact_team=contact_team,
        evidence=evidence,
        rule_id=rule_id
    )

# --- State ---
# In a real app, we might use a dependency or a more robust way to manage agent state
master_agent = MedicalMaster()
learning_agent = LearningAgent(llm_cfg=get_llm_cfg(MASTER_MODEL))

# --- Endpoints ---

@app.post("/v1/evaluate", response_model=EvaluateResponse)
async def evaluate(request: EvaluateRequest):
    """
    接收症状描述，返回 Agent 决策结果。
    """
    try:
        response_text = master_agent.chat(
            request.user_input, 
            session_id=request.session_id,
            history=request.history
        )
        return parse_agent_response(response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    还原会话记忆线索。
    """
    try:
        memory_list_tool = ReadMemoryList()
        res = memory_list_tool.call({})
        
        memories = []
        context_parts = []
        
        if res.get('status') == 'success':
            all_memories = res.get('memories', [])
            # Filter for this session_id
            session_memories = [m for m in all_memories if m.get('session_id') == session_id]
            
            detail_tool = ReadMemoryDetail()
            for m in session_memories:
                # Get detail for context
                detail_res = detail_tool.call({
                    'session_id': session_id,
                    'timestamp': m['timestamp']
                })
                if detail_res.get('status') == 'success':
                    mem_content = detail_res.get('content', '')
                    context_parts.append(f"### {m['title']} ({m['timestamp']})\n{mem_content}")
                
                memories.append(MemoryItem(
                    clue=m['title'],
                    summary=m.get('summary', '暂无总结'), # ReadMemoryList doesn't return summary, but we could fetch it if needed
                    learned=m.get('learned', False)
                ))
                
        return SessionResponse(memories=memories, context="\n\n".join(context_parts))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/knowledge/learn", response_model=KnowledgeLearnResponse)
async def learn_knowledge(background_tasks: BackgroundTasks):
    """
    异步触发学习与审查流水线。
    """
    background_tasks.add_task(learning_agent.run, force=True)
    return KnowledgeLearnResponse(status="processing")

@app.get("/v1/knowledge/skills")
async def get_skills():
    """
    列出当前生效的所有评估规则索引。
    """
    try:
        skills = get_all_skill_metadata()
        return skills
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
