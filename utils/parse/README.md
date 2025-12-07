# API测试用例生成工具

这是一个智能API测试用例生成工具，支持从多种输入源生成测试用例，包括飞书URL、JSON文件和直接OpenAPI文档输入。

## 功能特点

- 支持从飞书URL下载API文档并生成测试用例
- 支持处理JSON格式的API文档
- 支持直接输入OpenAPI文档
- 支持业务场景和接口关联关系输入
- 自动生成YAML格式的测试用例
- 提供Web前端界面
- 提供命令行接口

## 文件结构

```
utils/parse/
├── feishu_parse.py           # 飞书URL解析和下载功能
├── ai.py                     # AI处理JSON生成OpenAPI文档、场景和接口关联
├── api_input_processor.py    # 统一的API输入处理器
├── test_case_generator.py    # 测试用例生成器
├── api_frontend.py           # 前端接口
├── main_integration.py       # 主集成脚本
└── README.md                 # 说明文档
```

## 使用方法

### 1. 命令行接口

#### 处理飞书URL
```bash
cd /Users/oss/code/PytestAutoApi/utils/parse
python main_integration.py feishu "https://open.feishu.cn/document/server-docs/contact-v3/user/create"
```

#### 处理JSON文件
```bash
cd /Users/oss/code/PytestAutoApi/utils/parse
python main_integration.py json ../../api/file1.json ../../api/file2.json
```

#### 处理OpenAPI文档
```bash
cd /Users/oss/code/PytestAutoApi/utils/parse
python main_integration.py openapi ../../openApi/openapi_file.yaml -s ../../openApi/scenes.json -r ../../openApi/relations.json
```

#### 启动前端服务
```bash
cd /Users/oss/code/PytestAutoApi/utils/parse
python main_integration.py frontend -H 127.0.0.1 -p 5000
```

### 2. Web前端接口

启动前端服务后，可以通过以下API接口进行交互：

#### 处理输入并生成测试用例
```http
POST /api/process
Content-Type: application/json

{
  "feishu_url": "https://open.feishu.cn/document/server-docs/contact-v3/user/create",
  "openapi_doc": "openapi: 3.0.0\ninfo:\n  title: 示例API...",
  "business_scenes": "{\"business_scenes\": {...}}",
  "api_relations": "{\"relation_info\": {...}}"
}
```

#### 上传文件并处理
```http
POST /api/upload
Content-Type: multipart/form-data

file: [JSON文件]
openapi_doc: [OpenAPI文档内容]
business_scenes: [业务场景内容]
api_relations: [接口关联关系内容]
```

#### 下载生成的文件
```http
GET /api/download/<filename>
```

#### 列出所有生成的文件
```http
GET /api/files
```

#### 预览文件内容
```http
GET /api/preview/<filename>
```

#### 健康检查
```http
GET /api/health
```

### 3. 直接使用Python模块

#### 使用API输入处理器
```python
from api_input_processor import APIInputProcessor

processor = APIInputProcessor()

# 处理飞书URL
result = processor.process_input(feishu_url="https://open.feishu.cn/document/...")

# 处理JSON文件
result = processor.process_input(json_files=["../../api/file1.json"])

# 处理OpenAPI文档
result = processor.process_input(openapi_doc="openapi: 3.0.0...")
```

#### 使用测试用例生成器
```python
from test_case_generator import TestCaseGenerator

generator = TestCaseGenerator()

# 从OpenAPI文档生成测试用例
output_path = generator.generate_all_test_cases(
    openapi_path="../../openApi/openapi_file.yaml",
    scene_path="../../openApi/scenes.json",
    relation_path="../../openApi/relations.json"
)
```

## 输出文件

工具会生成以下类型的文件：

1. **OpenAPI文档** (YAML格式): 标准的OpenAPI 3.0规范文档
2. **接口关联关系** (JSON格式): 描述接口之间的依赖关系和数据流转
3. **业务场景** (JSON格式): 描述基于接口的业务场景
4. **测试用例** (YAML格式): 包含基础API测试用例、场景测试用例和关联测试用例

## 依赖项

- Python 3.7+
- Flask (用于Web前端)
- PyYAML (用于YAML处理)
- requests (用于HTTP请求)
- openai (用于AI处理)
- python-dotenv (用于环境变量管理)

## 环境变量

在项目根目录创建`.env`文件，配置以下环境变量：

```
DASHSCOPE_API_KEY=your_api_key
BAILIAN_API_URL=your_api_url
BAILIAN_MODEL=your_model_name
```

## 示例

### 示例1: 从飞书URL生成测试用例

```bash
# 处理飞书URL
python main_integration.py feishu "https://open.feishu.cn/document/server-docs/contact-v3/user/create"

# 输出:
# 处理飞书URL: https://open.feishu.cn/document/server-docs/contact-v3/user/create
# 原始URL: https://open.feishu.cn/document/server-docs/contact-v3/user/create
# 转换后的API URL: https://open.feishu.cn/document_portal/v1/document/get_detail?fullPath=%2Fserver-docs%2Fcontact-v3%2Fuser%2Fcreate
# 生成的文件名: ../../api/server-docs_contact-v3_user_create.json
# 成功获取JSON数据:
# 数据已保存到: ../../api/server-docs_contact-v3_user_create.json
# JSON文件验证成功: ../../api/server-docs_contact-v3_user_create.json
# 输入文件指纹: abc12345 (基于 1 个文件)
# openapi文件输出路径: ../../openApi/openapi_server-docs_contact-v3_user_create_abc12345.yaml
# 接口关联关系文件输出路径: ../../openApi/api_relation_server-docs_contact-v3_user_create_abc12345.json
# 业务场景文件输出路径: ../../openApi/business_scene_server-docs_contact-v3_user_create_abc12345.json
# 测试用例已生成: ../../test_cases/test_cases_openapi_server-docs_contact-v3_user_create_abc12345.yaml
# 测试用例生成完成:
#   - 基础API测试用例: 5
#   - 场景测试用例: 3
#   - 关联测试用例: 2
#   - 总计: 10
```

### 示例2: 通过Web API处理输入

```bash
# 启动前端服务
python main_integration.py frontend

# 使用curl发送请求
curl -X POST http://127.0.0.1:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "feishu_url": "https://open.feishu.cn/document/server-docs/contact-v3/user/create"
  }'

# 响应:
# {
#   "status": "success",
#   "input_result": {
#     "openapi": "../../openApi/openapi_server-docs_contact-v3_user_create_abc12345.yaml",
#     "api_relation": "../../openApi/api_relation_server-docs_contact-v3_user_create_abc12345.json",
#     "business_scene": "../../openApi/business_scene_server-docs_contact-v3_user_create_abc12345.json"
#   },
#   "test_cases_path": "../../test_cases/test_cases_openapi_server-docs_contact-v3_user_create_abc12345.yaml"
# }
```

## 注意事项

1. 确保已正确配置环境变量，特别是AI相关的API密钥
2. 飞书URL必须是有效的公开文档链接
3. 上传的JSON文件必须符合API文档格式要求
4. 直接输入的OpenAPI文档必须是有效的YAML或JSON格式
5. 业务场景和接口关联关系必须是有效的JSON格式

## 故障排除

### 常见问题

1. **ModuleNotFoundError**: 确保已安装所有依赖项
2. **API密钥错误**: 检查`.env`文件中的API密钥配置
3. **飞书URL访问失败**: 确保URL有效且可公开访问
4. **JSON格式错误**: 检查输入的JSON文件格式是否正确

### 调试模式

启动前端服务时添加`-d`参数启用调试模式：

```bash
python main_integration.py frontend -d
```

## 贡献

欢迎提交问题报告和功能请求！