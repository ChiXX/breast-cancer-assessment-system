---
description: 化疗常见副作用的分诊评估与护理建议，包括脱发、皮肤干燥/瘙痒/色素改变、手脚麻木等症状的风险分级与处置指导。
name: chemotherapy-side-effect-triage
updated_at: '2026-04-27T15:51:24.892721'
---

# 化疗副作用分诊技能

本技能提供化疗期间常见副作用的评估与处置指导。每个症状的详细评估逻辑存储在对应的子资源文件中。

## 症状索引

| 症状 | 资源文件 | 规则ID | 风险等级 |
|------|---------|--------|---------|
| 脱发 | [alopecia.md](./alopecia.md) | QA-L-001 | LOW |
| 皮肤干燥/瘙痒/色素改变 | [dry-skin.md](./dry-skin.md) | QA-L-002 | LOW |
| 手脚麻木（严重） | [peripheral-neuropathy.md](./peripheral-neuropathy.md) | QA-M-005 | HIGH |

## 使用说明

1. 根据患者主诉的症状，定位到对应的子资源文件。
2. 读取文件中的 `assessment` 对象，获取风险等级、处置建议和护理指导。
3. 遵循 `action_required` 执行相应操作。
4. 如 `contact_team` 为 `true`，需立即联系医疗团队。

