# MCP Agent Specification

## 1. 核心 Agent: MedicalMaster

### 定位
作为系统的“中控客服”，基于 `Assistant` 架构。负责作为患者与专家系统间的桥梁，进行初步接待、意图识别、资源调度与结果汇总。

### 技术选型
- **框架**: `qwen_agent.agents.Assistant` (使用 Tool-based 模式调用子 Agent)
- **模型控制**: 统一收口至 `mcp/agents/config.py` 进行全局模型选型管理（默认使用 `deepseek-v4-flash`）。
- **主要工具**: 
  - `RAG_Expert`: 包装了 RAGAgent 的工具，负责获取指南建议。
  - `read_skill`: 查阅评估技能执行手册（SKILL.md）。支持资源文件自动检索。
  - `resolve_skill_references`: 解析并读取技能文档中引用的外部资源文件（如 `./neuropathy.md`）。
  - `read_memory_list`: 获取历史记忆线索列表。
  - `read_memory_detail`: 查阅某条记忆的详细对话内容。

### 职责
1. **中控调度**: 识别症状，优先检查系统提示词中的“历史记忆线索”。
2. **记忆优先**: 优先检查“未学习的记忆线索”。如果匹配，调用 `read_memory_detail` 查阅详情，避免重复调用 `RAG_Expert`。
3. **极简追问**: 在评估信息缺失时，进行单句、单点的极简追问。
4. **结果呈现**: 原样转达专家评估结果或 Skill 库内容，严格遵循四段式结构（风险等级、下一步建议、是否建议联系团队、参考依据和说明）。

---

## 2. 检索 Agent: RAGAgent (RAG_Expert)

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

### 技术选型
- **框架**: `qwen_agent.agents.Assistant`
- **主要工具**: 
  - `create_memory`: 将对话总结并持久化为 Markdown 文件。
  - `summarize_memory`: 整合归纳多个历史记忆文档。

### 职责
1. **结构化归档**: 提取会话线索，按 `[核心症状/问题] - [当前状态/阶段] - [关键处置/动作]` 格式生成标题。
2. **闭环管理**: 为 `LearningAgent` 提供高质量的原始语料。

### 存储规范
- **路径**: `mcp/agents/memory/{session_id}/{YYYY-MM-DD_HH-MM-SS}.md`
- **格式**: 包含 YAML Frontmatter，标记 `learned` 状态。
- **标题格式 (Clue)**: `[核心症状/问题] - [当前状态/阶段] - [关键处置/动作]`
- **内容结构**: 
  - YAML Frontmatter (e.g., `learned: false`)
  - 1. 一级标题 (Clue)
  - 2. 一句话极简总结 (Summary)
  - 3. 分隔符 `---`
  - 4. 全文对话记录

---

## 4. 学习 Agent: LearningAgent

### 技术选型
- **框架**: `qwen_agent.agents.Assistant`
- **主要工具**: 
  - `read_memory_list` / `read_memory_detail`: 获取待学习语料。
  - `read_skill` / `resolve_skill_references`: 评估现状。
  - `upsert_skill` / `upsert_skill_resource`: 持久化提炼的知识。
  - `mark_memory_learned`: 标记处理进度。

### 核心逻辑 (Necessity & Superiority)
1. **必要性评估**: 仅当 Memory 包含新症状、更优逻辑或细致标准时才执行更新。
2. **逻辑优选**: 新提炼的专业知识在冲突时具有更高的参考价值。
3. **红线约束**: 严禁记录缺乏明确参考依据（Reference ID）的知识条目。

### 工作流
1. **扫描**: 查找所有 `learned: false` 的内存文件。
2. **触发**: 手动触发 (`/learn`) 或自动触发（未学习文件达到 $N=5$）。
3. **提炼**: 优先更新子资源文件，保持 `SKILL.md` 索引简洁。
4. **审计**: 完成提炼后，自动触发 `ReviewerAgent` 进行合规性与消歧审计。
5. **归档**: 调用 `mark_memory_learned` 标记已处理。

---

## 5. 审查 Agent: ReviewerAgent

### 定位
医疗文档合规性审查员，负责对 `LearningAgent` 生成或更新的知识进行二次审计。

### 技术选型
- **模型**: 使用高效的 Flash 模型（如 `qwen3.6-flash`）。
- **工具**:
  - `verify_skill_format`: 检查资源文件是否具备必需的四个字段，并剔除无依据条目。
  - `resolve_skill_conflicts`: 识别并修复整个技能库内的逻辑冲突。

### 职责
1. **格式审计**: 确保所有知识条目包含：风险等级、下一步建议、是否建议联系团队、参考依据。
2. **消歧审计**: 保证整个 `medical_consultation_workflow` 技能库内部逻辑自洽。

---

## 6. 评估技能 (Skills)

### 核心技能: `medical_consultation_workflow`
- **定位**: 副作用评估决策字典的主入口（SKILL.md）。
- **结构**: “1个索引 + N个子资源文件”。
- **约束**: 信息足够（3要素齐全）时严禁追问；每次追问仅限一句话；两轮封顶。

---

## 7. 检索优先级
1. **Top Priority: Skills**: 优先匹配 `mcp/agents/skills` 中的字典条目。
2. **Secondary: Memory**: 扫描 `learned: false` 的历史记忆线索。
3. **Last Resort: RAG**: 若以上均无结果，调用 `RAG_Expert` 检索原始指南。

---

## 8. 可观测性 (LangSmith)

- **元数据注入**: 在 `MedicalMaster.run` 时强制向 LangSmith 注入 `system_prompt`、`tools` 和 `model` 信息。
- **全链路追踪**: 所有 Agent 与 Tool 均使用 `@traceable` 装饰器进行监控。

---

## 9. 文件结构
- `mcp/agents/master.py`: `MedicalMaster` (中控)
- `mcp/agents/memory_agent.py`: `MemoryAgent` (记忆管理)
- `mcp/agents/learning_agent.py`: `LearningAgent` (知识提炼)
- `mcp/agents/reviewer_agent.py`: `ReviewerAgent` (合规审计)
- `mcp/agents/memory/`: 结构化记忆 Markdown 存储目录
- `mcp/agents/skills/`: 技能执行手册与子资源目录
- `mcp/agents/rag_agent.py`: `RAGAgent` (专家)
- `mcp/agents/tools/`: 
  - `rag_tool.py`: RAG 检索工具
  - `skill_tools.py`: 技能查阅与资源发现工具
  - `memory_tools.py`: 记忆读写与列表提取工具
  - `learning_tools.py`: 学习触发与状态管理工具
  - `reviewer_tools.py`: 格式校验与逻辑消歧工具
