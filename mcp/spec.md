# MCP Agent Specification

## 1. 核心 Agent: MedicalMaster

### 定位
作为系统的“中控客服”，基于 `Assistant` 架构。负责作为患者与专家系统间的桥梁，进行初步接待、意图识别、资源调度与结果汇总。

### 技术选型
- **框架**: `qwen_agent.agents.Assistant` (使用 Tool-based 模式调用子 Agent)
- **底座模型**: `qwen3.5-plus`
- **主要工具**: 
  - `RAG_Expert`: 包装了 RAGAgent 的工具，负责获取指南。
  - `read_skill`: 查阅评估技能执行手册（SKILL.md）。
- **输入**: 用户自然语言文本
- **输出**: 汇总专家评估后的专业反馈

### 职责
1. **中控调度**: 识别症状，**强制**调用 `RAG_Expert`。
2. **极简追问**: 根据 `symptom_followup` 技能，在信息缺失时进行单句、单点的极简追问。
3. **信息汇总**: **原样转达** `RAG_Expert` 的结构化建议，仅添加必要的开场白或免责提醒。

---

## 2. 专家 Agent: RAGAgent (RAG_Expert)

### 定位
医疗知识专家，专门负责通过 RAG 工具检索权威指南并给出分级建议。

### 技术选型
- **框架**: `qwen_agent.agents.Assistant`
- **工具**: `rag_query_tool` (对接本地 FAISS 向量库)

### 职责
1. **结构化输出**: 严格按以下格式输出：
   - 1. 风险等级
   - 2. 下一步建议
   - 3. 是否建议联系团队
   - 4. 简单依据说明
   - 5. 参考依据ID (如 QA-M-004)
2. **确定性逻辑**: 检索不到结果时必须回答“不清楚”，禁止幻觉。

---

## 3. 评估技能 (Skills)

### 核心技能: `symptom_followup`
- **目标**: 补全症状的名称、时长、严重程度。
- **约束**:
  - **必要性评估**: 信息足够（3要素齐全）时严禁追问，直接查询。
  - **单句原则**: 每次追问仅限一句话。
  - **两轮封顶**: 针对同一症状，追问总次数严禁超过 2 次。

---

## 4. 可观测性 (LangSmith)

### 监控实现
- **全链路追踪**: 使用 `@traceable` 装饰器覆盖 Master、Sub-Agent 及关键 Tool。
- **元数据捕获**: 记录 Agent 决策链、Tool 调用细节及 Token 消耗。

---

## 5. 文件结构
- `mcp/agents/master.py`: `MedicalMaster` (中控/Assistant)
- `mcp/agents/rag_agent.py`: `RAGAgent` (专家/Assistant)
- `mcp/agents/skills/`: 技能定义目录 (SKILL.md)
- `mcp/agents/tools/`: 工具定义目录 (rag_tool.py, skill_tools.py)
- `mcp/data/`: 知识库与向量存储 (rag_documents.json, vector_store/)
