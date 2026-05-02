# Frontend — AGENTS.md

> 继承根目录 `AGENTS.md` 全局约束。本文件定义 Frontend 入口（~50 行），详细契约见 `spec.md`。


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

- 组件划分：鼓励高内聚，页面内部强相关的内联模块（如 ChatPage 的交互元素）可以保持在一个文件内，公用组件再行拆分
- 类型安全：尽量避免 `any`，但在必要时（如适配不确定的历史数据或复杂配置）可适度放宽
- API 调用统一走 service 层，组件不直接 fetch

## 启动

```bash
cd frontend
npm install && npm run dev
```
