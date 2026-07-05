# 移动应用（原生）和社区功能实施计划

**创建日期**: 2026-01-22  
**状态**: 规划中

---

## 📱 移动应用（原生）

### 技术栈选择

#### 推荐方案: React Native
- **跨平台**: iOS 和 Android 一套代码
- **性能**: 接近原生性能
- **生态**: 丰富的第三方库
- **开发效率**: 与现有 React 前端技术栈一致

#### 备选方案: Flutter
- **性能**: 优秀的性能表现
- **UI**: 精美的 Material Design
- **缺点**: 需要学习 Dart 语言

**决定**: 使用 **React Native**

---

### 移动应用架构

```
mobile/
├── src/
│   ├── screens/          # 屏幕组件
│   │   ├── HomeScreen.js
│   │   ├── ChatScreen.js
│   │   ├── TrackingScreen.js
│   │   ├── CommunityScreen.js
│   │   └── ProfileScreen.js
│   ├── components/       # 可复用组件
│   ├── navigation/       # 导航配置
│   ├── services/         # API 服务
│   ├── store/            # 状态管理 (Zustand)
│   ├── utils/            # 工具函数
│   └── constants/        # 常量配置
├── android/              # Android 原生代码
├── ios/                  # iOS 原生代码
├── package.json
└── app.json
```

---

### 核心功能实现

#### 1. 认证和授权
- JWT Token 管理
- 自动刷新 Token
- 生物识别登录（Face ID / Touch ID）
- 安全存储

#### 2. AI 聊天
- 实时对话界面
- 语音输入支持
- 消息历史
- 夜间模式

#### 3. 追踪功能
- 快速记录（喂养、尿布、睡眠）
- 数据可视化
- 趋势分析

#### 4. 社区功能
- 帖子浏览
- 发帖和评论
- 点赞和收藏
- 关注用户
- 话题分类

#### 5. 通知推送
- 本地通知
- 推送通知（Firebase / OneSignal）
- 智能提醒

---

## 👥 社区功能

### 功能需求

#### 1. 帖子系统
- 创建帖子（文字、图片）
- 编辑和删除帖子
- 帖子分类（经验分享、问题求助、心情日记等）
- 帖子搜索

#### 2. 互动功能
- 点赞/取消点赞
- 评论和回复
- 收藏帖子
- 分享帖子

#### 3. 用户关系
- 关注/取消关注
- 用户资料页
- 粉丝和关注列表

#### 4. 内容管理
- 内容审核（NSFW检测）
- 举报功能
- 管理员权限

#### 5. 话题和标签
- 话题分类
- 标签系统
- 热门话题

---

### 数据库设计

#### 社区相关表

1. **posts** - 帖子表
   - id, user_id, title, content, images, category, tags
   - created_at, updated_at, like_count, comment_count
   - is_deleted, is_pinned

2. **comments** - 评论表
   - id, post_id, user_id, parent_id (回复), content
   - created_at, updated_at, like_count

3. **post_likes** - 帖子点赞表
   - id, post_id, user_id, created_at

4. **comment_likes** - 评论点赞表
   - id, comment_id, user_id, created_at

5. **post_favorites** - 收藏表
   - id, post_id, user_id, created_at

6. **user_follows** - 关注表
   - id, follower_id, following_id, created_at

7. **topics** - 话题表
   - id, name, description, post_count, created_at

8. **post_topics** - 帖子话题关联表
   - id, post_id, topic_id

---

### API 端点设计

#### 社区 API

```
POST   /api/community/posts              # 创建帖子
GET    /api/community/posts              # 获取帖子列表
GET    /api/community/posts/{id}         # 获取帖子详情
PUT    /api/community/posts/{id}         # 更新帖子
DELETE /api/community/posts/{id}          # 删除帖子

POST   /api/community/posts/{id}/like     # 点赞/取消点赞
POST   /api/community/posts/{id}/favorite # 收藏/取消收藏

POST   /api/community/posts/{id}/comments      # 创建评论
GET    /api/community/posts/{id}/comments      # 获取评论列表
PUT    /api/community/comments/{id}            # 更新评论
DELETE /api/community/comments/{id}            # 删除评论
POST   /api/community/comments/{id}/like        # 点赞评论

POST   /api/community/users/{id}/follow   # 关注/取消关注
GET    /api/community/users/{id}/followers    # 获取粉丝列表
GET    /api/community/users/{id}/following     # 获取关注列表

GET    /api/community/topics              # 获取话题列表
GET    /api/community/topics/{id}/posts   # 获取话题下的帖子

GET    /api/community/feed                # 获取动态流（关注的人的帖子）
GET    /api/community/search               # 搜索帖子
```

---

## 📋 实施步骤

### 阶段 1: 社区功能后端 (Week 1-2)

1. **数据库模型**
   - [ ] 创建社区相关数据库模型
   - [ ] 添加索引优化查询

2. **后端服务**
   - [ ] `community_service.py` - 社区核心服务
   - [ ] `post_service.py` - 帖子服务
   - [ ] `comment_service.py` - 评论服务
   - [ ] `user_relationship_service.py` - 用户关系服务

3. **API 路由**
   - [ ] `api/community_routes.py` - 社区 API

4. **内容安全**
   - [ ] 集成 NSFW 检测
   - [ ] 内容审核机制

---

### 阶段 2: 社区功能前端 (Week 2-3)

1. **Web 前端**
   - [ ] `CommunityScreen.jsx` - 社区主页
   - [ ] `PostCard.jsx` - 帖子卡片
   - [ ] `PostDetail.jsx` - 帖子详情
   - [ ] `CreatePost.jsx` - 创建帖子
   - [ ] `CommentSection.jsx` - 评论区域

2. **功能实现**
   - [ ] 帖子列表和分页
   - [ ] 点赞和收藏
   - [ ] 评论和回复
   - [ ] 用户关注

---

### 阶段 3: 移动应用基础 (Week 3-4)

1. **项目初始化**
   - [ ] 初始化 React Native 项目
   - [ ] 配置开发环境
   - [ ] 设置导航 (React Navigation)
   - [ ] 配置状态管理 (Zustand)

2. **基础功能**
   - [ ] 认证和登录
   - [ ] API 集成
   - [ ] 基础 UI 组件库

---

### 阶段 4: 移动应用核心功能 (Week 4-6)

1. **核心屏幕**
   - [ ] HomeScreen - 主页
   - [ ] ChatScreen - AI 聊天
   - [ ] TrackingScreen - 追踪
   - [ ] CommunityScreen - 社区
   - [ ] ProfileScreen - 个人资料

2. **功能实现**
   - [ ] AI 聊天集成
   - [ ] 追踪功能
   - [ ] 社区功能集成
   - [ ] 推送通知

---

### 阶段 5: 测试和优化 (Week 6-7)

1. **测试**
   - [ ] 单元测试
   - [ ] 集成测试
   - [ ] 端到端测试

2. **优化**
   - [ ] 性能优化
   - [ ] UI/UX 优化
   - [ ] 错误处理

---

## 🛠️ 技术依赖

### 移动应用依赖

```json
{
  "react-native": "^0.73.0",
  "@react-navigation/native": "^6.1.0",
  "@react-navigation/stack": "^6.3.0",
  "@react-navigation/bottom-tabs": "^6.5.0",
  "zustand": "^4.4.0",
  "axios": "^1.6.0",
  "react-native-push-notification": "^8.1.0",
  "@react-native-async-storage/async-storage": "^1.19.0",
  "react-native-image-picker": "^7.0.0"
}
```

### 后端新增依赖

```txt
# 社区功能可能需要
Pillow>=10.0.0  # 图片处理
```

---

## 📝 注意事项

1. **隐私保护**
   - 社区内容需要用户明确同意
   - 敏感信息自动过滤
   - 匿名选项

2. **内容安全**
   - 所有帖子通过 NSFW 检测
   - 自动内容审核
   - 举报机制

3. **性能优化**
   - 图片压缩和 CDN
   - 分页加载
   - 缓存策略

4. **移动端优化**
   - 离线支持
   - 数据同步
   - 推送通知

---

## ✅ 完成标准

- [ ] 社区功能后端完整实现
- [ ] 社区功能前端（Web）完整实现
- [ ] 移动应用（React Native）基础框架
- [ ] 移动应用核心功能集成
- [ ] 社区功能在移动端可用
- [ ] 所有功能测试通过
- [ ] 文档完整

---

## 📚 相关文档

- [React Native 官方文档](https://reactnative.dev/)
- [React Navigation 文档](https://reactnavigation.org/)
- [Zustand 文档](https://zustand-demo.pmnd.rs/)
