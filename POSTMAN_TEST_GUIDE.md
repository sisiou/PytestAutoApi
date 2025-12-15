# Postman 测试接口指南

## 接口信息

**接口路径**: `POST /api/chain/run`

**服务器地址**: `http://127.0.0.1:5000` (默认端口，根据实际配置调整)

**完整URL**: `http://127.0.0.1:5000/api/chain/run`

**注意**: `group_name` 参数现在需要在请求体（Body）中传递，而不是 URL 路径参数

---

## Postman 配置步骤

### 1. 创建新请求

1. 打开 Postman
2. 点击左上角 **"New"** → **"HTTP Request"**
3. 或使用快捷键 `Ctrl+N` (Windows) / `Cmd+N` (Mac)

### 2. 设置请求方法

- 在请求方法下拉菜单中选择 **POST**

### 3. 设置请求 URL

**URL 格式**: `http://127.0.0.1:5000/api/chain/run`

**示例**:
```
http://127.0.0.1:5000/api/chain/run
```

**注意**: `group_name` 参数需要在请求体中传递（见下方 Body 配置）

### 4. 设置请求头 (Headers)

在 **Headers** 标签页中添加：

| Key | Value |
|-----|-------|
| `Content-Type` | `application/json` |

### 5. 设置请求体 (Body)

1. 点击 **Body** 标签页
2. 选择 **raw**
3. 在右侧下拉菜单中选择 **JSON**
4. 输入 JSON 请求体（可选参数）

#### 最小请求（必需参数）

```json
{
  "group_name": "related_group_4"
}
```

#### 完整请求示例

```json
{
  "group_name": "related_group_4",
  "redis_url": "redis://127.0.0.1:6379/0",
  "tmp_dir": ".chain_out",
  "api_key": "your_api_key_here",
  "model": "deepseek-v3.2",
  "base_url": "https://api.dashscope.com/v1",
  "timeout": 3600,
  "skip_pytest": false,
  "stream": false,
  "only_file": "openapi_message_create.yaml"
}
```

#### 请求体参数说明

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `group_name` | string | **是** | - | 组名，如 `related_group_4`，会与基础路径拼接 |
| `redis_url` | string | 否 | `redis://127.0.0.1:6379/0` | Redis 连接 URL |
| `tmp_dir` | string | 否 | `.chain_out` | 临时目录 |
| `api_key` | string | 否 | 环境变量 | 大模型 API Key |
| `model` | string | 否 | `deepseek-v3.2` | 模型名称 |
| `base_url` | string | 否 | 默认值 | 模型网关 base_url |
| `timeout` | number | 否 | `3600` | 超时时间（秒） |
| `skip_pytest` | boolean | 否 | `false` | 仅生成用例，不执行 pytest |
| `stream` | boolean | 否 | `false` | 是否流式输出 |
| `only_file` | string | 否 | - | 只处理特定文件（逗号分隔） |

---

## 完整 Postman 配置示例

### 示例 1: 基本请求

**Method**: `POST`

**URL**: 
```
http://127.0.0.1:5000/api/chain/run
```

**Headers**:
```
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "group_name": "related_group_4"
}
```

### 示例 2: 带自定义 Redis URL

**Method**: `POST`

**URL**: 
```
http://127.0.0.1:5000/api/chain/run
```

**Headers**:
```
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "group_name": "related_group_4",
  "redis_url": "redis://127.0.0.1:6379/1",
  "tmp_dir": "custom_output"
}
```

### 示例 3: 仅生成用例，不执行测试

**Method**: `POST`

**URL**: 
```
http://127.0.0.1:5000/api/chain/run
```

**Headers**:
```
Content-Type: application/json
```

**Body** (raw, JSON):
```json
{
  "group_name": "related_group_4",
  "skip_pytest": true
}
```

---

## 预期响应

### 成功响应 (200 OK)

```json
{
  "success": true,
  "message": "链式测试执行成功",
  "group_name": "related_group_4",
  "api_dir": "multiuploads/split_openapi/openapi_API/related_group_4",
  "return_code": 0,
  "test_files": [
    {
      "file_path": ".chain_out/test_chain_openapi_message_create.py",
      "file_name": "test_chain_openapi_message_create.py",
      "test_count": 3,
      "test_cases": [
        {
          "name": "test_ai_case_1",
          "description": "发送文本消息给指定用户（正常场景）",
          "line_number": 50
        },
        {
          "name": "test_ai_case_2",
          "description": "发送消息_机器人对用户不可用_异常",
          "line_number": 120
        }
      ]
    }
  ],
  "test_metrics": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "skipped": 0,
    "error": 0,
    "duration_ms": 5000,
    "duration_human": "5.00s"
  },
  "failed_tests": [
    {
      "file": "test_chain_openapi_message_create.py",
      "test_name": "test_ai_case_2",
      "error": "AssertionError: HTTP期望400 实际200"
    }
  ],
  "summary": {
    "total_cases": 10,
    "passed_cases": 8,
    "failed_cases": 2,
    "success_rate": "80.0%",
    "duration": "5.00s"
  },
  "stdout_tail": "...",
  "stderr_tail": "..."
}
```

### 错误响应 - 缺少必需参数 (400)

```json
{
  "error": "参数缺失",
  "message": "请求体中必须包含 group_name 参数"
}
```

### 错误响应 - 目录不存在 (404)

```json
{
  "error": "API目录不存在",
  "message": "路径不存在: multiuploads/split_openapi/openapi_API/related_group_4",
  "api_dir": "multiuploads/split_openapi/openapi_API/related_group_4"
}
```

### 错误响应 - 执行失败 (500)

```json
{
  "error": "执行失败",
  "message": "错误信息...",
  "return_code": 1,
  "stdout": "...",
  "stderr": "...",
  "api_dir": "multiuploads/split_openapi/openapi_API/related_group_4",
  "test_files": [...],
  "test_metrics": {...},
  "failed_tests": [...]
}
```

---

## 测试步骤检查清单

- [ ] 确保 API 服务器已启动 (`python api_server.py`)
- [ ] 确认服务器地址和端口（默认 `http://127.0.0.1:5000`）
- [ ] 确认 `group_name` 对应的目录存在
- [ ] 设置正确的请求方法 (POST)
- [ ] 设置正确的 Content-Type 头
- [ ] 请求体格式为 JSON（如果提供）
- [ ] 检查响应状态码和响应体

---

## 常见问题

### Q1: 返回 404 错误
**A**: 检查 `group_name` 对应的目录是否存在：
- 路径应该是: `multiuploads/split_openapi/openapi_API/{group_name}`
- 确保该目录下有 OpenAPI 文件

### Q2: 返回 500 错误
**A**: 检查：
- Redis 服务是否运行
- 环境变量是否正确配置（如 `FEISHU_APP_ID`, `FEISHU_APP_SECRET`）
- 查看响应中的 `stderr` 字段获取详细错误信息

### Q3: 请求超时
**A**: 
- 增加 `timeout` 参数值（默认 3600 秒）
- 检查测试用例执行是否正常

### Q4: 如何查看完整的执行日志？
**A**: 
- 查看响应中的 `stdout_tail` 和 `stderr_tail` 字段
- 或查看服务器日志文件 `api_server.log`

---

## 快速测试命令（使用 curl）

如果不想使用 Postman，也可以使用 curl：

```bash
# 基本请求（必需包含 group_name）
curl -X POST http://127.0.0.1:5000/api/chain/run \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "related_group_4"
  }'

# 带参数的请求
curl -X POST http://127.0.0.1:5000/api/chain/run \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "related_group_4",
    "redis_url": "redis://127.0.0.1:6379/0",
    "skip_pytest": false
  }'
```

---

## 注意事项

1. **执行时间**: 测试用例生成和执行可能需要较长时间，请耐心等待
2. **超时设置**: 如果测试用例较多，建议增加 `timeout` 参数
3. **Redis 连接**: 确保 Redis 服务正常运行
4. **文件权限**: 确保服务器有权限读取和写入相关目录
5. **环境变量**: 确保必要的环境变量已配置（如 `FEISHU_APP_ID`, `FEISHU_APP_SECRET`）

