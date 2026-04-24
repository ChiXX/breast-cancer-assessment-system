# MCP Agent Specification

## 1. 核心 Agent: MedicalMaster

### 定位
作为系统的“大脑”，负责接收用户输入，提取医疗实体（症状、时长、程度等），并根据决策逻辑（L1 Skill -> L2 RAG）调度执行，最后汇总结果反馈给用户。

### 技术选型
- **框架**: `qwen_agent.agents.Assistant`
- **底座模型**: `qwen3.5-plus` (DashScope API via OpenAI-compatible endpoint)
- **输入**: 用户自然语言文本
- **输出**: 评估报告、红旗信号提示、随访建议

### 职责
1. **多轮对话管理**: 维护会话上下文，确保医疗问询的连贯性。
2. **意图路由**: 识别用户当前处于“症状汇报”、“建议咨询”还是“紧急求助”状态。
3. **工具链编排**:
   - **元数据注入**: 初始化时将所有 `SKILL.md` 的 YAML 头（name, description）注入 System Prompt。
   - `read_skill`: 查阅指定技能的完整执行手册（SKILL.md 内容）。
   - `rag_query_tool`: 当现有技能无法覆盖用户需求时，调用 RAG 查询知识库。

## 2. 可观测性 (LangSmith)

### 监控目标
- **Trace ID**: 全链路追踪每一次用户请求。
- **Agent 决策链**: 记录 `System Prompt`、`Tool Calls`、`Tool Outputs`。
- **Token 统计**: 监控各阶段的输入输出成本。

### 实现方案
- **装饰器注入**: 在 `MedicalMaster.run` 或其主入口函数上使用 `@langsmith.traceable`。
- **环境配置**: 必须在运行环境中设置 `LANGCHAIN_TRACING_V2=true` 和 `LANGCHAIN_API_KEY`。

## 3. 文件结构
- `mcp/agents/master.py`: 定义 `MedicalMaster` 类及其核心逻辑。
- `mcp/agent.py`: 服务的启动入口，集成 TUI 或 FastAPI 调用。
