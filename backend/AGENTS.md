# Backend — AGENTS.md

> 模块级约束，确保 Backend 实现的一致性与健壮性。

## 1. 技术栈
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (Mapped Column 风格)
- **Database**: PostgreSQL
- **Manager**: `uv`

### 启动
```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 2. 验证管道 (Validation Pipeline)
1. **TDD (强制)**: 所有功能必须先在 `tests/` 编写失败测试。禁止先写业务代码再补测试。
2. **Clean Code**: 业务逻辑收口于 `app/services/`，Router 仅负责请求分发与参数校验。
3. **Environment**: 必须提供 `.env.example` 且运行前 `source .venv/bin/activate`。

## 3. 核心约束
- **审计优先**: 每次评估必须产生 `assessment` 记录和至少一个 `event_log`。
- **错误处理**: 调用 MCP 失败时，必须返回清晰的 502 (Bad Gateway) 错误，并记录错误日志。
- **类型安全**: Pydantic Schema 必须与数据库模型及 API 契约保持 100% 同步。
- **环境隔离**: 数据库连接通过 `DATABASE_URL` 环境变量配置。
