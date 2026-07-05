# Postpartum AI Copilot - 测试文档

## 测试概览

本文档包含应用的功能测试清单和测试用例。

## 环境准备

### 后端测试
```bash
cd backend
pip install -r requirements.txt
cp env.example .env
# 在 .env 中添加 OPENAI_API_KEY
uvicorn main:app --reload
```

### 前端测试
```bash
cd frontend
npm install
npm run dev
```

## 功能测试清单

### ✅ 核心功能测试

#### 1. 欢迎屏幕 (WelcomeScreen)
- [ ] 首次访问显示欢迎屏幕
- [ ] 可以完成引导流程
- [ ] 可以跳过引导
- [ ] 信息保存到本地存储
- [ ] 完成引导后不再显示

#### 2. 仪表板 (Dashboard)
- [ ] 显示今日统计（喂养、尿布、睡眠）
- [ ] 快速操作按钮可用
- [ ] AI 洞察显示正常
- [ ] 加载时显示骨架屏
- [ ] 响应式设计正常

#### 3. AI 聊天 (ChatInterface)
- [ ] 可以发送消息
- [ ] 收到 AI 回复
- [ ] 显示建议和红色警告
- [ ] 流式响应（如果启用）
- [ ] 错误处理正常
- [ ] Toast 通知显示

#### 4. 智能跟踪 (TrackingPanel)
- [ ] 可以添加跟踪条目
- [ ] 显示最近条目列表
- [ ] AI 摘要生成
- [ ] 图表显示正常
- [ ] 可以切换显示/隐藏图表
- [ ] 数据导出功能

#### 5. 夜间模式 (NightMode)
- [ ] 可以从任何页面进入
- [ ] 快速操作按钮可用
- [ ] 响应简洁明了
- [ ] 紧急信息显示
- [ ] 可以退出夜间模式

#### 6. 情绪检查 (EmotionalCheckIn)
- [ ] 可以提交检查
- [ ] 风险评估正确
- [ ] 显示建议和资源
- [ ] 高风险情况升级提示
- [ ] 数据保存正常

#### 7. 设置页面 (Settings)
- [ ] 可以更新用户信息
- [ ] 可以修改偏好设置
- [ ] 数据导出功能
- [ ] 通知管理功能
- [ ] 帮助文档显示

### ✅ UI/UX 测试

#### 响应式设计
- [ ] 移动端 (< 768px) 显示正常
- [ ] 平板 (768px - 1024px) 显示正常
- [ ] 桌面 (> 1024px) 显示正常
- [ ] 导航栏在小屏幕上适配

#### 动画和交互
- [ ] 页面切换动画流畅
- [ ] 按钮悬停效果正常
- [ ] 加载状态显示
- [ ] Toast 通知动画

#### 可访问性
- [ ] 键盘导航可用
- [ ] 屏幕阅读器兼容
- [ ] 颜色对比度足够
- [ ] 焦点状态清晰

### ✅ 数据管理测试

#### 本地存储
- [ ] 用户 ID 保存
- [ ] 用户上下文保存
- [ ] 提醒设置保存
- [ ] 数据持久化正常

#### API 集成
- [ ] 后端 API 连接正常
- [ ] 错误处理正确
- [ ] 超时处理
- [ ] 网络错误提示

### ✅ PWA 功能测试

#### Service Worker
- [ ] Service Worker 注册成功
- [ ] 离线缓存工作正常
- [ ] 离线页面显示
- [ ] 缓存更新机制

#### 安装功能
- [ ] 安装提示显示
- [ ] 可以安装到主屏幕
- [ ] 安装后独立运行
- [ ] 图标和名称正确

#### 通知系统
- [ ] 通知权限请求
- [ ] 通知显示正常
- [ ] 提醒调度正确
- [ ] 通知点击跳转

### ✅ 错误处理测试

#### 错误边界
- [ ] 组件错误被捕获
- [ ] 错误页面显示
- [ ] 可以重载应用
- [ ] 可以返回首页

#### 网络错误
- [ ] API 错误处理
- [ ] 超时处理
- [ ] 离线状态处理
- [ ] 错误消息友好

## API 端点测试

### 使用 curl 测试

#### 健康检查
```bash
curl http://localhost:8000/health
```

#### 聊天测试
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My baby is crying, what should I do?",
    "user_id": "test_user_123"
  }'
```

#### 添加跟踪条目
```bash
curl -X POST http://localhost:8000/api/tracking \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "entry_type": "feeding",
    "feeding_type": "breast",
    "duration_minutes": 20,
    "timestamp": "2024-01-01T10:00:00Z"
  }'
```

#### 获取跟踪条目
```bash
curl http://localhost:8000/api/tracking/test_user_123?days=7
```

#### 获取摘要
```bash
curl http://localhost:8000/api/tracking/test_user_123/summary?days=7
```

#### 情绪检查
```bash
curl -X POST http://localhost:8000/api/emotional-checkin \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "overwhelmed_level": 5,
    "anxiety_level": 4,
    "support_level": 6
  }'
```

#### 危机模式
```bash
curl -X POST http://localhost:8000/api/crisis \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "query": "Baby won't stop crying",
    "urgency": "high"
  }'
```

## 浏览器兼容性测试

### 桌面浏览器
- [ ] Chrome (最新版)
- [ ] Firefox (最新版)
- [ ] Safari (最新版)
- [ ] Edge (最新版)

### 移动浏览器
- [ ] iOS Safari
- [ ] Chrome Mobile
- [ ] Samsung Internet

## 性能测试

### 加载性能
- [ ] 首屏加载时间 < 3秒
- [ ] 资源压缩正常
- [ ] 图片优化
- [ ] 代码分割

### 运行时性能
- [ ] 页面切换流畅
- [ ] 动画 60fps
- [ ] 内存使用合理
- [ ] 无内存泄漏

## 安全测试

- [ ] API 密钥不暴露在前端
- [ ] 用户数据加密存储
- [ ] XSS 防护
- [ ] CSRF 防护
- [ ] 输入验证

## 测试脚本

### 自动化测试（可选）

创建 `test.sh` 脚本：

```bash
#!/bin/bash

echo "Starting tests..."

# 测试后端健康
echo "Testing backend health..."
curl -f http://localhost:8000/health || exit 1

# 测试前端
echo "Testing frontend..."
curl -f http://localhost:3000 || exit 1

echo "All tests passed!"
```

## 已知问题

- [ ] 待修复的问题列表
- [ ] 待改进的功能

## 测试报告模板

### 测试日期: [日期]
### 测试人员: [姓名]
### 测试环境: 
- 后端版本: [版本]
- 前端版本: [版本]
- 浏览器: [浏览器和版本]
- 操作系统: [OS]

### 测试结果
- 通过: [数量]
- 失败: [数量]
- 跳过: [数量]

### 问题记录
1. [问题描述]
   - 严重程度: [高/中/低]
   - 状态: [待修复/已修复]

## 持续集成建议

建议设置 CI/CD 流程：
1. 代码提交时自动运行测试
2. 构建检查
3. 代码质量检查
4. 自动部署到测试环境
