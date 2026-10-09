# 2026-10-09 review fixes

基于 `510fe2c873d780282fc556d09693f1ca2d4ddfc8` 的复审，修复以下 13 项问题。

| # | 问题 | 修复后的行为 |
|---|---|---|
| 1 | 密码正确即可绕过 2FA 获得令牌 | 启用 2FA 的账号必须同时提交正确的验证器或备用码。密码验证阶段只返回 `requires_2fa`，不签发 access/refresh token；HTTP、WebSocket 和 refresh 校验当前认证器版本，旧的仅密码令牌失效。 |
| 2 | API 离线缓存可跨账号复用 | Service Worker 对 API 和携带 Authorization 的请求使用 `no-store`；激活时清理旧应用缓存，退出或重新登录时删除私人缓存。API 响应也设置 `Cache-Control: no-store`。 |
| 3 | 家庭共享忽略授权开关 | 默认不共享。原始记录和 AI 摘要仅使用明确设置 `share_tracking=true` 的成员数据；成员只能更改自己的共享偏好，关闭后立即影响后续请求。 |
| 4 | 作者筛选暴露匿名帖归属 | 公开作者筛选排除匿名帖；新增鉴权的 `/api/community/posts/mine`，只查询当前用户自己的帖子。 |
| 5 | 客户端可自行开通付费订阅 | 暂停 premium/enterprise 开通，保留免费方案；忽略客户端提供的支付订阅 ID。旧的未经支付验证的付费记录不能授予高级权限。 |
| 6 | PayPal webhook 没有验签 | 使用 PayPal OAuth 和签名验证 API，在返回 `SUCCESS` 后才更新订阅。配置缺失、签名错误和验证服务不可用均不更新状态。订阅匹配同时限定支付平台。Stripe 验证原始请求体签名及时间窗口，开发模式也不能跳过验证。 |
| 7 | OpenAI 与 LangChain 版本约束冲突 | OpenAI 固定为 1.6.1，满足 langchain-openai 0.0.2 的 `>=1.6.1,<2.0.0`；固定兼容的 httpx，NumPy 使用支持 Python 3.12 的 1.26.4。 |
| 8 | 默认日志路径导致导入失败 | 以项目根目录解析日志和向量库路径，保留旧默认路径的兼容性，限制其位于 `do-not-upload` 内并创建父目录。SQLite 的旧相对路径也在 API 和 worker 中保持一致。 |
| 9 | Docker worker 缺少 JWT 配置 | API 和 worker 共享必要环境配置，Compose 要求提供 JWT 密钥；修正 worker 容器路径，镜像包含 worker 和翻译资源，并共享私人运行数据卷。 |
| 10 | 迟到结果覆盖已取消任务 | 结果提交必须匹配 processing 状态、worker 和执行开始时间；取消、超时和结果更新使用带条件的原子更新。旧执行不能完成或重试新一轮任务。 |
| 11 | 未审核帖子可公开读取 | 单帖读取同样检查审核状态，非 approved 帖子仅允许作者读取。 |
| 12 | 家庭待办进入 AI 队列后反复失败 | AI worker 只查询和认领支持的三种 AI 任务；手工家庭待办保留待处理状态。 |
| 13 | 数据库异常向客户端暴露内部信息 | 生产环境内部异常只返回通用消息和空 details，包括被路由包装成 HTTP 5xx 的异常；验证错误也不返回或记录原始输入及异常上下文。 |

同时修复静态检查发现的管理权限、排序和 SQL 类型导入缺失，以及聊天、设置、语言选择和家庭分享组件中损坏的 JSX 标签或注释。

## 运行行为与配置

- 已启用 2FA 的账号需要重新登录并输入第二因素。启用或更换认证器后，先前的令牌不再满足当前验证要求；备用码使用后会持久化移除。
- 家庭成员默认不共享健康记录；需要在家庭界面主动打开共享开关。关闭不会撤回其他成员已经查看或另行保存的数据。
- **付费订阅尚未实现真实结账流程，因此保持关闭。** 重新开放需要服务端创建支付会话、绑定用户及价格/方案、验证支付状态后再赋予权益。不能通过修改按钮或客户端传入支付 ID 开放。
- 现有的付费记录只有服务端元数据明确包含 `payment_verified=true` 且 `verified_plan` 与方案一致时才满足权益验证；本次修改不会自行给旧记录添加该标记。Webhook 只更新已绑定的订阅状态，不创建付费权益。
- Stripe webhook 需要 `STRIPE_WEBHOOK_SECRET`。PayPal 需要 `PAYPAL_WEBHOOK_ID`、`PAYPAL_CLIENT_ID`、`PAYPAL_CLIENT_SECRET` 和 `PAYPAL_ENVIRONMENT`（`sandbox` 或 `live`）。实际密钥只放在被忽略的本地环境文件或部署环境中。
- Docker Compose 需要在宿主环境设置 `JWT_SECRET_KEY`。日志和向量数据限制在项目的 `do-not-upload` 目录中，容器内为 `/app/do-not-upload`。

协议及依赖依据：[PayPal 签名验证 API](https://developer.paypal.com/api/webhooks/v1/verify-webhook-signature-post)、[Stripe webhook 签名说明](https://docs.stripe.com/events/manage-webhook-endpoints)、[langchain-openai 0.0.2 发布元数据](https://pypi.org/pypi/langchain-openai/0.0.2/json)。

## 验证结果与范围

```bash
python tests/regression/security_checks.py
node --test tests/regression/frontend_security.test.cjs
python -m unittest discover -s tests/privacy -v
ruff check --select E9,F63,F7,F82 backend core workers tests/regression/security_checks.py
./check-privacy.sh
```

- 后端隔离回归：33 项通过。使用真实路由、SQLAlchemy 查询和状态更新；配置、支付网络、JWT/TOTP 外部依赖为受控 fixture。认证测试执行原始方法体，不验证第三方加密库本身。
- 前端 Service Worker 和 API 客户端回归：9 项通过，覆盖缓存、离线回退、退出、2FA 登录及刷新。
- 隐私扫描器回归：14 项通过。待发布工作树、暂存区和分支可达历史的隐私扫描未发现匹配的真实 IP、私人邮箱、个人目录路径或凭证；忽略的本地文件及不可达对象不在此结论范围内。
- Python 致命静态错误检查通过；全部前端源文件的 JavaScript/JSX 语法检查通过；Docker Compose 配置解析通过。
- **未执行完整依赖安装、完整应用集成测试、前端生产构建或 Docker 镜像构建/启动。** 依赖下载未获批准，当前环境也没有完整后端依赖和前端 node_modules。版本约束修复不等于完整依赖解析已验证；本次测试不证明真实支付网络、实际 JWT/TOTP 库或 PostgreSQL 并发行为已经端到端验证。
