# MCP Agent Specification

## 1. 核心 Agent: MedicalMaster

### 定位
作为系统的“中控客服”，基于 `Assistant` 架构。负责作为患者与专家系统间的桥梁，进行初步接待、意图识别、资源调度与结果汇总。

### 技术选型
- **框架**: `qwen_agent.agents.Assistant` (使用 Tool-based 模式调用子 Agent)
- **主要工具**: 
  - `RAG_Expert`: 包装了 RAGAgent 的工具，负责获取指南。
  - `read_skill`: 查阅评估技能执行手册（SKILL.md）。
  - `read_memory_list`: 获取所有历史记忆线索（标题+时间）。
  - `read_memory_detail`: 按量查阅某条记忆的详细对话内容。

### 职责
1. **中控调度**: 识别症状，优先检查系统提示词中的“历史记忆线索”。
2. **记忆优先**: 如果历史记忆线索中有可参考回答，优先调用 `read_memory_detail` 查阅详情，避免重复调用 `RAG_Expert`。
3. **极简追问**: 根据 `symptom_followup` 技能，在信息缺失时进行单句、单点的极简追问。
4. **信息汇总**: 原样转达专家评估结果或历史记忆中的核心结论。

---

## 2. 专家 Agent: RAGAgent (RAG_Expert)

### 定位
医疗知识专家，专门负责通过 RAG 工具检索权威指南并给出分级建议。

### 技术选型
- **框架**: `qwen_agent.agents.Assistant`
- **工具**: `rag_query_tool` (对接本地 FAISS 向量库)

### 职责
1. **结构化输出**: 严格按以下格式输出：风险等级、下一步建议、是否建议联系团队、依据说明、参考ID。
2. **确定性逻辑**: 检索不到结果时必须回答“不清楚”，禁止幻觉。

---

## 3. 记忆 Agent: MemoryAgent

### 定位
记忆管理专家，负责在会话结束或接到指令时，对对话进行结构化总结与持久化。

### 存储规范
- **路径**: `mcp/agents/memory/{session_id}/{YYYY-MM-DD_HH-MM-SS}.md`
- **标题格式 (Clue)**: `[核心症状/问题] - [当前状态/阶段] - [关键处置/动作]`
- **内容结构**: 
  - 1. 一级标题 (Clue)
  - 2. 一句话极简总结 (Summary)
  - 3. 分隔符 `---`
  - 4. 全文对话记录

---

## 4. 评估技能 (Skills)

### 核心技能: `symptom_followup`
- **约束**: 信息足够（3要素齐全）时严禁追问；每次追问仅限一句话；两轮封顶。

---

## 5. 可观测性 (LangSmith)

- **全链路追踪**: 使用 `@traceable` 装饰器覆盖 Master、Sub-Agent 及关键 Tool。

---

## 6. 文件结构
- `mcp/agents/master.py`: `MedicalMaster` (中控)
- `mcp/agents/memory_agent.py`: `MemoryAgent` (记忆管理)
- `mcp/agents/memory/`: 结构化记忆 Markdown 存储目录
- `mcp/agents/rag_agent.py`: `RAGAgent` (专家)
- `mcp/agents/tools/`: 
  - `rag_tool.py`: RAG 检索工具
  - `skill_tools.py`: 技能查阅工具
  - `memory_tools.py`: 记忆读写与列表提取工具
