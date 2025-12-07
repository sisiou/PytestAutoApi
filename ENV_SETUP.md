# 环境变量设置说明

## 硅基流动API密钥配置

本项目使用硅基流动API作为AI服务提供商，需要配置API密钥才能正常使用AI功能。

### 方法1：在终端中设置（临时）

```bash
export SILICONFLOW_API_KEY="your_actual_api_key_here"
```

### 方法2：在.env文件中设置（推荐）

1. 在项目根目录创建`.env`文件：
```bash
touch .env
```

2. 编辑`.env`文件，添加以下内容：
```
SILICONFLOW_API_KEY=your_actual_api_key_here
```

3. 安装python-dotenv（如果尚未安装）：
```bash
pip install python-dotenv
```

### 方法3：在shell配置文件中设置（永久）

对于bash用户：
```bash
echo 'export SILICONFLOW_API_KEY="your_actual_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

对于zsh用户（macOS默认）：
```bash
echo 'export SILICONFLOW_API_KEY="your_actual_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### 获取API密钥

1. 访问[硅基流动官网](https://siliconflow.cn/)
2. 注册并登录账户
3. 在控制台中获取API密钥

### 配置文件模板

项目中的配置文件已经使用环境变量引用，无需修改：

- `configs/config.yaml` - 主配置文件
- `utils/smart_auto/openapi_agent_config.yaml` - OpenAPI Agent配置文件

### 验证配置

运行以下命令验证环境变量是否设置成功：

```bash
echo $SILICONFLOW_API_KEY
```

如果显示您的API密钥，则表示配置成功。

### 部署注意事项

1. 在生产环境中，建议使用环境变量或安全的密钥管理服务
2. 不要将API密钥硬编码在代码中或提交到版本控制系统
3. 确保`.env`文件已添加到`.gitignore`中

### 故障排除

如果遇到API调用失败的问题：

1. 检查API密钥是否正确设置
2. 确认API密钥是否有效且未过期
3. 检查网络连接是否正常
4. 查看日志文件获取详细错误信息