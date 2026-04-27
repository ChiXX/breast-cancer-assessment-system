import os
import re
import json
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
    history: Optional[List[Dict[str, Any]]] = []

from mcp.agents.schemas import RiskLevel

class EvaluateResponse(BaseModel):
    risk_level: RiskLevel
    action_required: Optional[str] = None
    ctcae_grade: Optional[str] = None
    advice: str
    contact_team: bool
    evidence: str
    rule_id: str
    display_text: str = ""
    id: Optional[int] = None # For DB reference if needed

class MemoryItem(BaseModel):
    clue: str
    summary: str
    learned: bool

class MemoryStoreRequest(BaseModel):
    session_id: str
    history: List[Dict[str, Any]]

class SessionResponse(BaseModel):
    memories: List[MemoryItem]

class KnowledgeLearnResponse(BaseModel):
    status: str

# --- Helpers ---

def parse_agent_response(text: str) -> EvaluateResponse:
    """
    Parses the JSON response from MedicalMaster.
    """
    try:
        # LLMs sometimes wrap JSON in code blocks
        json_str = text
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0].strip()
        
        data = json.loads(json_str)
        
        if data.get("type") == "evaluation":
            eval_data = data.get("data", {})
            advice = eval_data.get("advice", "")
            display_text = data.get("display_text", "")
            
            # If display_text is just a repeat of advice, or empty, handle it
            if not display_text or display_text == advice:
                display_text = "根据您的描述，我们为您整理了以下评估结果：" if not display_text else display_text

            return EvaluateResponse(
                risk_level=eval_data.get("risk_level", "未知"),
                action_required=eval_data.get("action_required"),
                ctcae_grade=eval_data.get("ctcae_grade"),
                advice=advice,
                contact_team=eval_data.get("contact_team", False),
                evidence=eval_data.get("evidence", ""),
                rule_id=eval_data.get("rule_id", ""),
                display_text=display_text
            )
        elif data.get("type") == "question":
            content = data.get("content", "")
            display_text = data.get("display_text", "")
            return EvaluateResponse(
                risk_level=RiskLevel.UNKNOWN,
                advice=content,
                contact_team=False,
                evidence="",
                rule_id="",
                display_text=display_text if display_text != content else ""
            )
        else:
            # Fallback or RAG direct output
            advice = data.get("advice", text)
            display_text = data.get("display_text", "")
            return EvaluateResponse(
                risk_level=data.get("risk_level", RiskLevel.UNKNOWN),
                advice=advice,
                contact_team=data.get("contact_team", False),
                evidence=data.get("evidence", ""),
                rule_id=data.get("rule_id", ""),
                display_text=display_text if display_text != advice else ""
            )
            
    except Exception as e:
        print(f"DEBUG: JSON parse failed, falling back to legacy regex. Error: {e}")
        # Legacy regex parsing as fallback
        risk_level = "未知"
        advice = text
        contact_team = False
        evidence = ""
        rule_id = ""

        risk_match = re.search(r"风险等级\s*\**\s*[：:]\s*(.*)", text)
        advice_match = re.search(r"下一步建议\s*\**\s*[：:]\s*(.*)", text)
        contact_match = re.search(r"是否建议联系团队\s*\**\s*[：:]\s*(.*)", text)
        evidence_match = re.search(r"(?:简单依据说明|参考依据和说明)\s*\**\s*[：:]\s*(.*)", text)
        rule_id_match = re.search(r"参考依据ID\s*\**\s*[：:]\s*([A-Za-z0-9_-]+)", text)

        if risk_match:
            risk_raw = risk_match.group(1).split('\n')[0].strip()
            risk_level = RiskLevel.HIGH if "高" in risk_raw else RiskLevel.MEDIUM if "中" in risk_raw else RiskLevel.LOW if "低" in risk_raw else risk_raw

        if advice_match:
            advice_text = advice_match.group(1)
            next_header = re.search(r"\n\s*[-*]\s+\*\*|是否建议联系团队|简单依据说明|参考依据ID|参考依据和说明", advice_text)
            advice = advice_text[:next_header.start()].strip() if next_header else advice_text.strip()
        
        if contact_match:
            contact_val = contact_match.group(1).split('\n')[0].strip().lower()
            contact_team = any(word in contact_val for word in ["是", "yes", "true", "建议"])
        
        if evidence_match:
            evidence_text = evidence_match.group(1)
            next_header = re.search(r"\n\s*[-*]\s+\*\*|参考依据ID", evidence_text)
            evidence = evidence_text[:next_header.start()].strip() if next_header else evidence_text.strip()
                
        if rule_id_match:
            rule_id = rule_id_match.group(1).strip()

        return EvaluateResponse(
            risk_level=risk_level,
            advice=advice,
            contact_team=contact_team,
            evidence=evidence,
            rule_id=rule_id,
            display_text=text
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
    print(f"DEBUG: Received evaluate request for session {request.session_id}")
    print(f"DEBUG: User Input: {request.user_input}")
    print(f"DEBUG: History Length: {len(request.history or [])}")
    try:
        response_text = master_agent.chat(
            request.user_input, 
            session_id=request.session_id,
            history=request.history
        )
        print(f"DEBUG: Full Agent Response Text:\n{response_text}")
        parsed_response = parse_agent_response(response_text)
        print(f"DEBUG: Parsed EvaluateResponse: {parsed_response}")
        return parsed_response
    except Exception as e:
        print(f"DEBUG: Error in evaluate: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from mcp.agents.memory_agent import MemoryAgent
memory_agent = MemoryAgent()

@app.post("/v1/memory/store")
async def store_memory(request: MemoryStoreRequest, background_tasks: BackgroundTasks):
    """
    触发记忆压缩与存储。
    """
    background_tasks.add_task(memory_agent.process_session, request.session_id, request.history)
    return {"status": "success"}

@app.get("/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    还原会话记忆线索。
    """
    try:
        memory_list_tool = ReadMemoryList()
        res = memory_list_tool.call({})
        
        memories = []
        
        if res.get('status') == 'success':
            all_memories = res.get('memories', [])
            # Filter for this session_id
            session_memories = [m for m in all_memories if m.get('session_id') == session_id]
            
            detail_tool = ReadMemoryDetail()
            for m in session_memories:
                # Get detail for summary
                detail_res = detail_tool.call({
                    'session_id': session_id,
                    'timestamp': m['timestamp']
                })
                
                summary = "暂无总结"
                if detail_res.get('status') == 'success':
                    try:
                        mem_data = json.loads(detail_res.get('content', '{}'))
                        summary = mem_data.get('summary', summary)
                    except:
                        pass
                
                memories.append(MemoryItem(
                    clue=m['title'],
                    summary=summary,
                    learned=m.get('learned', False)
                ))
                
        return SessionResponse(memories=memories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/knowledge/learn", response_model=KnowledgeLearnResponse)
async def learn_knowledge(background_tasks: BackgroundTasks):
    """
    异步触发学习与审查流水线。
    """
    background_tasks.add_task(learning_agent.run, force=True)
    return KnowledgeLearnResponse(status="processing")

@app.get("/v1/memory/all")
async def get_all_memories():
    """
    获取所有已归档的记忆。
    """
    try:
        memory_list_tool = ReadMemoryList()
        res = memory_list_tool.call({})
        if res.get('status') == 'success':
            return res.get('memories', [])
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
