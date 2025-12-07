# 飞书URL测试用例生成器

这是一个整合工具，可以将飞书API文档URL转换为完整的测试用例，包括API文档、业务场景、接口关联关系和自动化测试用例。

## 功能特点

1. **URL解析**: 从飞书API文档URL获取JSON格式的API定义
2. **AI增强**: 使用阿里云百炼API生成API文档、业务场景和接口关联关系
3. **测试用例生成**: 自动生成飞书消息发送接口的测试用例
4. **前端交互**: 提供Web界面，方便用户操作
5. **批量处理**: 支持处理多个URL

## 使用方法

### 1. 单个URL处理

```bash
python run_url_to_testcase.py --url "https://open.feishu.cn/open-apis/docx/v1/documents"
```

### 2. 批量URL处理

```bash
python run_url_to_testcase.py --urls example_urls.txt
```

### 3. 启动Web服务

```bash
python run_url_to_testcase.py --server
```

然后在浏览器中访问 http://localhost:5000

## 工具架构

本工具整合了以下模块：

1. **feishu_parse.py**: 负责将飞书URL转换为JSON格式
2. **ai.py**: 使用阿里云百炼API生成API文档、业务场景和接口关联关系
3. **openapi_to_testcase.py**: 从OpenAPI数据生成测试用例的独立工具
4. **feishu_test_generator.py**: 提供前端交互功能

### 独立工具使用

除了整合工具外，您也可以单独使用`openapi_to_testcase.py`工具：

```bash
# 从OpenAPI文件生成测试用例
python utils/other_tools/openapi_to_testcase.py --file path/to/openapi.yaml --output output_dir
```

## 输出文件

处理完成后，会在以下目录生成文件：

- `output/openapi/`: OpenAPI格式的API文档
- `output/relation/`: 接口关联关系文件
- `output/scene/`: 业务场景文件
- `interfacetest/`: 测试用例文件

## 前端交互

启动Web服务后，可以通过以下方式与工具交互：

1. 在URL输入框中输入飞书API文档URL
2. 点击"处理URL"按钮开始处理
3. 查看处理进度和结果
4. 下载生成的文件

## 示例

项目中包含了一个示例URL文件 `example_urls.txt`，您可以使用它来测试工具：

```bash
python run_url_to_testcase.py --urls example_urls.txt
```

## 依赖要求

- Python 3.7+
- Flask (用于Web服务)
- requests (用于HTTP请求)
- pyyaml (用于YAML处理)
- 其他依赖见 requirements.txt

## 注意事项

1. 使用AI功能需要配置阿里云百炼API密钥
2. 处理大量URL可能需要较长时间
3. 生成的测试用例可能需要根据实际需求进行调整

## 故障排除

如果遇到问题，请检查：

1. 网络连接是否正常
2. API密钥是否正确配置
3. 依赖是否正确安装
4. URL是否有效

## 贡献

欢迎提交Issue和Pull Request来改进这个工具。