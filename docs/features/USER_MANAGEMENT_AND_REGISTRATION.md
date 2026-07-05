# 用户管理与注册说明

## 一、后端（API）状态：OK

### 1. 注册 (Register)

- **端点**: `POST /api/auth/register`
- **请求体**: `{ "email": "用户邮箱", "password": "密码", "user_id": "可选，不传则自动生成" }`
- **校验**:
  - 邮箱格式（Pydantic + InputSanitizer）
  - 密码强度：至少 8 位，需包含大小写字母和数字（PasswordValidator）
- **逻辑**: `AuthService.create_user` 检查邮箱是否已存在、生成 `user_id`、哈希密码（pbkdf2_sha256）、写入 `UserDB`
- **响应**: 201，返回用户信息（不含密码）；邮箱重复时由 `ValidationError` 经全局异常处理返回 400

### 2. 登录 (Login)

- **端点**: `POST /api/auth/login`
- **请求体**: `{ "email": "邮箱", "password": "密码" }`
- **逻辑**: 校验密码、记录设备与登录日志、签发 JWT access_token 与 refresh_token
- **响应**: 200，返回 `access_token`、`refresh_token`、`requires_2fa` 等

### 3. Token 刷新

- **端点**: `POST /api/auth/refresh`（需 Bearer refresh_token）
- **响应**: 新的 access_token 与 refresh_token

### 4. 当前用户信息

- **端点**: `GET /api/auth/me`（需 Bearer access_token）
- **响应**: 当前登录用户信息

### 5. 路由与依赖

- `main.py` 已挂载 `auth_router`
- `auth_service`、`device_service`、`two_factor_auth_service` 通过 `dependencies.service_registry` 注册并在 auth 路由中使用

**结论**：后端对用户的**注册、登录、Token 刷新、当前用户**管理完整，注册与登录接口可用。

---

## 二、前端状态：已接入（必须先注册/登录再使用）

### 1. API 封装

- `frontend/src/utils/api.js` 提供：
  - `register(email, password, user_id)` → 调用 `POST /api/auth/register`
  - `login(email, password)` → 调用 `POST /api/auth/login`，写入 `access_token`、`refresh_token`
  - `getCurrentUser()` → 调用 `GET /api/auth/me`，用于获取当前用户的 `user_id`
  - Token 与 `userId` 通过 `localStorage` 管理，请求头自动带 `Authorization: Bearer <token>`
  - `logout()` 清除 token 与 `userId`

### 2. 当前实际行为

- **Auth.jsx**：登录/注册页（同一界面切换），使用代码内注册机制（`api.register` / `api.login`）。
- **App.jsx**：
  - 启动时检查 `api.isAuthenticated()`；若无 token 或无法通过 `/api/auth/me` 取得用户，则展示 **Auth** 页。
  - 登录/注册成功后，从 `/api/auth/me` 取得 `user_id` 并写入 `localStorage`，主应用全程使用该 **后端用户 ID**。
  - 未登录时不再生成本地 `user_${Date.now()}`，必须先注册或登录才能进入主应用。
- **Settings**：提供「Log out」按钮，登出后清除 token 与 `userId`，回到 Auth 页。

### 3. 流程小结

- 注册：填写邮箱、密码 → `api.register()` → `api.login()` → `api.getCurrentUser()` → 存储 `user_id` → 进入主应用。
- 登录：填写邮箱、密码 → `api.login()` → `api.getCurrentUser()` → 存储 `user_id` → 进入主应用。
- 登出：Settings 中点击 Log out → `api.logout()` → 清除 token 与 `userId` → 回到 Auth 页。

---

## 三、总结

| 项目           | 状态 | 说明 |
|----------------|------|------|
| 后端注册 API   | OK   | `/api/auth/register` 可用，校验、存储、异常（如重复邮箱 400）正常 |
| 后端登录 API   | OK   | `/api/auth/login` 可用，返回 JWT |
| 后端 Token/me  | OK   | refresh、/api/auth/me 可用 |
| 前端 API 封装  | OK   | `api.register()`、`api.login()`、token 与 `userId` 管理已存在 |
| 前端注册/登录页 | 已实现 | Auth.jsx：登录 + 注册，使用代码内注册机制 |
| 前端当前身份   | 后端 userId | 必须登录/注册后使用，主应用使用 `/api/auth/me` 返回的 `user_id` |

**结论**：产品已实现**必须先注册/登录再使用**；注册与登录均使用代码内既有机制（后端 `/api/auth/register`、`/api/auth/login`），前端通过 Auth 页与 App 认证门控接入。
