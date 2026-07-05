# 测试文档

## 测试概览

Postpartum AI Copilot 项目包含多种测试方法，用于验证不同层面的功能。

## 最新测试 (2026-01-22)

### 代码质量改进测试 ✅
- **Test scripts**: `tests/internal/test_code_quality_improvements_internal.py`
- **测试环境**: product conda环境，内部测试（不暴露端口）
- **测试结果**: ✅ 6/6 测试通过
- **测试内容**:
  - 数据库辅助函数测试
  - TrackingService重构测试
  - 数据库索引测试
  - 路由文件导入测试
  - 服务容器测试
  - 错误处理测试

See [Code Quality Test Report](../backend/development/CODE_QUALITY_TEST_REPORT.md)

---

## 测试类型

### 1. 单元测试

测试核心服务功能，不依赖外部服务。

**运行方式：**
```bash
cd Postpartum
python run_tests.py
```

**测试内容：**
- 验证系统（SuggestionValidator）
- 陪伴层（CompanionLayer）
- 信息缓冲层（InformationBuffer）
- 配置管理系统（Settings）
- 数据库依赖注入（Database Dependencies）
- 缓存服务（Cache Service）

### 2. 内部 API 测试 ⭐ 推荐

**无需启动服务器**，在进程内部完成所有 API 测试。

**运行方式：**
```bash
cd Postpartum
python test_internal_api.py
```

**优点：**
- 无需启动服务器
- 无需暴露端口
- 运行速度快
- 适合 CI/CD

**测试内容：**
- 健康检查
- 用户认证（注册、登录）
- 任务管理（创建、查询、取消）
- 聊天端点
- 用户上下文
- 个性化功能

### 3. Worker 测试

测试任务队列和 Worker 功能。

**运行方式：**
```bash
cd Postpartum
python test_worker.py
```

**测试内容：**
- 任务创建
- 任务认领
- 任务完成
- 任务失败和重试
- 任务优先级
- 任务取消
- 超时检测

### 4. API 集成测试

测试完整的 HTTP API 端点（需要运行服务器）。

**运行方式：**
```bash
# 终端 1: 启动服务器
cd backend
uvicorn main:app --reload

# 终端 2: 运行测试
cd Postpartum
python test_api.py
```

**测试内容：**
- 所有 HTTP 端点
- 请求/响应格式
- 错误处理
- 认证流程

### 5. AI 提供商测试

测试不同 AI 提供商的连接和基本响应。

**运行方式：**
```bash
cd Postpartum
python test_ai_providers.py
```

**测试内容：**
- OpenAI 连接
- Claude 连接
- Gemini 连接
- 基本响应生成

## 测试环境设置

### 环境变量

确保 `backend/.env` 文件包含必要的配置：

```bash
# 数据库
DATABASE_URL=sqlite:///./postpartum_test.db

# AI 提供商（可选，某些测试需要）
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# JWT
JWT_SECRET_KEY=test_secret_key
```

### 数据库

测试使用独立的测试数据库（SQLite），不会影响生产数据。

## 测试最佳实践

### 1. 运行顺序

推荐测试运行顺序：
1. 单元测试（最快）
2. 内部 API 测试（推荐）
3. Worker 测试
4. AI 提供商测试（需要 API 密钥）
5. API 集成测试（需要运行服务器）

### 2. CI/CD 集成

在 CI/CD 中使用内部 API 测试：

```yaml
# GitHub Actions 示例
- name: Run Internal API Tests
  run: |
    cd Postpartum
    python test_internal_api.py
```

### 3. 测试数据清理

测试会自动清理创建的测试数据，但建议：
- 使用独立的测试数据库
- 定期清理测试用户和任务
- 使用时间戳生成唯一标识符

## 测试覆盖率

当前测试覆盖：
- ✅ 核心服务功能
- ✅ API 端点
- ✅ 任务队列
- ✅ 认证系统
- ✅ Worker 功能
- ✅ 配置管理系统
- ✅ 数据库会话管理
- ✅ 错误处理中间件
- ✅ 性能监控
- ✅ 健康检查
- ⚠️ AI 提供商（需要 API 密钥）
- ⚠️ 完整工作流（需要运行服务器）

## 故障排除

### 测试失败常见原因

1. **数据库连接错误**
   - 检查 `DATABASE_URL` 配置
   - 确保数据库文件可写

2. **认证失败**
   - 检查 `JWT_SECRET_KEY` 配置
   - 确保测试用户创建成功

3. **AI API 错误**
   - 检查 API 密钥是否正确
   - 检查 API 配额是否充足
   - 某些测试可以跳过 AI API 测试

4. **导入错误**
   - 确保在正确的目录运行测试
   - 检查 Python 路径设置

## 编写新测试

### 测试模板

```python
def test_new_feature():
    """测试新功能"""
    print("\n=== 测试新功能 ===")
    # 测试代码
    assert condition, "错误消息"
    print("✅ 测试通过")
    return True
```

### 添加到测试套件

在 `run_all_tests()` 函数中添加：

```python
tests = [
    ("新功能", test_new_feature),
    # ... 其他测试
]
```

## 压力测试 (Stress Testing)

### 运行压力测试

使用专门的 stress test 脚本进行性能测试：

```bash
cd Postpartum
python stress_test.py
```

**测试选项：**
- `--endpoint`: 要测试的端点 (默认: /api/chat)
- `--concurrent`: 并发用户数 (默认: 10)
- `--requests`: 每个用户的请求数 (默认: 50)
- `--duration`: 测试持续时间（秒）(默认: 60)
- `--base-url`: API 基础 URL (默认: http://localhost:8000)

**示例：**
```bash
# 测试聊天端点，10个并发用户，每个用户50个请求
python stress_test.py --endpoint /api/chat --concurrent 10 --requests 50

# 测试追踪端点，20个并发用户，持续60秒
python stress_test.py --endpoint /api/tracking --concurrent 20 --duration 60

# 测试健康检查端点，100个并发用户
python stress_test.py --endpoint /health --concurrent 100 --requests 100
```

**测试报告包括：**
- 总请求数
- 成功/失败请求数
- 平均响应时间
- P50/P95/P99 响应时间
- 请求速率 (RPS)
- 错误率
- 响应时间分布

### 压力测试最佳实践

1. **逐步增加负载**：从低并发开始，逐步增加
2. **监控系统资源**：观察 CPU、内存、数据库连接数
3. **测试不同端点**：测试各个端点的性能表现
4. **测试错误处理**：验证系统在负载下的错误处理能力
5. **测试恢复能力**：停止负载后验证系统恢复

## 持续改进

- 定期更新测试用例
- 增加测试覆盖率
- 优化测试性能
- ✅ 添加性能测试
- ✅ 添加负载测试
