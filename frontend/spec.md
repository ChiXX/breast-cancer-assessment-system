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
| `/` | `ChatPage` | 对话式症状输入、多轮追问、实时风险评估展示 |
| `/result/:id` | `ResultPage` | (Legacy/Detail) 风险分级详细展示 |
| `/history` | `HistoryPage` | 历史记录列表 |

## 3. 核心组件实现 (Component Details)

### 3.1 视觉规范 (Aesthetics)
- **Chat UI**: 气泡式对话流，用户消息靠右，AI 消息靠左。
- **Auto-scroll**: 对话更新时自动滚动到底部。
- **Inline Results**: 当 AI 返回明确风险等级（非“未知”）时，在对话流中紧随 AI 回复展示 `RiskBanner` 与 `AdviceCard`。

### 3.2 业务组件
- **`ChatMessage`**: 对话气泡组件，支持 Markdown 渲染。
- **`ChatInput`**: 支持多行输入、快捷发送及发送状态反馈。**当显示评估结果时，输入框变为 disabled 状态。**
- **`RiskBanner`**: 自动映射后端 `risk_level`, `action_required` 和 `ctcae_grade`：
  - **红色 (Grade 1)**: 立即线下就医 -> 展示“拨打 120”或“联系急诊”按钮。
  - **橙色 (Grade 2)**: 24小时内联系团队 -> 展示“预约医生”按钮。
  - **黄色 (Grade 3)**: 联系团队 -> 展示“在线咨询”按钮。
  - **蓝色 (Grade 4)**: 密切观察 -> 展示“添加观察日志”按钮。
  - **绿色 (Grade 5)**: 继续观察与记录 -> 展示“完成记录”按钮。
- **`AssessmentActions`**: 结果展示时出现的附加按钮：
  - **结束回答**: 提交最终评估结果并存入历史对话，随后开启新对话（清空当前状态）。
  - **我要补充**: 重新启用输入框，继续对话。

## 4. API 交互与代理 (Networking)

### 4.1 代理配置 (Vite Proxy)
所有以 `/api` 开头的请求均通过 Vite 转发至 `http://127.0.0.1:8000`，有效解决跨域 (CORS) 并简化了部署环境下的端口转发需求。

### 4.2 接口映射
- `POST /api/v1/assessments`: 提交评估数据以获取实时反馈。
- `POST /api/v1/assessments/save`: 最终提交评估结果与全量历史对话。
- `GET /api/v1/assessments`: 获取所有评估记录列表（用于历史页面）。
- `GET /api/v1/assessments/{id}`: 获取详情。
- `GET /api/v1/assessments/{id}/history`: 获取该评估对应的完整对话历史。
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
