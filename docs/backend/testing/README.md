# 测试文档

## 概述

本目录包含 Postpartum AI Copilot 后端的所有测试文件。测试使用 pytest 框架，支持异步测试。

## 最新测试 (2026-01-22)

### 代码质量改进测试 ✅
- **测试脚本**: `test_code_quality_improvements_internal.py`
- **测试环境**: product conda环境，内部测试（不暴露端口）
- **测试结果**: ✅ 6/6 测试通过
- **详细报告**: [代码质量测试报告](../development/CODE_QUALITY_TEST_REPORT.md)

---

## 测试文件结构

```
tests/
├── __init__.py
├── conftest.py              # 测试配置和fixtures
├── test_error_handling.py   # 异常处理测试
├── test_tracking_service.py # 跟踪服务测试（已重构）
├── test_feedback_service.py # 反馈服务测试
├── test_analytics_service.py # 分析服务测试
├── test_task_queue.py       # 任务队列测试
├── test_auth_service.py     # 认证服务测试
├── test_settings.py         # 配置测试
├── test_health_check.py     # 健康检查测试
└── test_api_routes.py       # API路由集成测试

# 内部测试脚本（根目录）
test_code_quality_improvements_internal.py  # 代码质量改进测试（最新）
```

## 运行测试

### 运行所有测试

```bash
cd backend
pytest
```

### 运行特定测试文件

```bash
pytest tests/test_feedback_service.py
```

### 运行特定测试函数

```bash
pytest tests/test_feedback_service.py::test_create_feedback
```

### 运行带标记的测试

```bash
# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 跳过需要API密钥的测试
pytest -m "not requires_api"
```

### 查看测试覆盖率

```bash
pytest --cov=services --cov=models --cov-report=html --cov-report=term-missing
```

## 测试分类

### 单元测试 (Unit Tests)

- `test_error_handling.py` - 异常类测试
- `test_feedback_service.py` - 反馈服务单元测试
- `test_analytics_service.py` - 分析服务单元测试
- `test_task_queue.py` - 任务队列单元测试
- `test_auth_service.py` - 认证服务单元测试
- `test_settings.py` - 配置类测试
- `test_health_check.py` - 健康检查服务测试

### 集成测试 (Integration Tests)

- `test_api_routes.py` - API端点集成测试
- `test_tracking_service.py` - 跟踪服务集成测试

## 测试Fixtures

### 数据库相关

- `test_db_session` - 测试数据库会话
- `test_engine` - 测试数据库引擎
- `test_settings` - 测试配置

### 数据相关

- `mock_user_id` - 模拟用户ID
- `sample_tracking_entry` - 示例跟踪条目
- `sample_user_context` - 示例用户上下文
- `mock_ai_response` - 模拟AI响应

### 服务相关

- `reset_container` - 重置服务容器
- `mock_cache` - 模拟缓存服务
- `auth_service` - 认证服务实例

## 测试最佳实践

1. **隔离性**: 每个测试应该独立运行，不依赖其他测试的状态
2. **清理**: 使用 `cleanup_test_data` fixture 自动清理测试数据
3. **异步**: 使用 `@pytest.mark.asyncio` 标记异步测试
4. **Mock**: 对于外部依赖（如AI API），使用mock避免实际调用
5. **断言**: 使用明确的断言，验证期望的行为

## 添加新测试

### 1. 创建测试文件

```python
"""
Unit tests for YourService
"""

import pytest
from services.your_service import YourService


@pytest.mark.asyncio
async def test_your_function(test_db_session):
    """Test description"""
    service = YourService()
    result = await service.your_function(test_db_session)
    assert result is not None
```

### 2. 使用现有Fixtures

```python
def test_with_user(test_db_session, mock_user_id):
    # 使用提供的fixtures
    pass
```

### 3. 创建自定义Fixtures

在 `conftest.py` 中添加：

```python
@pytest.fixture
def custom_fixture():
    """Custom fixture description"""
    return CustomData()
```

## 持续集成

测试应该在以下情况下运行：

1. 提交代码前（pre-commit hook）
2. Pull Request 创建时
3. 代码合并到主分支前

## 故障排除

### 数据库锁定错误

如果遇到 SQLite 数据库锁定错误，确保：
- 所有测试会话都已关闭
- 使用 `test_db_session` fixture 而不是直接创建会话

### 导入错误

如果遇到导入错误：
- 确保 `backend` 目录在 Python 路径中
- 检查 `conftest.py` 中的路径设置

### 异步测试失败

确保：
- 使用 `@pytest.mark.asyncio` 装饰器
- pytest-asyncio 已安装
- `pytest.ini` 中配置了 `asyncio_mode = auto`

## 测试覆盖率目标

- 服务层: > 80%
- 模型层: > 90%
- API路由: > 70%

## 相关文档

- [pytest 文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
