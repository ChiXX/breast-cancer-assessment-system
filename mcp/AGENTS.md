# MCP Server — AGENTS.md

> 继承根目录 `AGENTS.md` 全局约束。本文件是 MCP 模块入口（~50 行），详细契约见 `spec.md`。

## 定位

症状输入 → MedicalMaster (Assistant) 调度 → RAG_Expert (评估) + read_skill (追问) → 结构化建议。

## 核心约束

| 约束 | 规则 |
|------|------|
| **中控架构** | 使用 `MedicalMaster` 作为统一入口，禁止跳过中控直接调用专家。 |
| **强制 RAG** | 只要涉及医疗症状，必须调用 `RAG_Expert`。 |
| **追问约束** | 单句提问，单点切入，总追问次数严禁超过 2 次。 |
| **原样转达** | 中控必须完整、原样展示 `RAG_Expert` 的输出（包含风险等级与参考 ID）。 |
| **无状态** | Agent 实例通过历史消息链维护上下文，不持有本地持久化状态。 |
| **可观测性** | 强制集成 LangSmith，追踪决策链与工具调用。 |

## 启动

```bash
# 运行 TUI 测试
source .venv/bin/activate
uv run python mcp/agent.py
```

## 导航

| 路径 | 说明 |
|------|------|
| [spec.md](spec.md) | 架构协议、Agent 职责、工具 Schema |
| `agents/` | 核心逻辑层 |
| ├── `master.py` | MedicalMaster (中控/Assistant) |
| ├── `rag_agent.py` | RAGAgent (专家/Assistant) |
| ├── `skills/` | 声明式技能层 (包含 `symptom_followup/SKILL.md`) |
| └── `tools/` | 程序化工具层 (rag_tool.py, skill_tools.py) |
| `data/` | 知识库与 FAISS 索引目录 |
| `agent.py` | TUI 交互入口 |
| `../.env` | API Key 配置 |
