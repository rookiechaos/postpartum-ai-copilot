# 2026-10-10 review fixes

基于 `235a4c9134688b4656b80f3a626d534549d75360` 的复审，修复以下 9 项问题。

| # | 问题 | 修复后的行为 |
|---|---|---|
| 1 | 未验证的注册邮箱可以获得管理员权限 | 管理权限只检查部署环境中的 `ADMIN_USER_IDS`。注册时由服务端生成账户 ID，忽略客户端传入的 ID；旧 `ADMIN_EMAILS` 不再授予任何权限。 |
| 2 | 已建立的 WebSocket 在令牌过期、2FA 变化或账户停用后仍可使用 | 握手、每条入站消息和所有私人推送重新验证令牌及当前账户。空闲连接每 30 秒复查，失效时关闭并移除订阅。 |
| 3 | 公开健康检查返回内部错误及系统诊断 | `/health` 仅返回存活状态；`/api/monitoring/health` 仅返回数据库就绪状态及时间，失败返回 503。诊断详情和系统指标要求管理员权限，组件错误均为通用消息。 |
| 4 | 情绪检查向字典接口传入 Pydantic 模型，导致 500 | 路由将验证后的模型转换为 JSON 字典，用户身份仍来自 JWT，正常提交能调用 AI 并解析结果。 |
| 5 | 旧账号迟到的响应体仍可进入新会话 | JSON、语音文本和音频读取完成后再次检查会话；迟到的错误也不能退出后继账号。登录变更重建私人页面状态，清理旧页面的异步读取；同一账号刷新保留页面。 |
| 6 | 设置保存的前后端请求格式不一致 | 接口接受 `{context, user_id?}`，服务端使用 JWT 账户，拒绝其他用户 ID。设置可持久化并读取；欢迎页等待保存成功再记录完成状态，失败时允许重试。 |
| 7 | 通知 metadata 字段映射错误 | 请求模型、数据库 JSON 列和响应正确对应；循环通知也保留 metadata。 |
| 8 | AI 情绪评估失败被标成低风险 | 返回 `analysis_available=false`、`risk_level=unknown`、`escalation_needed=null` 及通用错误。页面明确显示评估不可用，提供重试入口和支持信息。 |
| 9 | 情绪检查错误分支的 toast 未定义 | 使用已有 ToastProvider 的 hook；请求失败可以正常显示错误和重试界面。 |

## 部署与兼容性

管理员需要由服务端操作人员明确授予，默认无人具有管理权限：

1. 创建并登录受控账户，从 `/api/auth/me` 获取该账户实际的 `user_id`。
2. 在部署环境或被忽略的本地环境文件中设置 `ADMIN_USER_IDS`，多个实际账户 ID 用逗号分隔，然后重启 API。Docker Compose 已转发此变量。
3. **不要将旧 `ADMIN_EMAILS` 自动转换为管理员 ID。** 需要独立确认现有账户确实由管理员控制；注册邮箱没有所有权验证，单凭邮箱匹配不能授权。

不修改已有账户 ID，不需要数据库迁移。公开注册的 `user_id` 输入为兼容旧客户端保留，但不再决定新账户的身份。移除管理员配置并重启 API 后，该账户不再通过管理权限检查。

`/api/monitoring/health/details` 提供受保护的完整组件诊断；`/metrics` 和 `/api/monitoring/{metrics,tasks,system}` 同样要求管理员。公开就绪探针的响应不再包含 `checks`，依赖旧结构的监控客户端需要更新。

启用、停用或更换 2FA 后，令牌携带的认证器版本必须与当前状态一致。前端在启用和停用后退出，要求重新登录。空闲 WebSocket 最迟在下一次 30 秒复查时关闭；发送或接收私人数据时会立即复查。

情绪检查调用方应先检查 `analysis_available`，不可把 `unknown` 或缺失的评估当成低风险。现有风险等级仍为非临床提示，本次修复不构成临床有效性验证。

## 验证范围

```bash
python -W ignore tests/regression/security_checks.py
python -W ignore tests/regression/followup_checks.py
python -W ignore tests/regression/review_235a4c9_checks.py
node --test tests/regression/frontend_security.test.cjs tests/regression/frontend_tasks.test.cjs
node --test tests/regression/frontend_review.test.cjs
python -m unittest discover -s tests/privacy -v
ruff check --select E9,F63,F7,F82 backend core workers tests/regression
./check-privacy.sh
```

- 后端隔离回归 71 项、前端回归 38 项、隐私扫描器测试 14 项通过。新增测试执行实际 HTTP/ASGI WebSocket 路由、SQLite 持久化、连接管理、AI 解析和前端组件处理函数，覆盖失败及正常路径。
- JSX 组件测试使用 TypeScript 转译器和受控 React hooks/元素树。转译器不在模块搜索路径时，通过 `REVIEW_TYPESCRIPT_PATH` 指定现有安装的位置；没有为测试新增或下载依赖。
- Python 致命静态错误检查、前端 JavaScript/JSX 语法及未定义名称检查、Docker Compose 配置解析通过。
- 隐私检查覆盖待发布工作树、暂存区、分支可达历史及提交元数据；未发现扫描规则匹配的真实 IP、私人邮箱、个人目录路径或凭证。忽略的本地运行数据、日志和不可达对象不在结论范围内。
- 未执行完整依赖安装、生产前端构建、真实浏览器或容器端到端测试。JWT/密码加密、AI 网络及认证依赖使用受控 fixture；不代表第三方加密库、真实供应商或 PostgreSQL 已完成集成验证。此前未获批准的依赖下载没有重试，付费订阅继续关闭。
