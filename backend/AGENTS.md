# Backend — AGENTS.md

> 继承根目录 `AGENTS.md` 全局约束。本文件是 Backend 入口（~50 行），详细契约见 `spec.md`。

## 1. 技术栈
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (Mapped Column 风格)
- **Database**: PostgreSQL
- **Manager**: `uv`

### 启动
```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```bash
source .venv/bin/activate
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 2. 验证管道 (Validation Pipeline)
1. **TDD (强制)**: 所有功能必须先在 `tests/` 编写失败测试。禁止先写业务代码再补测试。
2. **Clean Code**: 业务逻辑收口于 `app/services/`，Router 仅负责请求分发与参数校验。
3. **Environment**: 必须提供 `.env.example` 且运行前 `source .venv/bin/activate`。

## 3. 核心约束
- **审计留痕**: 临时评估无需落库，但最终“保存”时必须持久化 `assessment` 和关联的会话历史，并触发 `event_log`。
- **容错处理**: 调用 MCP 等外部服务失败时应返回明确状态码 (如 502)，后端需兜底异常，防止级联崩溃。
- **类型对齐**: Pydantic Schema 与数据库模型保持一致，但允许根据 API 需求做适度裁剪或组合。
- **环境隔离**: 数据库连接及依赖服务地址必须通过环境变量配置，禁止硬编码。
