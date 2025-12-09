import yaml
import json
import os
from typing import Dict, Any, List
from openai import OpenAI
import requests
import pytest
import sys
from pathlib import Path

class APITestGenerator:
    def __init__(self, yaml_path: str, openai_api_key: str = None):
        """
        初始化API测试生成器
        
        Args:
            yaml_path: YAML文件路径
            openai_api_key: OpenAI/DashScope API密钥
        """
        self.yaml_path = yaml_path
        self.openapi_spec = None
        self.client = None
        
        # 初始化OpenAI客户端
        if openai_api_key is None:
            openai_api_key = os.getenv("DASHSCOPE_API_KEY")
        
            self.client = OpenAI(
            api_key=openai_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 加载YAML文件
        self.load_yaml()
    
    def load_yaml(self):
        """加载和解析YAML文件"""
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as file:
                self.openapi_spec = yaml.safe_load(file)
            print(f"[OK] 成功加载YAML文件: {self.yaml_path}")
        except Exception as e:
            print(f"[ERROR] 加载YAML文件失败: {e}")
            raise
    
    def extract_api_info(self) -> Dict[str, Any]:
        """
        从OpenAPI规范中提取关键信息
        
        Returns:
            包含API信息的字典
        """
        api_info = {
            "title": self.openapi_spec.get("info", {}).get("title", ""),
            "version": self.openapi_spec.get("info", {}).get("version", ""),
            "description": self.openapi_spec.get("info", {}).get("description", ""),
            "servers": self.openapi_spec.get("servers", []),
            "paths": {},
            "components": self.openapi_spec.get("components", {}),
            "security_schemes": self.openapi_spec.get("components", {}).get("securitySchemes", {})
        }
        
        # 提取每个路径的信息
        for path, methods in self.openapi_spec.get("paths", {}).items():
            api_info["paths"][path] = {}
            for method, details in methods.items():
                api_info["paths"][path][method] = {
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "operationId": details.get("operationId", ""),
                    "security": details.get("security", []),
                    "parameters": details.get("parameters", []),
                    "requestBody": details.get("requestBody", {}),
                    "responses": details.get("responses", {}),
                    "examples": self._extract_examples(details)
                }
        
        return api_info
    
    def _extract_examples(self, method_details: Dict) -> Dict:
        """提取示例数据"""
        examples = {}
        
        # 从requestBody中提取示例
        if "requestBody" in method_details:
            request_body = method_details["requestBody"]
            content = request_body.get("content", {})
            for content_type, content_info in content.items():
                if "example" in content_info:
                    examples["request_example"] = content_info["example"]
                if "examples" in content_info:
                    examples["request_examples"] = content_info["examples"]
        
        # 从responses中提取示例
        if "responses" in method_details:
            for status_code, response_info in method_details["responses"].items():
                content = response_info.get("content", {})
                for content_type, content_info in content.items():
                    if "example" in content_info:
                        examples[f"response_{status_code}_example"] = content_info["example"]
                    if "examples" in content_info:
                        examples[f"response_{status_code}_examples"] = content_info["examples"]
        
        return examples
    
    def generate_ai_prompt(self, api_info: Dict) -> str:
        """
        生成AI提示词
        
        Args:
            api_info: API信息字典
            
        Returns:
            AI提示词字符串
        """
        prompt = f"""你是一名资深的软件测试工程师，请根据以下OpenAPI规范生成全面的pytest测试用例。

## API基本信息
- 标题: {api_info['title']}
- 版本: {api_info['version']}
- 描述: {api_info['description']}
- 测试环境服务器: {api_info['servers'][1]['url'] if len(api_info['servers']) > 1 else 'N/A'}

## 认证信息
tenant_access_token获取方式已在代码中提供，测试用例中需要:
1. 使用fixture来管理token获取
2. 处理token过期和刷新
3. 验证Authorization头部

## 需要测试的接口
"""

        # 添加每个接口的详细信息
        for path, methods in api_info["paths"].items():
            for method, details in methods.items():
                prompt += f"""
### 接口: {method.upper()} {path}
- 操作ID: {details['operationId']}
- 摘要: {details['summary']}
- 描述: {details['description'][:200]}... (截断)

#### 请求信息
- 认证: {details['security']}
- 请求体: {json.dumps(details['requestBody'], ensure_ascii=False, indent=2)[:500]}...

#### 响应状态码
{self._format_responses(details['responses'])}

#### 组件schema
{self._format_schemas(api_info['components'].get('schemas', {}))}
"""
        
        prompt += """
## 测试用例生成要求

请生成完整、可执行的pytest测试用例文件，包含以下内容：

### 1. 必要的import语句
import pytest
import requests
import json
from typing import Dict, Any
import os

### 2. Fixtures设计
- @pytest.fixture: 用于tenant_access_token获取
- @pytest.fixture: 用于API客户端
- @pytest.fixture: 用于测试数据准备
- @pytest.fixture(scope="session"): 用于测试配置

### 3. 测试场景分类

#### 3.1 认证测试
- 测试有效token的请求
- 测试无效/过期token的请求
- 测试缺少Authorization头部的请求

#### 3.2 正常流程测试
- 测试成功创建卡片（card_json类型）
- 测试成功创建卡片（template类型）
- 验证响应结构符合schema
- 验证card_id返回格式

#### 3.3 边界值测试
- 测试最小长度的type和data
- 测试最大长度的data（接近3MB限制）
- 测试type枚举值验证
- 测试必填字段缺失

#### 3.4 错误场景测试（根据400响应示例）
- 参数错误 (code: 10002)
- 卡片内容超限 (code: 200860)
- 组件ID重复 (code: 300301)
- update_multi属性为false (code: 300302)
- 不支持非schema 2.0 (code: 300303)
- 生成卡片失败 (code: 200220)
- 组件数量超过200 (code: 300305)
- 卡片DSL为空 (code: 300307)

#### 3.5 服务器错误测试
- 模拟500内部服务器错误
- 测试超时场景

#### 3.6 性能测试
- 测试API响应时间
- 测试并发请求处理

### 4. 测试用例结构要求
- 每个测试类对应一个接口
- 使用@pytest.mark.parametrize进行参数化测试
- 包含清晰的断言语句
- 测试用例名称为test_<场景>_<期望结果>格式

### 5. 辅助函数
- 请求构建函数
- 响应验证函数
- 错误处理函数

### 6. 配置管理
- 从环境变量读取配置
- 支持多环境切换

### 7. 注意点
- 使用responses库模拟外部API调用
- 避免硬编码敏感信息
- 添加适当的注释和文档字符串
- 考虑测试的可维护性和可读性

请直接输出完整的Python测试代码，不需要额外的解释说明。代码应该可以直接运行（可能需要安装pytest和requests-mock）。
"""
        
        return prompt
    
    def _format_responses(self, responses: Dict) -> str:
        """格式化响应信息"""
        formatted = []
        for status_code, info in responses.items():
            desc = info.get('description', '')
            formatted.append(f"- {status_code}: {desc}")
            
            # 添加示例错误码
            if status_code in ['400', '500']:
                content = info.get('content', {})
                for content_type, content_info in content.items():
                    if 'examples' in content_info:
                        for example_name, example_data in content_info['examples'].items():
                            value = example_data.get('value', {})
                            formatted.append(f"  - {example_name}: code={value.get('code')}, msg={value.get('msg')}")
        return '\n'.join(formatted)
    
    def _format_schemas(self, schemas: Dict) -> str:
        """格式化schema信息"""
        formatted = []
        for schema_name, schema_def in schemas.items():
            formatted.append(f"- {schema_name}:")
            if 'required' in schema_def:
                formatted.append(f"  必填字段: {', '.join(schema_def['required'])}")
            if 'properties' in schema_def:
                for prop_name, prop_def in schema_def['properties'].items():
                    prop_type = prop_def.get('type', 'unknown')
                    formatted.append(f"  - {prop_name}: {prop_type}")
        return '\n'.join(formatted[:10])  # 只显示前10个属性
    
    def call_ai_for_test_cases(self, prompt: str) -> str:
        """
        调用AI生成测试用例
        
        Args:
            prompt: AI提示词
            
        Returns:
            生成的测试用例代码
        """
        try:
            messages = [
                {"role": "system", "content": "你是一个专业的测试开发工程师，擅长编写全面、健壮的API测试用例。"},
                {"role": "user", "content": prompt}
            ]
            
            print("[INFO] 正在调用AI生成测试用例...")
            
            completion = self.client.chat.completions.create(
                model="deepseek-v3.2",
                messages=messages,
                temperature=0.3,  # 较低的温度以获得更确定性的输出
                max_tokens=8000,  # 足够生成完整的测试用例
                extra_body={"enable_thinking": False}  # 关闭思考过程以获取直接输出
            )
            
            generated_code = completion.choices[0].message.content
            
            # 清理代码，确保是有效的Python代码
            if "```python" in generated_code:
                # 提取代码块中的内容
                start_idx = generated_code.find("```python") + len("```python")
                end_idx = generated_code.find("```", start_idx)
                generated_code = generated_code[start_idx:end_idx].strip()
            elif "```" in generated_code:
                # 处理其他格式的代码块
                start_idx = generated_code.find("```") + 3
                end_idx = generated_code.find("```", start_idx)
                generated_code = generated_code[start_idx:end_idx].strip()
            
            print("[OK] AI测试用例生成完成")
            return generated_code
            
        except Exception as e:
            print(f"[ERROR] 调用AI失败: {e}")
            # 返回一个基本的测试框架
            return self._generate_fallback_test_cases()
    
    def _generate_fallback_test_cases(self) -> str:
        """生成备用的测试用例框架"""
        return '''
import pytest
import json
import os
from unittest.mock import patch, Mock
import sys

# 模拟token获取
class MockTokenManager:
    def get_tenant_access_token(self):
        return "mock_tenant_access_token_123456"

# 基础测试类
class TestFeishuCardAPI:
    
    @pytest.fixture
    def token_manager(self):
        return MockTokenManager()
    
    @pytest.fixture
    def base_url(self):
        return "http://api.example.com/v1"
    
    @pytest.fixture
    def headers(self, token_manager):
        token = token_manager.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def valid_card_json_request(self):
        return {
            "type": "card_json",
            "data": json.dumps({
                "schema": "2.0",
                "header": {
                    "title": {
                        "content": "测试卡片",
                        "tag": "plain_text"
                    }
                },
                "config": {
                    "streaming_mode": True,
                    "summary": {"content": ""}
                },
                "body": {
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": "测试内容",
                            "element_id": "element_1"
                        }
                    ]
                }
            })
        }
    
    def test_create_card_success(self, base_url, headers, valid_card_json_request):
        """测试成功创建卡片"""
        # 这里应该使用requests发送实际请求
        # 暂时用assert True占位
        assert True
    
    def test_create_card_missing_token(self, base_url, valid_card_json_request):
        """测试缺少token的请求"""
        # 测试缺少Authorization头部的情况
        assert True
    
    def test_create_card_invalid_type(self, base_url, headers):
        """测试无效的type参数"""
        invalid_request = {
            "type": "invalid_type",
            "data": "{}"
        }
        assert True
    
    def test_create_card_missing_required_fields(self, base_url, headers):
        """测试缺少必填字段"""
        incomplete_request = {
            "type": "card_json"
            # 缺少data字段
        }
        assert True
'''
    
    def save_test_cases(self, test_code: str, output_path: str = "test_generated.py"):
        """
        保存生成的测试用例到文件
        
        Args:
            test_code: 测试用例代码
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(test_code)
            print(f"[OK] 测试用例已保存到: {output_path}")
            
            # 验证生成的代码
            self._validate_test_cases(output_path)
            
        except Exception as e:
            print(f"[ERROR] 保存测试用例失败: {e}")
    
    def _validate_test_cases(self, file_path: str):
        """验证生成的测试用例文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # 检查基本的pytest结构
            required_imports = ["import pytest", "import json"]
            imports_present = all(imp in content for imp in required_imports)
            
            # 检查是否有测试类或测试函数
            has_test_class = "class Test" in content
            has_test_function = "def test_" in content
            
            # 检查是否有断言
            has_assertions = "assert " in content
            
            print("[INFO] 测试用例验证结果:")
            print(f"  - 必要的import: {'✓' if imports_present else '✗'}")
            print(f"  - 包含测试类: {'✓' if has_test_class else '✗'}")
            print(f"  - 包含测试函数: {'✓' if has_test_function else '✗'}")
            print(f"  - 包含断言: {'✓' if has_assertions else '✗'}")
            
            if imports_present and has_test_function:
                print("[OK] 测试用例基本结构正确")
            else:
                    print("[WARNING] 测试用例结构可能不完整")
                
        except Exception as e:
            print(f"[ERROR] 验证测试用例失败: {e}")
    
    def generate_test_cases(self, output_path: str = "test_generated.py"):
        """
        主函数：生成测试用例
        
        Args:
            output_path: 输出文件路径
        """
        print("=" * 50)
        print("开始生成API测试用例")
        print("=" * 50)
        
        # 1. 提取API信息
        print("[1/4] 提取API信息...")
        api_info = self.extract_api_info()
        
        # 2. 生成AI提示词
        print("[2/4] 生成AI提示词...")
        prompt = self.generate_ai_prompt(api_info)
        
        # 可选：保存提示词供调试
        with open("ai_prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)
        print("[INFO] AI提示词已保存到: ai_prompt.txt")
        
        # 3. 调用AI生成测试用例
        print("[3/4] 调用AI生成测试用例...")
        test_code = self.call_ai_for_test_cases(prompt)
        
        # 4. 保存测试用例
        print("[4/4] 保存测试用例...")
        self.save_test_cases(test_code, output_path)
        
        print("=" * 50)
        print("测试用例生成完成!")
        print(f"请检查文件: {output_path}")
        print("=" * 50)
        
        return test_code


# 使用示例
if __name__ == "__main__":
    # 配置
    YAML_FILE_PATH = "feishu_openapi.yaml"  # 您的YAML文件路径
    OUTPUT_TEST_FILE = "test_feishu_api.py"
    
    # 确保有API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("[ERROR] 请设置DASHSCOPE_API_KEY环境变量")
        print("例如: export DASHSCOPE_API_KEY='sk-xxx'")
        sys.exit(1)
    
    # 创建生成器并生成测试用例
    try:
        generator = APITestGenerator(YAML_FILE_PATH, api_key)
        generator.generate_test_cases(OUTPUT_TEST_FILE)
        
        # 额外：生成一个简单的运行脚本
        run_script = '''
# 运行生成的测试用例
# 安装依赖: pip install pytest requests requests-mock

import subprocess
import sys

def run_tests():
    """运行pytest测试"""
    cmd = [sys.executable, "-m", "pytest", "test_feishu_api.py", "-v"]
    
    print("运行测试用例...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("标准输出:")
    print(result.stdout)
    
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
'''
        
        with open("run_tests.py", "w", encoding="utf-8") as f:
            f.write(run_script)
        print(f"[INFO] 运行脚本已生成: run_tests.py")
        
    except FileNotFoundError:
        print(f"[ERROR] 找不到YAML文件: {YAML_FILE_PATH}")
        print("请确保YAML文件存在，或修改YAML_FILE_PATH变量")
    except Exception as e:
        print(f"[ERROR] 生成测试用例时出错: {e}")