import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from mcp.agents.tools import get_all_skill_metadata
from mcp.agents.tools.memory_tools import ReadMemoryList, ReadMemoryDetail

from mcp.scripts.schemas import (
    EvaluateRequest, 
    EvaluateResponse, 
    MemoryItem, 
    MemoryStoreRequest, 
    SessionResponse, 
    KnowledgeLearnResponse
)
from mcp.scripts.parser import parse_agent_response
from mcp.scripts.agents import master_agent, learning_agent, memory_agent

app = FastAPI(title="Breast Cancer Side Effect Assessment System MCP")

# --- Endpoints ---

@app.post("/v1/evaluate", response_model=EvaluateResponse)
async def evaluate(request: EvaluateRequest):
    """
    接收症状描述，返回 Agent 决策结果。
    """
    print(f"DEBUG: Received evaluate request for session {request.session_id}")
    try:
        response_text = master_agent.chat(
            request.user_input, 
            session_id=request.session_id,
            history=request.history
        )
        parsed_response = parse_agent_response(response_text)
        return parsed_response
    except Exception as e:
        print(f"DEBUG: Error in evaluate: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
    background_tasks.add_task(learning_agent.start_learning, force=True)
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
