# 个性化优化接口文档

## 概述

个性化优化接口允许根据用户的个人数据来定制和优化AI响应。系统会自动学习用户偏好，并根据用户的行为模式、偏好设置和上下文信息来提供更个性化的体验。

## API 端点

### 1. 获取个性化配置

**GET** `/api/user/{user_id}/personalization`

获取用户的完整个性化配置。

**响应示例：**
```json
{
  "response_style": "balanced",
  "tone_preference": "warm",
  "detail_level": "moderate",
  "preferred_topics": ["feeding", "sleep", "diaper"],
  "avoided_topics": [],
  "interaction_patterns": {
    "active_days": 15,
    "preferred_time": "varied",
    "interaction_frequency": "medium",
    "total_entries": 45
  },
  "baby_stage": "newborn_month1",
  "customizations": {
    "baby_name": "Emma",
    "feeding_preferences": "breast",
    "birth_experience": "vaginal",
    "cultural_preferences": {},
    "medical_guidelines": {},
    "doctor_notes": ""
  },
  "language": "en",
  "timezone": "UTC",
  "notification_preferences": {}
}
```

### 2. 更新个性化偏好

**POST** `/api/user/personalization`

更新用户的个性化偏好设置。

**请求体：**
```json
{
  "user_id": "user123",
  "preferences": {
    "response_style": "brief",
    "tone_preference": "warm",
    "detail_level": "minimal",
    "preferred_topics": ["feeding", "sleep"],
    "customizations": {
      "baby_name": "Emma",
      "doctor_notes": "Pediatrician recommends feeding every 2-3 hours"
    }
  }
}
```

**响应：**
```json
{
  "message": "Personalization preferences updated",
  "preferences": {
    "response_style": "brief",
    "tone_preference": "warm",
    ...
  },
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 3. 个性化聊天接口

**POST** `/api/chat/personalized`

使用个性化优化的聊天接口。自动应用用户的个性化设置。

**请求体：**
```json
{
  "user_id": "user123",
  "query": "My baby won't sleep",
  "language": "en"
}
```

**响应：**
```json
{
  "response": "I understand that can be really tough...",
  "suggestions": [...],
  "red_flags": [...],
  "timestamp": "2024-01-15T10:30:00Z",
  "validation": {...},
  "personalization_applied": true
}
```

## 个性化维度

### 1. 响应风格 (Response Style)

- **brief**: 简洁响应（2-3句话）
- **detailed**: 详细响应（包含完整解释）
- **balanced**: 平衡响应（默认）

### 2. 语气偏好 (Tone Preference)

- **warm**: 温暖、共情、支持性
- **professional**: 专业但友好
- **casual**: 随意、友好

### 3. 详细程度 (Detail Level)

- **minimal**: 仅核心信息
- **moderate**: 适度详细（默认）
- **comprehensive**: 全面详细

### 4. 偏好主题 (Preferred Topics)

用户经常询问的主题列表，AI会优先关注这些主题。

### 5. 避免主题 (Avoided Topics)

用户不希望讨论的主题列表。

### 6. 自定义设置 (Customizations)

- **baby_name**: 宝宝名字
- **feeding_preferences**: 喂养偏好
- **birth_experience**: 分娩经历
- **cultural_preferences**: 文化偏好
- **medical_guidelines**: 医疗指导
- **doctor_notes**: 医生备注

## 自动学习

系统会自动从用户行为中学习：

1. **交互频率**: 根据使用频率调整响应详细程度
2. **活跃时间**: 识别用户最活跃的时间段
3. **偏好主题**: 从跟踪数据中提取最常关注的主题
4. **宝宝阶段**: 根据宝宝年龄自动调整建议

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"
USER_ID = "user123"

# 获取个性化配置
response = requests.get(f"{BASE_URL}/api/user/{USER_ID}/personalization")
profile = response.json()
print(f"Response style: {profile['response_style']}")

# 更新偏好
preferences = {
    "user_id": USER_ID,
    "preferences": {
        "response_style": "brief",
        "tone_preference": "warm",
        "customizations": {
            "baby_name": "Emma"
        }
    }
}
response = requests.post(
    f"{BASE_URL}/api/user/personalization",
    json=preferences
)

# 使用个性化聊天
chat_request = {
    "user_id": USER_ID,
    "query": "My baby won't sleep",
    "language": "en"
}
response = requests.post(
    f"{BASE_URL}/api/chat/personalized",
    json=chat_request
)
result = response.json()
print(result["response"])
```

### JavaScript 示例

```javascript
const API_BASE = 'http://localhost:8000';
const userId = 'user123';

// 获取个性化配置
const profile = await fetch(`${API_BASE}/api/user/${userId}/personalization`)
  .then(r => r.json());

// 更新偏好
await fetch(`${API_BASE}/api/user/personalization`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: userId,
    preferences: {
      response_style: 'brief',
      tone_preference: 'warm',
      customizations: {
        baby_name: 'Emma'
      }
    }
  })
});

// 使用个性化聊天
const response = await fetch(`${API_BASE}/api/chat/personalized`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: userId,
    query: "My baby won't sleep",
    language: 'en'
  })
});
const result = await response.json();
console.log(result.response);
```

## 集成到现有聊天

现有的 `/api/chat` 端点仍然可用，但不会应用个性化优化。

要使用个性化功能，请使用：
- `/api/chat/personalized` - 应用完整个性化
- 或先调用 `/api/user/{user_id}/personalization` 获取配置，然后手动应用到 `/api/chat`

## 个性化效果

使用个性化接口后，AI响应会：

1. **根据响应风格调整长度**
   - Brief: 2-3句话
   - Detailed: 完整解释
   - Balanced: 适中长度

2. **根据语气偏好调整语调**
   - Warm: 更多共情和支持
   - Professional: 更正式但友好
   - Casual: 更随意

3. **根据详细程度调整内容深度**
   - Minimal: 只给要点
   - Comprehensive: 包含背景和解释
   - Moderate: 平衡

4. **考虑宝宝阶段**
   - 根据宝宝年龄调整建议的适用性
   - 关注当前阶段的发展重点

5. **使用自定义信息**
   - 在适当时候使用宝宝名字
   - 参考医生的指导
   - 考虑文化偏好

## 最佳实践

1. **初始设置**: 新用户完成欢迎流程后，系统会自动创建基础个性化配置
2. **渐进学习**: 系统会随着使用逐渐学习用户偏好
3. **手动调整**: 用户可以在设置中手动调整偏好
4. **定期更新**: 系统会根据新的交互数据定期更新个性化配置

## 注意事项

- 个性化数据存储在用户上下文中
- 所有个性化设置都是可选的
- 如果未设置，系统会使用智能默认值
- 个性化不会影响安全性验证
