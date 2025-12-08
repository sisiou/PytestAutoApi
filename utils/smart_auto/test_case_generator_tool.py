"""
测试用例生成功能模块
基于LangChain工具实现，用于根据API文档自动生成测试用例
"""

import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import random
import string
from .test_generator import TestCase, TestSuite
from .openapi_parser_tool import OpenAPIParseTool


@dataclass
class GeneratedTestCase:
    """生成的测试用例"""
    name: str
    description: str
    method: str
    url: str
    headers: Dict[str, str]
    params: Dict[str, Any]
    body: Optional[Dict[str, Any]]
    expected_status: int
    expected_response: Optional[Dict[str, Any]]
    assertions: List[Dict[str, Any]]


@dataclass
class GeneratedTestSuite:
    """生成的测试套件"""
    name: str
    description: str
    test_cases: List[GeneratedTestCase]
    setup: Optional[Dict[str, Any]]
    teardown: Optional[Dict[str, Any]]


class TestCaseGeneratorInput(BaseModel):
    """测试用例生成工具输入模型"""
    openapi_source: str = Field(description="OpenAPI 3.0.0文档来源，可以是URL、文件路径或JSON/YAML字符串")
    source_type: str = Field(description="来源类型：url、file或content")
    test_type: str = Field(description="测试类型：basic(基础测试)、boundary(边界测试)、error(错误测试)或all(全部)")
    num_cases: Optional[int] = Field(description="每个API生成的测试用例数量，默认为3")


class TestCaseGeneratorTool(BaseTool):
    """测试用例生成工具"""
    name = "test_case_generator_tool"
    description = "根据OpenAPI 3.0.0文档自动生成API测试用例"
    args_schema: type[BaseModel] = TestCaseGeneratorInput
    
    def _run(self, openapi_source: str, source_type: str, test_type: str = "all", num_cases: int = 3) -> Dict[str, Any]:
        """执行测试用例生成"""
        try:
            # 首先解析OpenAPI文档
            parse_tool = OpenAPIParseTool()
            parse_result = parse_tool._run(openapi_source, source_type)
            
            if "error" in parse_result:
                return parse_result
            
            endpoints = parse_result.get("endpoints", [])
            schemas = parse_result.get("schemas", {})
            base_url = parse_result.get("base_url", "")
            
            # 添加调试信息
            print(f"DEBUG: Found {len(endpoints)} endpoints")
            if len(endpoints) > 0:
                print(f"DEBUG: First endpoint: {endpoints[0]}")
            
            # 生成测试用例
            test_suites = []
            
            for i, endpoint in enumerate(endpoints):
                print(f"DEBUG: Processing endpoint {i+1}/{len(endpoints)}: {endpoint.get('method')} {endpoint.get('path')}")
                
                method = endpoint["method"]
                path = endpoint["path"]
                endpoint_name = f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
                
                # 生成不同类型的测试用例
                test_cases = []
                
                if test_type in ["basic", "all"]:
                    basic_cases = self._generate_basic_test_cases(endpoint, schemas, base_url, num_cases)
                    print(f"DEBUG: Generated {len(basic_cases)} basic test cases for {method} {path}")
                    test_cases.extend(basic_cases)
                
                if test_type in ["boundary", "all"]:
                    boundary_cases = self._generate_boundary_test_cases(endpoint, schemas, base_url, num_cases)
                    print(f"DEBUG: Generated {len(boundary_cases)} boundary test cases for {method} {path}")
                    test_cases.extend(boundary_cases)
                
                if test_type in ["error", "all"]:
                    error_cases = self._generate_error_test_cases(endpoint, schemas, base_url, num_cases)
                    print(f"DEBUG: Generated {len(error_cases)} error test cases for {method} {path}")
                    test_cases.extend(error_cases)
                
                print(f"DEBUG: Total test cases for {method} {path}: {len(test_cases)}")
                
                # 创建测试套件
                test_suite = GeneratedTestSuite(
                    name=f"{endpoint_name}_test_suite",
                    description=f"测试{method} {path}接口",
                    test_cases=test_cases,
                    setup=self._generate_setup(endpoint),
                    teardown=self._generate_teardown(endpoint)
                )
                
                test_suites.append(test_suite)
            
            print(f"DEBUG: Total test suites: {len(test_suites)}")
            print(f"DEBUG: Total test cases: {sum(len(suite.test_cases) for suite in test_suites)}")
            
            # 生成测试套件汇总
            summary = self._generate_test_summary(test_suites)
            
            return {
                "test_suites": [
                    {
                        "name": suite.name,
                        "description": suite.description,
                        "test_cases": [
                            {
                                "name": case.name,
                                "description": case.description,
                                "method": case.method,
                                "url": case.url,
                                "headers": case.headers,
                                "params": case.params,
                                "body": case.body,
                                "expected_status": case.expected_status,
                                "expected_response": case.expected_response,
                                "assertions": case.assertions
                            } for case in suite.test_cases
                        ],
                        "setup": suite.setup,
                        "teardown": suite.teardown
                    } for suite in test_suites
                ],
                "summary": summary
            }
            
        except Exception as e:
            return {"error": f"生成测试用例失败: {str(e)}"}
    
    def _generate_basic_test_cases(self, endpoint: Dict, schemas: Dict, base_url: str, num_cases: int) -> List[GeneratedTestCase]:
        """生成基础测试用例"""
        test_cases = []
        method = endpoint["method"]
        path = endpoint["path"]
        
        # 生成正常情况测试用例
        for i in range(min(num_cases, 2)):
            case_name = f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_basic_{i+1}"
            
            # 生成参数
            params = self._generate_params(endpoint, schemas, "basic")
            
            # 生成请求体
            body = self._generate_request_body(endpoint, schemas, "basic")
            
            # 生成预期响应
            expected_status = self._get_expected_success_status(method)
            expected_response = self._generate_expected_response(endpoint, schemas, expected_status)
            
            # 生成断言
            assertions = self._generate_assertions(endpoint, expected_status, expected_response)
            
            # 构建URL，避免重复路径
            if base_url and path.startswith(base_url):
                # 如果path已经包含base_url，直接使用path
                url = path
            else:
                # 否则组合base_url和path
                url = f"{base_url}{path}"
            
            test_case = GeneratedTestCase(
                name=case_name,
                description=f"测试{method} {path}接口 - 基础测试用例{i+1}",
                method=method,
                url=url,
                headers=self._generate_headers(endpoint),
                params=params,
                body=body,
                expected_status=expected_status,
                expected_response=expected_response,
                assertions=assertions
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def _generate_boundary_test_cases(self, endpoint: Dict, schemas: Dict, base_url: str, num_cases: int) -> List[GeneratedTestCase]:
        """生成边界测试用例"""
        test_cases = []
        method = endpoint["method"]
        path = endpoint["path"]
        
        # 生成边界值测试用例
        boundary_cases = [
            {"name": "empty_params", "description": "空参数测试"},
            {"name": "max_length", "description": "最大长度测试"},
            {"name": "min_length", "description": "最小长度测试"}
        ]
        
        for i, case_type in enumerate(boundary_cases[:min(num_cases, len(boundary_cases))]):
            case_name = f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_boundary_{case_type['name']}"
            
            # 生成参数
            params = self._generate_params(endpoint, schemas, "boundary", case_type["name"])
            
            # 生成请求体
            body = self._generate_request_body(endpoint, schemas, "boundary", case_type["name"])
            
            # 生成预期响应
            expected_status = self._get_expected_success_status(method)
            expected_response = self._generate_expected_response(endpoint, schemas, expected_status)
            
            # 生成断言
            assertions = self._generate_assertions(endpoint, expected_status, expected_response)
            
            # 构建URL，避免重复路径
            if base_url and path.startswith(base_url):
                # 如果path已经包含base_url，直接使用path
                url = path
            else:
                # 否则组合base_url和path
                url = f"{base_url}{path}"
            
            test_case = GeneratedTestCase(
                name=case_name,
                description=f"测试{method} {path}接口 - {case_type['description']}",
                method=method,
                url=url,
                headers=self._generate_headers(endpoint),
                params=params,
                body=body,
                expected_status=expected_status,
                expected_response=expected_response,
                assertions=assertions
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def _generate_error_test_cases(self, endpoint: Dict, schemas: Dict, base_url: str, num_cases: int) -> List[GeneratedTestCase]:
        """生成错误测试用例"""
        test_cases = []
        method = endpoint["method"]
        path = endpoint["path"]
        
        # 生成错误情况测试用例
        error_cases = [
            {"name": "invalid_method", "description": "无效HTTP方法测试", "status": 405},
            {"name": "missing_required", "description": "缺少必需参数测试", "status": 400},
            {"name": "invalid_format", "description": "无效格式测试", "status": 400},
            {"name": "unauthorized", "description": "未授权测试", "status": 401}
        ]
        
        for i, case_type in enumerate(error_cases[:min(num_cases, len(error_cases))]):
            case_name = f"test_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}_error_{case_type['name']}"
            
            # 生成参数
            params = self._generate_params(endpoint, schemas, "error", case_type["name"])
            
            # 生成请求体
            body = self._generate_request_body(endpoint, schemas, "error", case_type["name"])
            
            # 生成预期响应
            expected_status = case_type["status"]
            expected_response = self._generate_expected_response(endpoint, schemas, expected_status)
            
            # 生成断言
            assertions = self._generate_assertions(endpoint, expected_status, expected_response)
            
            # 构建URL，避免重复路径
            if base_url and path.startswith(base_url):
                # 如果path已经包含base_url，直接使用path
                url = path
            else:
                # 否则组合base_url和path
                url = f"{base_url}{path}"
            
            test_case = GeneratedTestCase(
                name=case_name,
                description=f"测试{method} {path}接口 - {case_type['description']}",
                method=method,
                url=url,
                headers=self._generate_headers(endpoint),
                params=params,
                body=body,
                expected_status=expected_status,
                expected_response=expected_response,
                assertions=assertions
            )
            
            test_cases.append(test_case)
        
        return test_cases
    
    def _generate_params(self, endpoint: Dict, schemas: Dict, test_type: str, case_type: str = "") -> Dict[str, Any]:
        """生成请求参数"""
        params = {}
        
        for param in endpoint.get("parameters", []):
            param_name = param["name"]
            param_in = param.get("in", param.get("param_in", ""))  # 兼容两种格式
            param_type = param.get("type", "string")
            required = param.get("required", False)
            
            # 只生成查询参数和路径参数
            if param_in in ["query", "path"]:
                # 根据测试类型生成不同的参数值
                if test_type == "basic":
                    value = self._generate_basic_value(param_type, param)
                elif test_type == "boundary":
                    value = self._generate_boundary_value(param_type, param, case_type)
                elif test_type == "error":
                    value = self._generate_error_value(param_type, param, case_type)
                else:
                    value = self._generate_basic_value(param_type, param)
                
                # 对于路径参数，总是提供值
                if param_in == "path" or required:
                    params[param_name] = value
                # 对于可选查询参数，在错误测试中可能不提供
                elif test_type == "error" and case_type == "missing_required" and not required:
                    continue  # 跳过可选参数
                else:
                    params[param_name] = value
        
        return params
    
    def _generate_request_body(self, endpoint: Dict, schemas: Dict, test_type: str, case_type: str = "") -> Optional[Dict[str, Any]]:
        """生成请求体"""
        request_body = endpoint.get("request_body")
        
        # 添加调试信息
        print(f"DEBUG: Request body for {endpoint.get('method')} {endpoint.get('path')}: {request_body}")
        
        if not request_body:
            return None
        
        # 处理我们的数据结构
        if "content_types" in request_body:
            if "application/json" not in request_body.get("content_types", []):
                return None
            
            schema = request_body.get("schema", {})
        else:
            # 处理标准OpenAPI 3.0格式
            content = request_body.get("content", {})
            json_content = content.get("application/json")
            if not json_content:
                return None
            
            schema = json_content.get("schema", {})
        
        # 根据测试类型生成不同的请求体
        if test_type == "basic":
            return self._generate_basic_object(schema, schemas)
        elif test_type == "boundary":
            return self._generate_boundary_object(schema, schemas, case_type)
        elif test_type == "error":
            return self._generate_error_object(schema, schemas, case_type)
        else:
            return self._generate_basic_object(schema, schemas)
    
    def _generate_basic_value(self, param_type: str, param: Dict) -> Any:
        """生成基础值"""
        if param_type == "string":
            if "enum" in param:
                return random.choice(param["enum"])
            elif param.get("format") == "email":
                return f"test{random.randint(1, 1000)}@example.com"
            elif param.get("format") == "date":
                return "2023-01-01"
            elif param.get("format") == "date-time":
                return "2023-01-01T00:00:00Z"
            else:
                return f"test_{random.randint(1, 1000)}"
        elif param_type == "integer":
            minimum = param.get("minimum", 1)
            maximum = param.get("maximum", 100)
            return random.randint(minimum, maximum)
        elif param_type == "number":
            minimum = param.get("minimum", 1.0)
            maximum = param.get("maximum", 100.0)
            return round(random.uniform(minimum, maximum), 2)
        elif param_type == "boolean":
            return random.choice([True, False])
        else:
            return f"test_{random.randint(1, 1000)}"
    
    def _generate_boundary_value(self, param_type: str, param: Dict, case_type: str) -> Any:
        """生成边界值"""
        if case_type == "empty_params":
            return "" if param_type == "string" else 0
        elif case_type == "max_length":
            if param_type == "string":
                max_length = param.get("maxLength", 50)
                return "".join(random.choices(string.ascii_letters + string.digits, k=max_length))
            elif param_type in ["integer", "number"]:
                return param.get("maximum", 100)
            else:
                return self._generate_basic_value(param_type, param)
        elif case_type == "min_length":
            if param_type == "string":
                min_length = param.get("minLength", 1)
                return "".join(random.choices(string.ascii_letters + string.digits, k=min_length))
            elif param_type in ["integer", "number"]:
                return param.get("minimum", 1)
            else:
                return self._generate_basic_value(param_type, param)
        else:
            return self._generate_basic_value(param_type, param)
    
    def _generate_error_value(self, param_type: str, param: Dict, case_type: str) -> Any:
        """生成错误值"""
        if case_type == "missing_required":
            return None  # 将在调用处处理
        elif case_type == "invalid_format":
            if param_type == "string":
                if param.get("format") == "email":
                    return "invalid-email"
                elif param.get("format") == "date":
                    return "invalid-date"
                else:
                    return 123  # 类型错误
            elif param_type in ["integer", "number"]:
                return "not-a-number"
            elif param_type == "boolean":
                return "not-a-boolean"
            else:
                return None
        else:
            return self._generate_basic_value(param_type, param)
    
    def _generate_basic_object(self, schema: Dict, schemas: Dict) -> Dict[str, Any]:
        """生成基础对象"""
        obj = {}
        
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            if ref_name in schemas:
                schema = schemas[ref_name]
        
        if "properties" in schema:
            properties = schema["properties"]
            required_fields = schema.get("required", [])
            
            for prop_name, prop_schema in properties.items():
                # 只生成必需字段和一些可选字段
                if prop_name in required_fields or random.random() > 0.5:
                    prop_type = prop_schema.get("type", "string")
                    obj[prop_name] = self._generate_basic_value(prop_type, prop_schema)
        
        return obj
    
    def _generate_boundary_object(self, schema: Dict, schemas: Dict, case_type: str) -> Dict[str, Any]:
        """生成边界对象"""
        obj = self._generate_basic_object(schema, schemas)
        
        if case_type == "empty_params":
            return {}
        elif case_type == "max_length":
            # 对字符串字段设置最大长度
            for key, value in obj.items():
                if isinstance(value, str):
                    obj[key] = value * 10  # 简单地放大字符串长度
            return obj
        elif case_type == "min_length":
            # 对字符串字段设置最小长度
            for key, value in obj.items():
                if isinstance(value, str) and len(value) > 1:
                    obj[key] = value[0]  # 只保留一个字符
            return obj
        else:
            return obj
    
    def _generate_error_object(self, schema: Dict, schemas: Dict, case_type: str) -> Dict[str, Any]:
        """生成错误对象"""
        if case_type == "missing_required":
            # 返回空对象，缺少必需字段
            return {}
        elif case_type == "invalid_format":
            # 生成类型错误的对象
            obj = self._generate_basic_object(schema, schemas)
            for key, value in obj.items():
                if isinstance(value, str):
                    obj[key] = 123  # 将字符串改为数字
                elif isinstance(value, (int, float)):
                    obj[key] = "not-a-number"  # 将数字改为字符串
                elif isinstance(value, bool):
                    obj[key] = "not-a-boolean"  # 将布尔值改为字符串
            return obj
        else:
            return self._generate_basic_object(schema, schemas)
    
    def _generate_headers(self, endpoint: Dict) -> Dict[str, str]:
        """生成请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 如果API需要认证，添加认证头
        if endpoint.get("security"):
            # 这里简化处理，实际应根据安全方案生成相应的认证头
            headers["Authorization"] = "Bearer test-token"
        
        return headers
    
    def _get_expected_success_status(self, method: str) -> int:
        """获取预期成功状态码"""
        if method == "POST":
            return 201
        elif method == "DELETE":
            return 204
        else:
            return 200
    
    def _generate_expected_response(self, endpoint: Dict, schemas: Dict, status_code: int) -> Optional[Dict[str, Any]]:
        """生成预期响应"""
        responses = endpoint.get("responses", {})
        response = responses.get(str(status_code))
        
        if not response:
            # 如果没有找到对应状态码的响应，使用默认响应
            if str(status_code).startswith("2"):
                response = responses.get("200") or responses.get("default")
            else:
                response = responses.get("default")
        
        if not response:
            return None
        
        content = response.get("content", {})
        json_content = content.get("application/json")
        
        if not json_content:
            return None
        
        schema = json_content.get("schema", {})
        
        # 根据模式生成示例响应
        return self._generate_basic_object(schema, schemas)
    
    def _generate_assertions(self, endpoint: Dict, expected_status: int, expected_response: Optional[Dict]) -> List[Dict[str, Any]]:
        """生成断言"""
        assertions = [
            {
                "type": "status",
                "expected": expected_status,
                "description": f"验证状态码为{expected_status}"
            }
        ]
        
        if expected_response:
            assertions.append({
                "type": "response_time",
                "expected": "< 5000",
                "description": "验证响应时间小于5秒"
            })
            
            # 如果有响应体，添加JSON结构验证
            if isinstance(expected_response, dict) and expected_response:
                assertions.append({
                    "type": "json_structure",
                    "expected": list(expected_response.keys()),
                    "description": "验证响应JSON结构"
                })
        
        return assertions
    
    def _generate_setup(self, endpoint: Dict) -> Optional[Dict[str, Any]]:
        """生成测试前置条件"""
        # 根据需要生成前置条件，例如创建测试数据
        return None
    
    def _generate_teardown(self, endpoint: Dict) -> Optional[Dict[str, Any]]:
        """生成测试后置条件"""
        # 根据需要生成后置条件，例如清理测试数据
        return None
    
    def _generate_test_summary(self, test_suites: List[GeneratedTestSuite]) -> Dict[str, Any]:
        """生成测试汇总"""
        total_suites = len(test_suites)
        total_cases = sum(len(suite.test_cases) for suite in test_suites)
        
        # 按测试类型统计
        basic_cases = 0
        boundary_cases = 0
        error_cases = 0
        
        for suite in test_suites:
            for case in suite.test_cases:
                if "basic" in case.name:
                    basic_cases += 1
                elif "boundary" in case.name:
                    boundary_cases += 1
                elif "error" in case.name:
                    error_cases += 1
        
        return {
            "total_suites": total_suites,
            "total_cases": total_cases,
            "basic_cases": basic_cases,
            "boundary_cases": boundary_cases,
            "error_cases": error_cases
        }


def create_test_generator_tools():
    """创建测试用例生成相关的工具集"""
    return [
        TestCaseGeneratorTool()
    ]