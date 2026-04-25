# Frontend 开发规格书 (dev-spec)

> 本文件是 Frontend 实现的完整契约。项目已按照此规格书完成 1.0.0 版本的开发。

## 1. 技术栈 (Implemented Tech Stack)

- **框架**: React 18 + TypeScript (Strict Mode)
- **构建工具**: Vite (配置固定端口 5173 及 0.0.0.0 宿主暴露)
- **状态管理**: TanStack Query v5
- **样式**: TailwindCSS v3.4 (配置自定义 HSL 品牌色)
- **路由**: React Router v6
- **图标**: Lucide React
- **动效**: Framer Motion (用于页面入场与卡片交互)

## 2. 页面与路由 (Final Routes)

| 路径 | 页面组件 | 核心功能 |
| :--- | :--- | :--- |
| `/` | `InputPage` | 症状输入、Session 初始化、埋点上报 |
| `/result/:id` | `ResultPage` | 风险分级展示（红/黄/绿）、动态处置建议、依据追溯 |
| `/history` | `HistoryPage` | 历史记录列表、风险状态摘要、回溯详情入口 |

## 3. 核心组件实现 (Component Details)

### 3.1 视觉规范 (Aesthetics)
- **Premium UI**: 采用玻璃拟态 (Glassmorphism) 导航栏，配合 HSL 动态渐变风险 Banner。
- **响应式**: 适配移动端与桌面端，最大容器宽度 640px (max-w-2xl)。
- **微动效**: 实现 `animate-fade-in` 入场动画及按钮 Hover 缩放效果。

### 3.2 业务组件
- **`RiskBanner`**: 自动映射后端 `risk_level`，动态切换渐变色背景与图标。
- **`AdviceCard`**: 结构化展示处置建议，支持 `contact_team` 逻辑触发协同按钮。
- **`EvidenceAccordion`**: 展示审计依据，包含规则 ID 与系统版本号。
- **`HistoryList`**: 时间轴样式的评估记录列表，支持风险标识摘要。

## 4. API 交互与代理 (Networking)

### 4.1 代理配置 (Vite Proxy)
所有以 `/api` 开头的请求均通过 Vite 转发至 `http://127.0.0.1:8000`，有效解决跨域 (CORS) 并简化了部署环境下的端口转发需求。

### 4.2 接口映射
- `POST /api/v1/assessments`: 提交评估数据。
- `GET /api/v1/assessments/{id}`: 获取详情。
- `GET /api/v1/assessments?session_id=...`: 获取会话历史。
- `POST /api/v1/events`: 埋点事件上报。

## 5. 可观测性 (Observability)

已实现在 `assignment.md` 要求的 5 个事件埋点：
1. `assessment_started`: 进入首页时触发。
2. `assessment_submitted`: 成功获取 AI 结果后触发。
3. `result_viewed`: 进入结果详情页时触发。
4. `contact_team_clicked`: 用户点击“联系团队”按钮时触发。
5. `assessment_closed`: 离开输入页面或关闭应用时触发。

## 6. 开发环境维护
- **启动**: `npm run dev` (监听 5173 端口)
- **测试**: `npm run test` (基于 Vitest)
- **Session ID**: 存储于 `localStorage` 键名 `shenzhi_session_id`。
