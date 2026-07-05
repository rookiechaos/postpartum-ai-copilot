# Suggestion Validation System

## 概述

Postpartum AI Copilot 实现了多层建议验证系统，确保所有 AI 生成的建议都经过准确性、安全性和合规性检查。  
**说明**：以下规则与 RAG 用于**内容安全**（避免 AI 输出医疗建议/诊断），并非对产品进行「医疗标准」认证；本产品为陪伴与支持工具，非医疗产品。

## 验证层级

### 1. 硬性安全规则 (Hard Safety Rules)

`medical_safety_rules.py` 定义了绝对不能违反的规则：

- **禁止模式**：
  - 不得推荐未经医生咨询的药物治疗
  - 不得提供医疗诊断
  - 不得建议忽略医疗建议
  - 不得建议跳过医疗预约
  - 不得延迟紧急呼叫

- **必需免责声明**：
  - 医疗建议必须包含免责声明
  - 药物相关建议必须强调咨询医生
  - 紧急情况必须建议立即就医
  - 心理健康问题必须提供紧急资源

### 2. 建议验证器 (Suggestion Validator)

`suggestion_validator.py` 提供：

- **安全检查**：
  - 检测危险内容
  - 识别不确定语言
  - 标记红色警告标志
  - 验证是否符合医疗指南

- **置信度评分**：
  - 基于多个因素计算置信度 (0-1)
  - 不确定语言降低置信度
  - 警告降低安全分数

- **RAG 交叉验证**：
  - 与可信医疗来源对比
  - 计算一致性分数
  - 检测矛盾

### 3. 验证结果

每个建议返回：

```python
{
    "is_valid": bool,           # 是否有效
    "confidence": float,        # 置信度 (0-1)
    "safety_score": float,      # 安全分数 (0-1)
    "warnings": List[str],     # 警告列表
    "needs_review": bool,       # 是否需要人工审核
    "validated_suggestion": str # 验证后的建议（可能添加了免责声明）
}
```

## 使用流程

### 1. AI 生成建议

AI 服务生成原始建议。

### 2. 验证建议

```python
validator = SuggestionValidator()
validation = validator.validate_suggestion(
    suggestion="...",
    context={...},
    suggestion_type="general"
)
```

### 3. 交叉验证（如果可用）

```python
rag_validation = validator.cross_validate_with_rag(
    suggestion="...",
    rag_context="..."
)
```

### 4. 过滤和标记

- 无效建议被移除或标记
- 低安全分数建议添加警告
- 添加必需的免责声明

### 5. 返回给用户

前端显示：
- 验证状态徽章
- 置信度分数
- 警告图标（如果有）

## 验证规则详情

### 危险内容检测

检测以下关键词：
- "give medication without doctor"
- "ignore medical advice"
- "self-diagnose"
- "don't call doctor"

### 不确定语言

检测：
- "might be"
- "could be"
- "possibly"
- "maybe"
- "uncertain"

### 红色警告标志

自动标记：
- 高烧 (>100.4°F)
- 呼吸困难
- 脱水迹象
- 6+ 小时无湿尿布
- 过度出血
- 严重疼痛
- 自伤想法

### 医疗指南验证

根据可信来源验证：
- 喂养频率：8-12 次/天（新生儿）
- 睡眠时长：14-17 小时/天
- 尿布更换：6+ 次/天

## 前端显示

### 验证徽章

- **✓ Validated** (绿色) - 所有建议已验证且安全
- **⚠ Reviewed** (橙色) - 建议已审核但需要谨慎

### 置信度显示

显示平均置信度百分比，帮助用户了解建议的可靠性。

### 警告图标

如果建议有警告，显示 ⚠️ 图标，悬停显示警告详情。

## 测试

运行验证测试：

```bash
cd backend/services
python validation_test.py
```

## 配置

可以在 `suggestion_validator.py` 中调整：

- 安全关键词列表
- 置信度阈值
- 安全分数计算权重
- 医疗指南参数

## 最佳实践

1. **始终验证**：所有 AI 生成的建议都应经过验证
2. **保守原则**：不确定时，添加免责声明或标记为需要审核
3. **用户透明**：向用户显示验证状态和置信度
4. **持续改进**：根据反馈调整验证规则

## 未来增强

- [ ] 使用嵌入模型进行语义相似度检查
- [ ] 集成更多可信医疗来源
- [ ] 实现学习机制，从用户反馈中改进
- [ ] 添加多语言验证支持
- [ ] 实现实时验证监控和告警
