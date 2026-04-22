# MCP 开发规格书 (dev-spec)

> ⚠️ **核心开发原则**：
> 1. 修改工具接口 / 数据 Schema / 决策流前先更新此文件。
> 2. 构建任何新功能（包含最小 MVP 系统）前，**必须优先检索并阅读项目现有文件**。严禁忽视已有模块设计（如 `agents/orchestrator.py`），直接在入口脚本内“全盘重写”或“堆砌代码”。

## 文件结构 (File Structure)

```
├── agents/                      # Agent 层
│   ├── __init__.py
│   ├── orchestrator.py          # 主 Agent
│   ├── assessment_agent.py      # 子 Agent
│   ├── memory/                  # 记忆层
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── compressor.py
│   │
│   ├── tools/                   # 程序化工具层 (Infrastructure)
│   │   ├── __init__.py
│   │   ├── skill_tools.py
│   │   ├── orchestrator_tools.py
│   │   └── infrastructure_tools.py
│   │
│   └── skills/                  # 声明式技能层 (Declarative)
│       └── hand-foot-syndrome/
│           └── SKILL.md
│
├── data/                        # 数据层
│   ├── build_index.py           # 建库脚本
│   ├── rag_documents.json
│   └── vector_store/
│
├── tests/
│   ├── test_build_index.py
│   ├── test_orchestrator.py
│   ├── test_assessment_agent.py
│   ├── test_skills.py
│   └── test_memory.py
│
├── server.py                    # FastAPI 入口 (port 9001)
├── agent.py                     # Hermes ReAct 主循环 run_agent()
├── __init__.py
├── AGENTS.md
└── spec.md
```

---

## 技术选型 (Tech Stack)

| 层级 | 组件 | 选型 |
|------|------|------|
| 服务入口 | HTTP Server | `FastAPI` |
| Agent 循环 | ReAct 框架 | 原生 Python 手写（仿 Karpathy MinReAct） |
| LLM | 推理引擎 | `openai` SDK + DashScope API |
| 引导生成 | 状态机输出 | `outlines` |
| 主/子 Agent 通信 | 任务队列 | `asyncio.Queue`（同进程，MVP） |
| 记忆层 | 向量数据库 | `lancedb`（Phase 2） |
| RAG 检索 | 索引 | `faiss` |
| 嵌入模型 | Embedding | DashScope `text-embedding-v4` |
| Skill 库 | 持久化 | `skills.json`（append-only） |
| 测试 | 框架 | `pytest` + `pytest-asyncio` |
| 类型安全 | 数据模型/提示词 | `pydantic v2` |

---

## 核心架构 (Core Architecture)

基于 Hermes 理念设计多智能体 (Multi-Agent) 协同架构。

### 1. 路由控制层 (Orchestrator)
作为唯一对话入口，不负责具体业务，专注意图识别与任务调度：
- **提示词管理**：使用 `pydantic` 定义 `OrchestratorPrompt` 模型，集中管理 System Prompt 和输入变量。
- **输出管理**：使用 `outlines` 状态机强制模型输出符合 `OrchestratorResponse` Schema 的 JSON。
- **核心逻辑**：
    - **`delegate_task`**：异步派发任务，启动专属子 Agent。
    - **`update_agent_context`**：状态注入。当用户补充信息时，无缝打断并注入到运行中的子 Agent。
    - **`terminate_task`**：终止子任务或放弃当前话题。

### 2. 记忆层 (LanceDB 分层存储)
避免长上下文遗忘，采用三级存储与事件驱动压缩：
- **T2 (短期/Raw)**：保留当前活跃对话的原始日志。
- **T1 (中期/Summary)**：百字内摘要与事实提取（触发机制：数据驱动如超时/离开窗口，或管理员魔法命令 `\summary` 主动触发）。
- **T0 (长期/Index)**：极限压缩为短标题并向量化，用于跨会话语义唤醒 T1。

### 3. 工具与技能层 (Tool & Skill Layer)

依据职责隔离原则，我们将能力分为 **程序化工具 (Tools)** 和 **声明式技能 (Skills)**：

#### A. 程序化工具 (Infrastructure Tools)
*（待实现，负责底层的发现、加载与 RAG 检索逻辑）*

#### B. 声明式技能 (Business Skills - L1)
存储于 `agents/skills/<skill-name>/SKILL.md`，采用标准的 Markdown + YAML Frontmatter 格式：
- **定义**: 每一个 `SKILL.md` 文件代表一个特定副作用（如“手足综合征”）的 SOP。
- **发现**: Agent 通过 `discover_skills` 读取文件头部的 `description` 和 `triggers` 进行匹配。
- **执行**: 加载文件内容作为系统 Prompt 的动态补充。

### 4. 反馈层 (Learn Layer)
- **技能蒸馏 (Skill Distillation)**：当 RAG 路径成功解决了一个复杂或新颖的案例后，由反馈层 Agent 将其逻辑压缩为 `SkillSchema` 格式，存入 `skills.json`。
- **知识演进**：定期自省，修正逻辑冲突。

---

## 数据格式

### `agents/skills/<skill-name>/SKILL.md` (L1 Skill 格式)

遵循 Claude Agent Skills 标准。

**结构示例：**

```markdown
---
name: hand-foot-syndrome-assessment
description: 用于评估手足综合征（红肿、疼痛、脱皮）。
triggers: ["手疼", "红肿", "脱皮", "水疱"]
---

# 评估逻辑
1. 询问疼痛是否影响日常生活。
2. 观察是否有水疱或溃疡。
3. ...
```

### `data/rag_documents.json` (L2 RAG 库)

RAG 层的知识底座，存储模拟的 NCCN 指南与 CTCAE 分级问答对。

**文件结构：**

- `version`: 文档版本 (如 "1.0")
- `updated_at`: 最后更新时间
- `source`: 数据来源描述
- `risk_levels`: 风险等级定义映射 (HIGH/MEDIUM/LOW)
- `documents`: 知识条目数组

**条目 Schema (`RAGDocument`)：**

| 字段 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `id` | `string` | 唯一标识符 | `"QA-H-001"` |
| `risk_level` | `string` | 风险等级 (HIGH/MEDIUM/LOW) | `"HIGH"` |
| `risk_label` | `string` | 风险等级的人类可读标签 | `"高风险：立即线下就医..."` |
| `category` | `string` | 副作用类别 | `"hematologic_toxicity"` |
| `symptom_keywords` | `string[]` | 触发匹配的核心关键词 | `["发热", "寒战"]` |
| `questions` | `string[]` | 模拟用户可能提出的问题，用于向量增强 | `["化疗后发烧了怎么办？"]` |
| `answer` | `string` | 医学解释与处置建议（核心 RAG 输出） | `"这是高风险紧急情况..."` |
| `action_required` | `string` | 必须执行的具体动作 | `"立即就医（急诊）"` |
| `source_ref` | `string` | 引用指南的具体章节 | `"NCCN Breast Cancer v4.2024"` |
| `ctcae_grade` | `string` | 对应的 CTCAE 分级 | `"Grade 3-4"` |

---

## RAG 建库规范 (RAG Indexing)

### 1. 触发机制
- **手动触发**：`export PYTHONPATH=$PYTHONPATH:. && uv run mcp/data/build_index.py`

### 2. 处理流程 (Pipeline)
1. **Load**: 读取 `data/rag_documents.json`。
2. **Text Synthesis**: 拼接 `category` + `symptom_keywords` + `questions` 作为语义索引文本。
3. **Embedding**: 使用 Qwen (DashScope) `text-embedding-v4` 模型生成 1024 维向量。
4. **Storage**: 使用 **FAISS (IndexFlatL2)** 进行本地持久化。
   - 路径：`data/vector_store/index.faiss`
   - 映射：`data/vector_store/doc_map.pkl` (索引 ID 到 `RAGDocument` 的映射)

### 3. 验证 (Verification)
- **文件检查**：运行后 `mcp/data/vector_store/` 应生成上述两个文件。
- **测试用例**：运行 `export PYTHONPATH=$PYTHONPATH:. && pytest mcp/tests/test_build_index.py` 验证建库逻辑。

---

## 运行与验证 (Running & Testing)

### TUI 最小系统
通过 TUI 界面验证主代理（Orchestrator）与子代理（Assessment Sub-Agent）的路由交互逻辑：

1. **激活虚拟环境**：
   ```bash
   source .venv/bin/activate
   ```
2. **运行 Agent TUI**：
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   uv run python mcp/agent.py
   ```
3. **交互指令**：
   - 输入普通对话（如“你好”）测试闲聊打招呼。
   - 输入症状（如“我好像发烧了”）测试路由和子代理的 FAISS 知识库查询。
   - 输入 `terminate` 终止当前诊断。
   - 输入 `exit` 或 `quit` 退出程序。
