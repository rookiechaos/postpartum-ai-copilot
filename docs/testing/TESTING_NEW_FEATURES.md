# 新功能测试指南
## Testing Guide for New Features

### 已完成的功能

1. **WebSocket 实时通信** ✅
   - 后端：`backend/services/websocket_manager.py`
   - 后端路由：`backend/api/websocket_routes.py`
   - 前端：`frontend/src/utils/websocketManager.js`
   - 集成到任务队列，实时推送任务状态

2. **通知和提醒系统** ✅
   - 后端服务：`backend/services/notification_service.py`
   - 后端路由：`backend/api/notification_routes.py`
   - Background worker: `workers/notification_worker.py`
   - 数据库模型：`NotificationDB`
   - 前端组件：`frontend/src/components/NotificationManager.jsx`
   - 支持智能喂养提醒、情绪检查提醒

3. **数据导出功能** ✅
   - 后端服务：`backend/services/data_export_service.py`
   - 后端路由：`backend/api/data_export_routes.py`
   - 支持 JSON、CSV、PDF 格式
   - GDPR 合规

4. **PWA 优化** ✅
   - 增强的 Service Worker：`frontend/public/sw.js`
   - 离线支持、后台同步
   - 推送通知支持
   - 改进的缓存策略

5. **数据可视化增强** ✅
   - 改进的图表组件：`frontend/src/components/Charts.jsx`
   - 更好的数据处理和可视化

### 测试步骤

#### 1. 启动后端服务器

```bash
cd Postpartum/backend
python -m uvicorn main:app --reload --port 8000
```

#### 2. 启动前端开发服务器

```bash
cd Postpartum/frontend
npm install  # 如果还没安装依赖
npm run dev
```

#### 3. 运行自动化测试

```bash
cd Postpartum
python3 test_all_features.py
```

测试脚本会测试：
- 健康检查
- 用户认证
- 追踪功能
- 任务队列
- WebSocket 连接
- 通知系统
- 数据导出

#### 4. 手动测试 WebSocket

1. 打开浏览器开发者工具
2. 登录应用
3. 发送一条聊天消息
4. 观察 WebSocket 连接和实时更新

#### 5. 测试通知系统

1. 在应用中创建智能喂养提醒
2. 检查通知是否创建成功
3. 等待通知触发（或手动触发通知工作器）

#### 6. 测试数据导出

1. 登录应用
2. 访问 `/api/export/json` 端点（需要认证）
3. 检查导出的数据是否完整

#### 7. 测试 PWA 功能

1. 在移动设备或 Chrome DevTools 中打开应用
2. 检查是否可以安装为 PWA
3. 断开网络连接，测试离线功能
4. 检查 Service Worker 是否正常工作

### API 端点

#### WebSocket
- `ws://localhost:8000/ws?token=<jwt_token>`

#### 通知
- `POST /api/notifications` - 创建通知
- `GET /api/notifications` - 获取用户通知
- `POST /api/notifications/smart/feeding` - 创建智能喂养提醒
- `POST /api/notifications/smart/mood-check` - 创建情绪检查提醒
- `DELETE /api/notifications/{id}` - 禁用通知

#### 数据导出
- `GET /api/export/json` - 导出为 JSON
- `GET /api/export/csv` - 导出为 CSV
- `GET /api/export/pdf` - 导出为 PDF（需要 reportlab）

### 启动通知工作器

通知工作器需要单独运行来处理待发送的通知：

```bash
cd Postpartum/backend
python -m workers.notification_worker
```

或者集成到主应用中（需要修改启动脚本）。

### 注意事项

1. **WebSocket 测试**：需要 `websocket-client` Python 包（测试脚本中可选）
2. **PDF 导出**：需要 `reportlab` 包：`pip install reportlab`
3. **通知工作器**：需要单独运行或集成到主应用启动流程中
4. **数据库迁移**：新添加的 `NotificationDB` 模型需要运行数据库迁移

### 数据库迁移

如果数据库已存在，需要添加新的表：

```python
# 在 Python 交互式环境中运行
from Postpartum.backend.models.database import init_db
init_db()  # 这会创建所有缺失的表
```

### 故障排除

1. **WebSocket 连接失败**：检查 JWT token 是否有效
2. **通知不发送**：确保通知工作器正在运行
3. **数据导出失败**：检查用户是否有数据，以及认证是否有效
4. **PWA 不工作**：检查 Service Worker 是否正确注册，manifest.json 是否存在
