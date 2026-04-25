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
| risk_level | String(20) | 风险等级 (高/中/低/未知) |
| advice | Text | 处置建议 |
| evidence | Text | 参考依据 (规则内容) |
| matched_rule_id | String(64) | 命中的规则 ID (如 QA-M-005) |
| contact_team | Boolean | 是否建议联系团队 |
| created_at | DateTime | 创建时间 (UTC) |

### 2.2 contact_requests (协同请求)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Serial | 主键 |
| assessment_id | Integer | 关联评估 ID |
| session_id | String(128) | 会话 ID |
| status | String(20) | 状态 (pending/contacted) |
| created_at | DateTime | 创建时间 |

### 2.3 event_logs (审计与埋点)
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
  - **Input**: `{ "user_input": "...", "session_id": "..." }`
  - **Logic**: Backend 调用 MCP `/v1/evaluate` -> 将结果存入 `assessments` 表 -> 记录 `assessment_submitted` 事件。
  - **Output**: `AssessmentResponse` (包含 risk_level, advice, evidence, contact_team, rule_id)。

- **GET `/assessments/{id}`**: 获取单次评估详情。
- **GET `/history`**: 获取会话历史。
  - **Query**: `session_id=...`
  - **Logic**: 从 `assessments` 表按时间倒序查询。

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

## 4. MCP 集成
- **Environment**: `MCP_URL` (默认 `http://localhost:9001`)
- **关键逻辑**：Backend 必须解析 MCP 返回的结构化数据，严禁直接处理 Markdown 文本。

## 5. 环境配置
| 变量名 | 说明 | 示例 |
|--------|------|------|
| DATABASE_URL | 数据库连接串 | `sqlite:///./shenzhi.db` 或 `postgresql://...` |
| MCP_URL | MCP 服务地址 | `http://localhost:9001` |
| DEBUG | 调试模式 | `True` |
