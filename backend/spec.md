# Backend 开发规格书 (dev-spec)

> 本文件是 Backend 实现的完整契约。修改接口/模型/服务前先更新此文件。

## 1. 系统角色
Backend 作为中控层，连接 Frontend、MCP 服务与 PostgreSQL 数据库。
- **Frontend -> Backend**: 业务 API (评估、历史、协同、埋点)。
- **Backend -> MCP**: 智能评估与知识查询 (基于 HTTP 调用)。
- **Backend -> DB**: 数据持久化与审计追踪。

## 2. 数据模型 (PostgreSQL)

### 2.1 assessments (评估记录)
用于记录用户输入、AI 判定结果及追溯规则。
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Serial | 主键 |
| session_id | String(128) | 会话 ID |
| user_input | Text | 原始用户输入 |
| risk_level | String(20) | 风险等级 (HIGH/MEDIUM/LOW) |
| action_required | String(100) | 行动建议 (如：立即线下就医) |
| ctcae_grade | String(20) | CTCAE 级别 (Grade 1-5) |
| advice | Text | 处置建议 |
| evidence | Text | 参考依据 (规则内容) |
| matched_rule_id | String(64) | 命中的规则 ID (如 QA-M-005) |
| display_text | Text | 展示文本 (可选，用于前端渲染) |
| contact_team | Boolean | 是否建议联系团队 |
| version | String(20) | 系统/规则版本 |
| created_at | DateTime | 创建时间 (UTC) |

### 2.2 contact_requests (协同请求)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Serial | 主键 |
| assessment_id | Integer | 关联评估 ID |
| session_id | String(128) | 会话 ID |
| status | String(20) | 状态 (pending/contacted) |
| created_at | DateTime | 创建时间 |

### 2.3 history_dialogues (历史对话全量)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Serial | 主键 |
| session_id | String(128) | 会话 ID |
| history_json | JSONB | 全量对话历史 (role/content 列表) |
| created_at | DateTime | 创建时间 |

### 2.4 event_logs (审计与埋点)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Serial | 主键 |
| event_name | String(64) | 事件名 (如 assessment_submitted) |
| session_id | String(128) | 会话 ID |
| payload | JSONB | 详细上下文 |
| created_at | DateTime | 记录时间 |

## 3. API 接口规范 (Base URL: /api/v1)

### 3.1 评估相关
- **POST `/assessments`**: 提交评估。
  - **Input**: 
    ```json
    { 
      "user_input": "...", 
      "session_id": "...", 
      "history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
      ]
    }
    ```
  - **Logic**: 
    1. 调用 MCP `/v1/evaluate` (传入 `history` 或从 DB 获取上下文)。
    2. 返回评估结果给前端，前端展示结果并提供“结束回答”和“我要补充”按钮。
    3. 如果前端点击“我要补充”，则重复此步骤。
    4. 如果前端点击“结束回答”，前端调用 `POST /assessments/save`。

- **POST `/assessments/save`**: 最终保存评估结果与历史对话。
  - **Input**:
    ```json
    {
      "session_id": "...",
      "assessment": { ... },
      "history": [ ... ]
    }
    ```
  - **Logic**:
    1. 将 `assessment` 存入 `assessments` 表。
    2. 将 `history` 存入 `history_dialogues` 表。
    3. 调用 MCP `/v1/memory/store` 触发记忆压缩存储。
    4. 记录 `assessment_finished` 事件。

- **GET `/assessments/{id}`**: 获取单次评估详情。
- **GET `/history`**: 获取会话历史。
  - **Query**: `session_id=...`
  - **Logic**: 从 `history_dialogues` 表查询该 session 的最新全量对话。

### 3.2 协同与埋点
- **POST `/contact-requests`**: 创建协同请求。
  - **Input**: `{ "assessment_id": int, "session_id": "string" }`
  - **Output**: `ContactRequestResponse`
- **GET `/contact-requests`**: 获取协同请求历史。
  - **Query**: `session_id=string`
  - **Output**: `List[ContactRequestResponse]`
- **POST `/events`**: 通用埋点上报 (实现 assignment.md 要求的 5 个事件)。
  - **Input**: `{ "event_name": "string", "session_id": "string", "payload": object }`
  - **Output**: `EventResponse`

### 3.3 测试与调试 (仅在 DEBUG 模式下可用)
- **GET `/debug/db/dump`**: 获取数据库所有表的快照。
  - **Output**: `{ "assessments": [...], "contact_requests": [...], "event_logs": [...], "history_dialogues": [...] }`
- **GET `/debug/db/assessments`**: 获取所有评估记录。
- **GET `/debug/db/contact-requests`**: 获取所有协同请求。
- **GET `/debug/db/events`**: 获取所有事件日志。
- **GET `/debug/db/history-dialogues`**: 获取所有历史对话记录。
- **POST `/debug/db/reset`**: 清空数据库并恢复到初始状态。

## 4. MCP 集成
- **Environment**: `MCP_URL` (默认 `http://localhost:9001`)
- **关键逻辑**：Backend 必须解析 MCP 返回的结构化数据，严禁直接处理 Markdown 文本。

## 5. 环境配置
| 变量名 | 说明 | 示例 |
|--------|------|------|
| DATABASE_URL | 数据库连接串 | `sqlite:///./shenzhi.db` 或 `postgresql://...` |
| MCP_URL | MCP 服务地址 | `http://localhost:9001` |
| DEBUG | 调试模式 | `True` |
