# AI Providers Configuration Guide

Postpartum AI Copilot 支持多种 AI 服务提供商：OpenAI、Anthropic Claude 和 Google Gemini。

## 配置方法

### 1. 选择 AI 提供商

在 `backend/.env` 文件中设置：

```bash
AI_PROVIDER=openai  # 可选: openai, claude, gemini
```

### 2. OpenAI 配置

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

**支持的模型：**
- `gpt-4`
- `gpt-4-turbo-preview`
- `gpt-3.5-turbo`

### 3. Anthropic Claude 配置

```bash
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

**支持的模型：**
- `claude-3-5-sonnet-20241022` (推荐)
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

**获取 API Key：**
1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在 API Keys 页面创建新密钥

### 4. Google Gemini 配置

```bash
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-google-api-key-here
GEMINI_MODEL=gemini-pro
```

**支持的模型：**
- `gemini-pro` (推荐)
- `gemini-pro-vision`

**获取 API Key：**
1. 访问 https://makersuite.google.com/app/apikey
2. 使用 Google 账户登录
3. 创建新的 API 密钥

## 切换提供商

只需修改 `.env` 文件中的 `AI_PROVIDER` 值并重启后端服务：

```bash
# 切换到 Claude
AI_PROVIDER=claude

# 切换到 Gemini
AI_PROVIDER=gemini

# 切换回 OpenAI
AI_PROVIDER=openai
```

重启后端：
```bash
uvicorn main:app --reload
```

## 功能对比

| 功能 | OpenAI | Claude | Gemini |
|------|--------|--------|--------|
| 聊天对话 | ✅ | ✅ | ✅ |
| 流式响应 | ✅ | ✅ | ✅ |
| 系统提示 | ✅ | ✅ | ⚠️ (需转换) |
| 上下文长度 | 高 | 很高 | 高 |
| 响应速度 | 快 | 中等 | 快 |
| 成本 | 中等 | 较高 | 较低 |

## 注意事项

1. **API 密钥安全**
   - 永远不要将 API 密钥提交到版本控制
   - 使用 `.env` 文件存储密钥
   - `.env` 文件已在 `.gitignore` 中

2. **模型兼容性**
   - 不同提供商的模型能力略有不同
   - 某些功能可能需要调整提示词
   - 建议测试后再切换

3. **成本考虑**
   - OpenAI: 按 token 计费
   - Claude: 按 token 计费，价格较高但质量好
   - Gemini: 免费额度较大，适合开发测试

4. **错误处理**
   - 如果配置的提供商不可用，应用会显示错误信息
   - 检查 API 密钥是否正确
   - 检查网络连接

## 测试配置

使用健康检查端点验证配置：

```bash
curl http://localhost:8000/health
```

查看当前使用的 AI 提供商：

```bash
curl http://localhost:8000/api/ai/provider
```

## 故障排除

### OpenAI 错误
- 检查 API 密钥格式：`sk-...`
- 确认账户有足够余额
- 检查模型名称是否正确

### Claude 错误
- 检查 API 密钥格式：`sk-ant-...`
- 确认账户已激活
- 检查模型名称是否支持

### Gemini 错误
- 检查 API 密钥是否正确
- 确认 API 已启用
- 检查配额限制

## 推荐配置

**开发环境：**
- 使用 Gemini（免费额度大）

**生产环境：**
- 使用 OpenAI GPT-4（稳定、快速）
- 或 Claude 3.5 Sonnet（质量最高）

**成本优化：**
- 使用 Gemini Pro（成本最低）
- 或 OpenAI GPT-3.5-turbo（性价比高）
