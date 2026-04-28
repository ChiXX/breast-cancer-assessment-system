# MCP Server — AGENTS.md

> 继承根目录 `AGENTS.md` 全局约束。本文件是 MCP 模块入口（~50 行），详细契约见 `spec.md`。

## 定位

症状输入 → MedicalMaster (中控) → Skills/Memory (优先检索) → RAG_Expert (保底) → 结构化建议。

## 核心约束

| 约束 | 规则 |
|------|------|
| **中控架构** | 使用 `MedicalMaster` 统一调度。优先查阅 `Skills` 字典，次选最近 `Memory`，最后保底 `RAG`。 |
| **知识闭环** | 零散 Memory 必须经由 `LearningAgent` 提炼为 Skill，且必须通过 `ReviewerAgent` 审计。 |
| **追问约束** | 单句提问，单点切入，总追问次数严禁超过 2 次。严禁在信息齐全时追问。 |
| **原样转达** | 中控必须完整、原样展示专家输出（包含风险等级、建议与参考依据）。 |
| **可观测性** | 集成 LangSmith。`MedicalMaster` 且在 Metadata 中注入 System Prompt。 |

## 启动

```bash
# 运行 TUI 测试
source .venv/bin/activate
uv run python mcp/agent.py
```
```bash
# 运行 MCP
source .venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
uv run python mcp/server.py
```

## 杀死进程
```bash
pkill -f "mcp/server.py"
```

## 导航

| 路径 | 说明 |
|------|------|
| [spec.md](spec.md) | 架构协议、Agent 职责、工具 Schema、检索优先级 |
| `agents/` | 核心逻辑层 |
| ├── `master.py` | MedicalMaster (中控) |
| ├── `rag_agent.py` | RAGAgent (专家) |
| ├── `learning_agent.py` | LearningAgent (知识提炼/提速) |
| ├── `reviewer_agent.py` | ReviewerAgent (合规审计) |
| ├── `memory_agent.py` | MemoryAgent (记忆持久化) |
| ├── `skills/` | 声明式技能层 (症状-风险映射字典) |
| ├── `memory/` | JSON结构化压缩记忆 |
| └── `tools/` | 程序化工具层 (rag_tool.py, skill_tools.py, etc.) |
| `data/` | 知识库与 FAISS 索引目录 |
| `agent.py` | TUI 交互入口 |
| `server.py` | MCP |
