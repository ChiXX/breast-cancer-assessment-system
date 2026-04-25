# Frontend — AGENTS.md

> 继承 `agents/AGENTS.md` 全局约束。本文件定义 Frontend 专属规则。

## 技术约束

- React 18 + TypeScript strict mode
- 构建工具：Vite
- 状态管理：TanStack Query（服务端状态）
- 样式方案：TailwindCSS
- 路由：React Router v6

> 页面规格、组件清单、类型定义、事件触发 → 见 `frontend/spec.md`

## 验证管道

| 命令 | 通过标准 |
|------|---------|
| `npm run test` | exit 0 |
| `npm run lint` | 0 violations |

失败 → 修复 → 重跑。

## 开发约定

- 组件拆分：一个文件一个组件
- 类型安全：禁止 `any`，所有 props 定义接口
- API 调用统一走 service 层，组件不直接 fetch

## 启动

```bash
cd frontend
npm install && npm run dev
```
