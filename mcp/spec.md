# MCP Agent Specification

## 1. 核心 Agent: MedicalMaster (中控)
- **定位**：基于 `Assistant` 架构，负责意图识别、资源调度与结果汇总。
- **配置**：模型选型统一收口至 `mcp/agents/config.py`。
- **风险等级与行动映射**：
  | 风险分级 (risk_level) | 行动建议 (action_required) | CTCAE 级别 (ctcae_grade) | 视觉引导 |
  | :--- | :--- | :--- | :--- |
  | **高风险** (HIGH) | 立即线下就医 | Grade 1 | 红色 + 紧急拨号按钮 |
  | **高风险** (HIGH) | 24小时内联系团队 | Grade 2 | 橙色 + 预约电话按钮 |
  | **中风险** (MEDIUM) | 联系团队 | Grade 3 | 黄色 + 在线咨询按钮 |
  | **中风险** (MEDIUM) | 密切观察 | Grade 4 | 蓝色 + 记录观察按钮 |
  | **低风险** (LOW) | 继续观察与记录 | Grade 5 | 绿色 + 健康日志按钮 |
- **工作准则**：
  1. **检索优先级**：Skills (评估技能) > Memory (未学习记忆) > RAG (专家库)。
  2. **极简原则**：单次追问仅限一个核心点，两轮封顶。
  3. **输出结构**：严格遵循 JSON 格式输出，包含 `type`、`data` 和 `display_text`。
  4. **历史加载**：按需调用 `read_full_history` 工具从后端加载全量历史对话。

## 2. 检索 Agent: RAGAgent (专家)
- **职责**：对接本地 FAISS 向量库，检索权威指南。
- **约束**：输出必须为 JSON 格式，包含参考 ID，无结果回复 `{"status": "not_found"}`，禁止幻觉。

## 3. 记忆 Agent: MemoryAgent (记录)
- **职责**：对对话进行标题级和一句话描述压缩，存为 JSON 格式。
- **存储**：`mcp/agents/memory/{session_id}/{timestamp}.json`，带 `learned: false` 标记，不保留原始全量对话内容。

## 4. 学习 Agent: LearningAgent (进化)
- **职责**：扫描未学习记忆，提取新症状或逻辑，更新 `SKILL.json` 或子资源。
- **触发**：通过 API 手动触发 (`/v1/knowledge/learn`)。

## 5. 审查 Agent: ReviewerAgent (审计)
- **职责**：对 `LearningAgent` 产出的知识进行格式校验与冲突审查。

## 6. FastAPI 接口规范 (Port 9001)

### 6.1 核心评估 (POST `/v1/evaluate`)
- **功能**：接收症状描述，返回 Agent 决策结果。支持多轮对话上下文。
- **输入 (EvaluateRequest)**：
  ```json
  {
    "user_input": "我感觉手麻",
    "session_id": "session_123",
    "history": [
      {"role": "user", "content": "你好"},
      {"role": "assistant", "content": "你好，请问有什么可以帮您？"}
    ] 
  }
  ```
- **输出 (EvaluateResponse)**：由服务器透传或解析 Agent 的 JSON 响应。
  ```json
  {
    "risk_level": "HIGH",
    "action_required": "立即线下就医",
    "ctcae_grade": "Grade 1",
    "advice": "建议进行...",
    "contact_team": true,
    "evidence": "参考依据内容",
    "rule_id": "QA-M-005",
    "display_text": "好的，收到您的问题..."
  }
  ```

### 6.2 会话加载 (GET `/v1/sessions/{session_id}`)
- **功能**：还原会话记忆线索。
- **输出 (SessionResponse)**：
  ```json
  {
    "memories": [
      {
        "clue": "核心症状标题",
        "summary": "一句话极简总结",
        "learned": false
      }
    ],
    "context": "JSON 格式的完整对话记录..."
  }
  ```

### 6.3 知识自进化 (POST `/v1/knowledge/learn`)
- **功能**：异步触发学习与审查流水线（Background Task）。
- **响应**：`{"status": "processing"}`

### 6.4 技能库查询 (GET `/v1/knowledge/skills`)
- **功能**：列出当前生效的所有评估规则元数据（从 SKILL.json 提取）。

## 7. 存储结构
- `mcp/agents/memory/`: 结构化记忆 JSON 存储，按 `session_id` 分包。
- `mcp/agents/skills/`: 原子技能目录，每个目录下包含 `SKILL.json` 及子资源 JSON 文件。
- `mcp/agents/tools/`: 封装好的原子工具集。

## 8. 可观测性 (LangSmith)
- **要求**：所有 Agent 调用与 Tool 使用必须注入 Trace ID，记录系统提示词及模型参数。

