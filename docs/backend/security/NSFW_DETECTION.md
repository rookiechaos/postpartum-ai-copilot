# NSFW 内容检测系统
## NSFW Content Detection System

## 概述

NSFW（Not Safe For Work）内容检测系统用于在所有用户交互中检测和阻止不当内容，确保平台内容的安全性和适宜性。这对于产后护理应用尤其重要，需要确保所有生成的内容都是安全、专业、适当的。

## 功能特性

### 1. 多层级检测
- **用户输入检测**: 检查所有用户输入（聊天、语音、追踪笔记等）
- **AI响应检测**: 检查所有AI生成的内容
- **双重保护**: 确保输入和输出都经过审核

### 2. 多提供商支持
- **OpenAI Moderation API**（主要方式）：使用 OpenAI 的官方内容审核 API
- **关键词检测**（后备方式）：当 AI API 不可用时使用
- **自动降级**: 如果主要检测失败，自动使用后备方法

### 3. 检测级别
- **SAFE**: 内容安全，可以处理
- **SUSPICIOUS**: 内容可疑，需要进一步审查
- **UNSAFE**: 内容不当，必须阻止

### 4. 集成端点
NSFW 检测已集成到以下所有用户交互端点：
- ✅ `/api/chat` - 聊天端点（输入和输出）
- ✅ `/api/crisis` - 危机模式端点
- ✅ `/api/tracking` - 追踪端点（notes字段）
- ✅ `/api/voice/speech-to-text` - 语音转文字
- ✅ `/api/voice/text-to-speech` - 文字转语音
- ✅ AI服务内部 - 所有AI响应生成

## 配置

### 环境变量

在 `.env` 文件中配置：

```env
# NSFW Detection Configuration
NSFW_DETECTION_ENABLED=true  # 启用 NSFW 检测（默认: true）
NSFW_DETECTION_STRICT=true   # 严格模式：阻止所有被标记的内容（默认: true）
                              # 如果为 false，只阻止不安全内容

# AI Provider (用于 NSFW 检测)
AI_PROVIDER=openai  # openai, claude, gemini
OPENAI_API_KEY=your-openai-api-key  # 如果使用 OpenAI
```

### 配置说明

- **NSFW_DETECTION_ENABLED**: 控制是否启用 NSFW 检测
  - `true`: 启用检测（推荐，生产环境必须）
  - `false`: 禁用检测（不推荐用于生产环境）

- **NSFW_DETECTION_STRICT**: 控制检测严格程度
  - `true`: 严格模式，所有被标记的内容都会被阻止
  - `false`: 宽松模式，只阻止明确不安全的内容

## 使用方法

### 在代码中使用

```python
from services.nsfw_detector import get_nsfw_detector

# 获取检测器实例
nsfw_detector = get_nsfw_detector()

# 检测文本
result = await nsfw_detector.check("用户输入的文本", language="en", check_type="input")

# 检查是否应该阻止
if nsfw_detector.should_block(result):
    raise ValidationError(nsfw_detector.get_block_message("en"))
```

### 检测结果格式

```python
{
    "safe": bool,              # 内容是否安全
    "level": str,              # "safe" | "suspicious" | "unsafe"
    "reason": str,             # 检测原因
    "blocked": bool,            # 是否应该阻止
    "categories": dict,         # 详细类别标志
    "category_scores": dict,    # 类别分数
    "confidence": float         # 检测置信度
}
```

## 检测流程

### 用户输入检测流程

1. 用户提交内容（聊天、语音、追踪等）
2. NSFW检测器检查内容
3. 如果检测到不当内容：
   - 阻止请求
   - 返回友好的错误消息
   - 记录安全事件
4. 如果内容安全：
   - 继续处理请求

### AI响应检测流程

1. AI生成响应
2. NSFW检测器检查响应
3. 如果检测到不当内容：
   - 替换为安全的默认响应
   - 记录安全事件
   - 不向用户显示不当内容
4. 如果内容安全：
   - 正常返回响应

## 安全措施

### 1. 多层防护
- 用户输入检测（第一层）
- AI响应检测（第二层）
- 医疗安全规则（第三层）

### 2. 自动降级
- 如果OpenAI Moderation API不可用，自动使用关键词检测
- 确保检测服务始终可用

### 3. 日志记录
- 所有被阻止的内容都记录在日志中
- 包含检测级别、原因、用户ID等信息
- 用于安全审计和问题排查

### 4. 用户友好
- 被阻止时返回友好的错误消息
- 多语言支持（英语、日语、中文）
- 不暴露技术细节

## 测试

### 测试NSFW检测

```python
from services.nsfw_detector import get_nsfw_detector

detector = get_nsfw_detector()

# 测试安全内容
result = await detector.check("How often should I feed my baby?")
assert result["safe"] == True

# 测试不当内容（示例）
# result = await detector.check("inappropriate content")
# assert result["safe"] == False
```

## 最佳实践

1. **始终启用**: 在生产环境中始终启用NSFW检测
2. **使用严格模式**: 对于医疗应用，建议使用严格模式
3. **监控日志**: 定期检查被阻止的内容，了解用户行为
4. **更新关键词**: 如果使用关键词检测，定期更新关键词列表
5. **API密钥安全**: 确保OpenAI API密钥安全存储

## 故障排除

### OpenAI Moderation API不可用
- 检查API密钥是否正确配置
- 检查网络连接
- 系统会自动降级到关键词检测

### 误报
- 检查检测级别设置
- 考虑调整严格模式设置
- 查看详细的检测结果和类别分数

### 性能问题
- NSFW检测是异步的，不会阻塞主流程
- 如果检测太慢，考虑使用缓存
- 监控检测API的响应时间

## 相关文件

- `backend/services/nsfw_detector.py` - NSFW检测服务
- `backend/services/ai_service.py` - AI服务（集成NSFW检测）
- `backend/main.py` - API端点（集成NSFW检测）
- `backend/api/voice_routes.py` - 语音路由（集成NSFW检测）
