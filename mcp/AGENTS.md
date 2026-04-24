# MCP Server — AGENTS.md

> 继承根目录 `AGENTS.md` 全局约束。本文件是 MCP 模块入口（~50 行），详细契约见 `spec.md`。

## 定位

症状输入 → Hermes ReAct 三层决策 → 风险等级 + 处置建议 → 会话结束后自动更新知识库。


## 核心约束

| 约束 | 规则 |
|------|------|
| **无状态** | 不持有会话状态，状态由 Backend 管理并传入 |
| **单职责** | 一个工具做一件事，禁止 god-tool |
| **先查后写** | 开发前强制阅读相关文件（如 `agents/orchestrator.py`），严禁在入口文件中重写或内联堆砌已存在的功能模块 |
| **决策顺序** | 优先 `discover_skills` (L1) -> 失败则回退 `RAG` (L2) |
| **LEARN 时机** | 仅在会话结束后由反馈层触发，禁止推理中途调用 |
| **数据只增** | `data/*.json` 只追加，禁止修改已有条目 |
| **可观测性** | 强制集成 LangSmith，追踪 Agent 决策、工具调用及 System Prompt |


## 启动

```bash
cd mcp && uvicorn server:app --port 9001 --reload
```

## 参考文献与知识检索触发器 (Knowledge Triggers)

> **[AI Agent 指令 - 强制执行]** 本表定义的关键词是系统的架构基石。当对话中提及下表关键词时，AI 助手 **必须立即调用网页读取或搜索工具**（优先访问核心 URL），严禁仅凭离线知识进行猜测。查阅到的官方设计理念应作为后续所有代码变更的 **最高指导准则**。

| 触发关键词 | 来源 | 技术指导价值 | 核心 URL |
|------------|------|--------------|----------|
| `hermes`, `多智能体` | **Hermes Agent** | 指导主从 Agent 路由架构、状态打断注入以及 `<tool_call>` 的实现。 | [Link](https://hermes-agent.nousresearch.com/) |
| `skill`, `agent skills`, `原子工具` | **Agent Skills** | 遵循开放式 Skill 规范，指导 `skill-name/SKILL.md` 的文件夹结构与原子化封装。 | [Link](https://github.com/anthropics/anthropic-agent-sdk) |

---

## 导航

| 路径 | 说明 |
|------|------|
| [spec.md](spec.md) | 工具接口、数据 Schema、决策流完整契约 ([文件结构](spec.md#文件结构-file-structure)) |
| `agents/` | 核心逻辑层 |
| ├── `tools/` | 程序化工具层 (包含 `skill_tools`, `orchestrator_tools` 等) |
| ├── `skills/` | 声明式技能层 (L1 Skill，按症状分类的 `SKILL.md` SOP文件) |
| └── `memory/` | 记忆层 (分层存储：T2短对话, T1摘要, T0向量索引) |
| `data/rag_documents.json` | L2 RAG 知识底座 |
| `data/build_index.py` | RAG 建库脚本 |
| `agent.py` | Hermes ReAct 主循环 (`run_agent`) |
| `server.py` | FastAPI 入口 (Port 9001) |
