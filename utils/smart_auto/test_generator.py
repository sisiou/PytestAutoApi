#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2025/12/04 10:00
# @Author : Smart Auto Platform
# @File   : test_generator.py
# @describe: 测试用例自动生成模块，根据API文档和依赖关系生成测试用例
"""

import os
import json
import yaml
import random
import string
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from utils.smart_auto.api_parser import parse_api_document, APIEndpoint
from utils.smart_auto.dependency_analyzer import analyze_api_dependencies, BusinessFlow, DataDependency
from utils.read_files_tools.yaml_control import GetYamlData
from utils.read_files_tools.testcase_template import write_testcase_file
from utils.logging_tool.log_control import INFO, ERROR, WARNING
from utils.other_tools.exceptions import TestGenerationError
from common.setting import ensure_path_sep


@dataclass
class TestCase:
    """测试用例数据类"""
    case_id: str
    case_name: str
    api_method: str
    api_path: str
    host: str
    headers: Dict
    request_type: str
    data: Dict
    is_run: bool
    detail: str
    dependence_case: bool
    dependence_case_data: Optional[Dict]
    current_request_set_cache: Optional[Dict]
    sql: Optional[str]
    assert_data: Dict
    setup_sql: Optional[str]
    teardown: Optional[Dict]
    teardown_sql: Optional[str]
    sleep: Optional[float]


@dataclass
class TestSuite:
    """测试套件数据类"""
    suite_id: str
    suite_name: str
    description: str
    test_cases: List[TestCase]
    allure_epic: str
    allure_feature: str
    allure_story: str


class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_string_data(length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_email_data() -> str:
        """生成随机邮箱"""
        username = TestDataGenerator.generate_string_data(8)
        domain = random.choice(['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com'])
        return f"{username}@{domain}"
    
    @staticmethod
    def generate_phone_data() -> str:
        """生成随机手机号"""
        return f"1{random.choice(['3', '4', '5', '6', '7', '8', '9'])}{random.choices(string.digits, k=9)}"
    
    @staticmethod
    def generate_integer_data(min_val: int = 1, max_val: int = 100) -> int:
        """生成随机整数"""
        return random.randint(min_val, max_val)
    
    @staticmethod
    def generate_float_data(min_val: float = 0.0, max_val: float = 100.0) -> float:
        """生成随机浮点数"""
        return round(random.uniform(min_val, max_val), 2)
    
    @staticmethod
    def generate_boolean_data() -> bool:
        """生成随机布尔值"""
        return random.choice([True, False])
    
    @staticmethod
    def generate_date_data() -> str:
        """生成随机日期"""
        year = random.randint(2000, 2023)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # 简化处理，不处理月份天数差异
        return f"{year}-{month:02d}-{day:02d}"
    
    @staticmethod
    def generate_data_by_type(data_type: str, field_name: str = "") -> Any:
        """根据数据类型生成测试数据"""
        type_lower = data_type.lower()
        
        if 'string' in type_lower:
            if 'email' in field_name.lower():
                return TestDataGenerator.generate_email_data()
            elif 'phone' in field_name.lower() or 'mobile' in field_name.lower():
                return TestDataGenerator.generate_phone_data()
            elif 'date' in field_name.lower():
                return TestDataGenerator.generate_date_data()
            else:
                return TestDataGenerator.generate_string_data()
        elif 'integer' in type_lower or 'int' in type_lower:
            return TestDataGenerator.generate_integer_data()
        elif 'number' in type_lower or 'float' in type_lower or 'double' in type_lower:
            return TestDataGenerator.generate_float_data()
        elif 'boolean' in type_lower or 'bool' in type_lower:
            return TestDataGenerator.generate_boolean_data()
        else:
            return TestDataGenerator.generate_string_data()


class TestCaseGenerator:
    """测试用例生成器"""
    
    def __init__(self, api_doc_path: str, output_dir: str = None):
        """
        初始化测试用例生成器
        :param api_doc_path: API文档路径
        :param output_dir: 输出目录
        """
        self.api_doc_path = api_doc_path
        self.output_dir = output_dir or ensure_path_sep("\\data")
        self.apis = []
        self.analyzer = None
        self.test_suites = []
        
    def generate_test_cases(self) -> List[TestSuite]:
        """生成测试用例"""
        try:
            INFO.logger.info("开始生成测试用例...")
            
            # 1. 解析API文档
            self.apis = parse_api_document(self.api_doc_path)
            INFO.logger.info(f"解析到 {len(self.apis)} 个API")
            
            # 2. 分析API依赖关系
            # 将APIEndpoint对象转换为字典格式，以符合dependency_analyzer的期望
            apis_dict = []
            for api in self.apis:
                api_dict = {
                    'path': api.path,
                    'method': api.method,
                    'operationId': api.operation_id,
                    'parameters': api.parameters,
                    'request_body': api.request_body,
                    'success_response': api.success_response,
                    'tags': api.tags,
                    'summary': api.summary
                }
                apis_dict.append(api_dict)
            
            self.analyzer = analyze_api_dependencies(apis_dict)
            
            # 3. 生成基础测试用例
            self._generate_basic_test_cases()
            
            # 4. 生成场景测试用例
            self._generate_scenario_test_cases()
            
            # 5. 生成边界值测试用例
            self._generate_boundary_test_cases()
            
            # 6. 生成异常测试用例
            self._generate_exception_test_cases()
            
            INFO.logger.info(f"测试用例生成完成，共生成 {len(self.test_suites)} 个测试套件")
            return self.test_suites
            
        except Exception as e:
            ERROR.logger.error(f"生成测试用例失败: {str(e)}")
            raise TestGenerationError(f"生成测试用例失败: {str(e)}")
            
    def _generate_basic_test_cases(self) -> None:
        """生成基础测试用例"""
        INFO.logger.info("生成基础测试用例...")
        
        for api in self.apis:
            api_id = f"{api.method}_{api.path}"
            case_id = f"basic_{api_id.replace('/', '_').replace('{', '_').replace('}', '_')}"
            
            # 生成测试数据
            test_data = self._generate_test_data_for_api(api)
            
            # 生成断言数据
            assert_data = self._generate_assert_data_for_api(api)
            
            # 创建测试用例
            test_case = TestCase(
                case_id=case_id,
                case_name=f"测试{api.summary}",
                api_method=api.method,
                api_path=api.path,
                host="${host()}",
                headers=self._generate_headers_for_api(api),
                request_type=self._get_request_type(api),
                data=test_data,
                is_run=True,
                detail=f"测试{api.summary}的基本功能",
                dependence_case=False,
                dependence_case_data=None,
                current_request_set_cache=None,
                sql=None,
                assert_data=assert_data,
                setup_sql=None,
                teardown=None,
                teardown_sql=None,
                sleep=None
            )
            
            # 创建测试套件
            test_suite = TestSuite(
                suite_id=f"suite_{case_id}",
                suite_name=f"{api.summary}测试",
                description=f"测试{api.summary}的基本功能",
                test_cases=[test_case],
                allure_epic=getattr(api, 'host', 'API测试'),
                allure_feature=getattr(api, 'tags', ['API'])[0] if getattr(api, 'tags', None) else 'API功能测试',
                allure_story=api.summary
            )
            
            self.test_suites.append(test_suite)
            
    def _generate_scenario_test_cases(self) -> None:
        """生成场景测试用例"""
        INFO.logger.info("生成场景测试用例...")
        
        # 获取业务流程
        business_flows = self.analyzer.get_business_flows()
        
        for flow in business_flows:
            if len(flow.apis) < 2:  # 跳过只有一个API的流程
                continue
                
            # 为每个业务流程创建测试套件
            test_cases = []
            
            for i, api_id in enumerate(flow.apis):
                # 查找对应的API信息
                api = None
                for a in self.apis:
                    if f"{a.method}_{a.path}" == api_id:
                        api = a
                        break
                        
                if not api:
                    WARNING.logger.warning(f"未找到API信息: {api_id}")
                    continue
                    
                case_id = f"scenario_{flow.flow_id}_{api_id.replace('/', '_').replace('{', '_').replace('}', '_')}"
                
                # 生成测试数据
                test_data = self._generate_test_data_for_api(api)
                
                # 如果不是第一个API，则需要依赖前面的API
                if i > 0:
                    # 查找依赖关系
                    dependencies = self._find_dependencies_for_api(api_id, flow.apis[:i])
                    
                    # 生成依赖数据
                    dependence_case_data = self._generate_dependence_data(dependencies)
                    
                    # 设置当前请求缓存
                    current_request_set_cache = self._generate_cache_data(api)
                else:
                    dependencies = []
                    dependence_case_data = None
                    current_request_set_cache = None
                    
                # 生成断言数据
                assert_data = self._generate_assert_data_for_api(api)
                
                # 创建测试用例
                test_case = TestCase(
                    case_id=case_id,
                    case_name=f"测试{api.summary}",
                    api_method=api.method,
                    api_path=api.path,
                    host="${host()}",
                    headers=self._generate_headers_for_api(api),
                    request_type=self._get_request_type(api),
                    data=test_data,
                    is_run=True,
                    detail=f"测试{api.summary}，业务流程: {flow.flow_name}",
                    dependence_case=len(dependencies) > 0,
                    dependence_case_data=dependence_case_data,
                    current_request_set_cache=current_request_set_cache,
                    sql=None,
                    assert_data=assert_data,
                    setup_sql=None,
                    teardown=None,
                    teardown_sql=None,
                    sleep=None
                )
                
                test_cases.append(test_case)
                
            # 创建测试套件
            test_suite = TestSuite(
                suite_id=f"suite_scenario_{flow.flow_id}",
                suite_name=flow.flow_name,
                description=flow.description,
                test_cases=test_cases,
                allure_epic="业务流程测试",
                allure_feature=flow.flow_name,
                allure_story=flow.description
            )
            
            self.test_suites.append(test_suite)
            
    def _generate_boundary_test_cases(self) -> None:
        """生成边界值测试用例"""
        INFO.logger.info("生成边界值测试用例...")
        
        # 为每个API生成边界值测试用例
        for api in self.apis:
            # 只为有参数的API生成边界值测试用例
            if not getattr(api, 'parameters', None) and not getattr(api, 'request_body', None):
                continue
                
            api_id = f"{api.method}_{api.path}"
            
            # 生成边界值测试数据
            boundary_test_cases = self._generate_boundary_test_data_for_api(api)
            
            if not boundary_test_cases:
                continue
                
            # 创建测试套件
            test_cases = []
            
            for i, test_data in enumerate(boundary_test_cases):
                case_id = f"boundary_{api_id.replace('/', '_').replace('{', '_').replace('}', '_')}_{i+1}"
                
                # 生成断言数据
                assert_data = self._generate_assert_data_for_api(api)
                
                # 创建测试用例
                test_case = TestCase(
                    case_id=case_id,
                    case_name=f"边界值测试{api.summary}_{i+1}",
                    api_method=api.method,
                    api_path=api.path,
                    host="${host()}",
                    headers=self._generate_headers_for_api(api),
                    request_type=self._get_request_type(api),
                    data=test_data,
                    is_run=True,
                    detail=f"测试{api.summary}的边界值",
                    dependence_case=False,
                    dependence_case_data=None,
                    current_request_set_cache=None,
                    sql=None,
                    assert_data=assert_data,
                    setup_sql=None,
                    teardown=None,
                    teardown_sql=None,
                    sleep=None
                )
                
                test_cases.append(test_case)
                
            # 创建测试套件
            test_suite = TestSuite(
                suite_id=f"suite_boundary_{api_id.replace('/', '_').replace('{', '_').replace('}', '_')}",
                suite_name=f"{api.summary}边界值测试",
                description=f"测试{api.summary}的边界值",
                test_cases=test_cases,
                allure_epic="边界值测试",
                allure_feature=getattr(api, 'tags', ['API'])[0] if getattr(api, 'tags', None) else 'API功能测试',
                allure_story=f"{api.summary}边界值测试"
            )
            
            self.test_suites.append(test_suite)
            
    def _generate_exception_test_cases(self) -> None:
        """生成异常测试用例"""
        INFO.logger.info("生成异常测试用例...")
        
        # 为每个API生成异常测试用例
        for api in self.apis:
            api_id = f"{api.method}_{api.path}"
            
            # 生成异常测试数据
            exception_test_cases = self._generate_exception_test_data_for_api(api)
            
            if not exception_test_cases:
                continue
                
            # 创建测试套件
            test_cases = []
            
            for i, (test_data, expected_status) in enumerate(exception_test_cases):
                case_id = f"exception_{api_id.replace('/', '_').replace('{', '_').replace('}', '_')}_{i+1}"
                
                # 生成断言数据，期望返回错误状态码
                assert_data = {"status_code": expected_status}
                
                # 创建测试用例
                test_case = TestCase(
                    case_id=case_id,
                    case_name=f"异常测试{api.summary}_{i+1}",
                    api_method=api.method,
                    api_path=api.path,
                    host="${host()}",
                    headers=self._generate_headers_for_api(api),
                    request_type=self._get_request_type(api),
                    data=test_data,
                    is_run=True,
                    detail=f"测试{api.summary}的异常情况",
                    dependence_case=False,
                    dependence_case_data=None,
                    current_request_set_cache=None,
                    sql=None,
                    assert_data=assert_data,
                    setup_sql=None,
                    teardown=None,
                    teardown_sql=None,
                    sleep=None
                )
                
                test_cases.append(test_case)
                
            # 创建测试套件
            test_suite = TestSuite(
                suite_id=f"suite_exception_{api_id.replace('/', '_').replace('{', '_').replace('}', '_')}",
                suite_name=f"{api.summary}异常测试",
                description=f"测试{api.summary}的异常情况",
                test_cases=test_cases,
                allure_epic="异常测试",
                allure_feature=getattr(api, 'tags', ['API'])[0] if getattr(api, 'tags', None) else 'API功能测试',
                allure_story=f"{api.summary}异常测试"
            )
            
            self.test_suites.append(test_suite)
            
    def _generate_test_data_for_api(self, api: APIEndpoint) -> Dict:
        """为API生成测试数据"""
        test_data = {}
        
        # 处理路径参数
        path_params = {}
        for param in api.parameters:
            if param.get('in') == 'path':
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                path_params[param_name] = TestDataGenerator.generate_data_by_type(param_type, param_name)
                
        if path_params:
            test_data['path_params'] = path_params
            
        # 处理查询参数
        query_params = {}
        for param in api.parameters:
            if param.get('in') == 'query':
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                query_params[param_name] = TestDataGenerator.generate_data_by_type(param_type, param_name)
                    
        if query_params:
            test_data['params'] = query_params
            
        # 处理请求体
        if api.request_body:
            content_types = api.request_body.get('content_types', [])
            if content_types:
                if 'headers' not in test_data:
                    test_data['headers'] = {}
                test_data['headers']['Content-Type'] = content_types[0]
                
                if 'application/json' in content_types[0]:
                    schema = api.request_body.get('schema', {})
                    test_data['data'] = self._generate_data_from_schema(schema)
                elif 'application/x-www-form-urlencoded' in content_types[0]:
                    schema = api.request_body.get('schema', {})
                    test_data['data'] = self._generate_data_from_schema(schema)
                elif 'multipart/form-data' in content_types[0]:
                    schema = api.request_body.get('schema', {})
                    test_data['data'] = self._generate_data_from_schema(schema)
        
        # 针对飞书API的特殊处理
        if hasattr(api, 'host') and 'open.feishu.cn' in api.host:
            test_data = self._enhance_feishu_test_data(test_data, api)
            
        return test_data
    
    def _enhance_feishu_test_data(self, test_data: Dict, api: APIEndpoint) -> Dict:
        """增强飞书API的测试数据"""
        # 飞书API通常需要特定的数据结构
        if api.path.startswith('/open-apis/im/v1/messages'):
            # 飞书发送消息API
            if 'data' not in test_data:
                test_data['data'] = {}
            if 'receive_id_type' not in test_data['data']:
                test_data['data']['receive_id_type'] = 'user_id'
            if 'receive_id' not in test_data['data']:
                test_data['data']['receive_id'] = 'test_user_id'
            if 'msg_type' not in test_data['data']:
                test_data['data']['msg_type'] = 'text'
            if 'content' not in test_data['data']:
                test_data['data']['content'] = json.dumps({"text": "这是一条测试消息"})
                
        elif api.path.startswith('/open-apis/contact/v3/users'):
            # 飞书用户API
            if 'data' not in test_data:
                test_data['data'] = {}
            if 'user_id_type' not in test_data['data']:
                test_data['data']['user_id_type'] = 'user_id'
                
        elif api.path.startswith('/open-apis/authen/v1'):
            # 飞书认证API
            if 'data' not in test_data:
                test_data['data'] = {}
            if 'app_id' not in test_data['data']:
                test_data['data']['app_id'] = 'test_app_id'
            if 'app_secret' not in test_data['data']:
                test_data['data']['app_secret'] = 'test_app_secret'
                
        return test_data
        
    def _generate_data_from_schema(self, schema: Dict) -> Dict:
        """根据schema生成数据"""
        if not schema:
            return {}
            
        data = {}
        
        # 处理对象类型
        if schema.get('type') == 'object' and 'properties' in schema:
            properties = schema['properties']
            for prop_name, prop_schema in properties.items():
                data[prop_name] = self._generate_data_from_schema(prop_schema)
                
        # 处理数组类型
        elif schema.get('type') == 'array':
            items_schema = schema.get('items', {})
            # 生成1-3个数组元素
            array_length = random.randint(1, 3)
            data = [self._generate_data_from_schema(items_schema) for _ in range(array_length)]
            
        # 处理基本类型
        else:
            data_type = schema.get('type', 'string')
            data = TestDataGenerator.generate_data_by_type(data_type)
            
        return data
        
    def _generate_boundary_test_data_for_api(self, api: APIEndpoint) -> List[Dict]:
        """为API生成边界值测试数据"""
        boundary_test_cases = []
        
        # 处理查询参数的边界值
        for param in api.parameters:
            if param.get('in') == 'query':
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                
                # 为字符串类型生成空字符串和超长字符串
                if param_type == 'string':
                    # 空字符串测试
                    empty_test = self._generate_test_data_for_api(api)
                    empty_test.setdefault('params', {})[param_name] = ""
                    boundary_test_cases.append((empty_test, 200))  # 假设空字符串是有效的
                    
                    # 超长字符串测试
                    long_test = self._generate_test_data_for_api(api)
                    long_test.setdefault('params', {})[param_name] = "a" * 1000  # 1000个字符
                    boundary_test_cases.append((long_test, 400))  # 假设超长字符串会导致错误
                    
                # 为数字类型生成边界值
                elif param_type in ['integer', 'number']:
                    # 0值测试
                    zero_test = self._generate_test_data_for_api(api)
                    zero_test.setdefault('params', {})[param_name] = 0
                    boundary_test_cases.append((zero_test, 200))  # 假设0是有效的
                    
                    # 负数测试
                    negative_test = self._generate_test_data_for_api(api)
                    negative_test.setdefault('params', {})[param_name] = -1
                    boundary_test_cases.append((negative_test, 400))  # 假设负数会导致错误
                    
        # 处理请求体的边界值
        request_body = api.request_body
        if request_body and 'schema' in request_body:
            schema = request_body['schema']
            
            # 空对象测试
            empty_body_test = self._generate_test_data_for_api(api)
            empty_body_test['json'] = {}
            boundary_test_cases.append((empty_body_test, 400))  # 假设空请求体会导致错误
            
            # 缺少必填字段测试
            if schema.get('type') == 'object' and 'properties' in schema:
                properties = schema['properties']
                required_fields = schema.get('required', [])
                
                if required_fields:
                    # 缺少第一个必填字段
                    missing_field_test = self._generate_test_data_for_api(api)
                    body_data = self._generate_data_from_schema(schema)
                    if required_fields[0] in body_data:
                        del body_data[required_fields[0]]
                    missing_field_test['json'] = body_data
                    boundary_test_cases.append((missing_field_test, 400))  # 假设缺少必填字段会导致错误
                    
        return boundary_test_cases
        
    def _generate_exception_test_data_for_api(self, api: APIEndpoint) -> List[Tuple[Dict, int]]:
        """为API生成异常测试数据"""
        exception_test_cases = []
        
        # 无效的HTTP方法测试
        invalid_method_test = {
            'method': 'INVALID',
            'path': api.path,
            'headers': self._generate_headers_for_api(api),
            'data': {}
        }
        exception_test_cases.append((invalid_method_test, 405))  # Method Not Allowed
        
        # 无效的路径测试
        invalid_path_test = self._generate_test_data_for_api(api)
        invalid_path_test['path'] = api.path + '/invalid'
        exception_test_cases.append((invalid_path_test, 404))  # Not Found
        
        # 无效的参数测试
        for param in api.parameters:
            if param.get('in') == 'query':
                param_name = param.get('name', '')
                
                # 无效的参数类型测试
                invalid_type_test = self._generate_test_data_for_api(api)
                invalid_type_test.setdefault('params', {})[param_name] = "invalid_type"
                exception_test_cases.append((invalid_type_test, 400))  # Bad Request
                
        return exception_test_cases
        
    def _generate_headers_for_api(self, api: APIEndpoint) -> Dict:
        """为API生成请求头"""
        headers = {}
        
        # 从API文档中提取请求头
        for param in api.parameters:
            if param.get('in') == 'header':
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                headers[param_name] = TestDataGenerator.generate_data_by_type(param_type, param_name)
                
        # 添加默认的Content-Type
        if api.request_body:
            content_types = api.request_body.get('content_types', [])
            if content_types:
                headers['Content-Type'] = content_types[0]
        
        # 检查是否为飞书API，添加特殊认证
        if hasattr(api, 'host') and 'open.feishu.cn' in api.host:
            headers["Authorization"] = "Bearer ${feishu_token()}"
            
        return headers
        
    def _get_request_type(self, api: APIEndpoint) -> str:
        """获取API的请求类型"""
        if not api.request_body:
            return 'NONE'
            
        content_types = api.request_body.get('content_types', [])
        if not content_types:
            return 'NONE'
            
        content_type = content_types[0]
        
        if 'application/json' in content_type:
            return 'JSON'
        elif 'application/x-www-form-urlencoded' in content_type:
            return 'DATA'
        elif 'multipart/form-data' in content_type:
            return 'FILE'
        else:
            return 'DATA'
            
    def _generate_assert_data_for_api(self, api: APIEndpoint) -> Dict:
        """为API生成断言数据"""
        assert_data = {}
        
        # 添加状态码断言
        if '200' in api.response_codes:
            assert_data['status_code'] = 200
        elif api.response_codes:
            assert_data['status_code'] = int(api.response_codes[0])
        else:
            assert_data['status_code'] = 200
            
        # 添加响应数据断言
        if api.success_response and 'schema' in api.success_response:
            schema = api.success_response['schema']
            assert_paths = self._extract_assert_paths_from_schema(schema)
            
            for path in assert_paths:
                assert_data[path] = {
                    'jsonpath': path,
                    'type': 'equals',
                    'value': None,  # 不检查具体值，只检查路径存在
                    'AssertType': None
                }
                
        return assert_data
        
    def _extract_assert_paths_from_schema(self, schema: Dict, prefix: str = "$") -> List[str]:
        """从schema中提取断言路径"""
        paths = []
        
        if not schema:
            return paths
            
        # 处理对象类型
        if schema.get('type') == 'object' and 'properties' in schema:
            properties = schema['properties']
            for prop_name, prop_schema in properties.items():
                path = f"{prefix}.{prop_name}"
                paths.append(path)
                
                # 递归处理嵌套对象
                nested_paths = self._extract_assert_paths_from_schema(prop_schema, path)
                paths.extend(nested_paths)
                
        # 处理数组类型
        elif schema.get('type') == 'array':
            items_schema = schema.get('items', {})
            path = f"{prefix}[0]"  # 检查第一个元素
            paths.append(path)
            
            # 递归处理数组元素
            nested_paths = self._extract_assert_paths_from_schema(items_schema, path)
            paths.extend(nested_paths)
            
        return paths
        
    def _find_dependencies_for_api(self, api_id: str, preceding_apis: List[str]) -> List[DataDependency]:
        """查找API的依赖关系"""
        dependencies = []
        
        # 获取所有数据依赖关系
        all_dependencies = self.analyzer.get_data_dependencies()
        
        # 筛选出当前API的依赖关系，且依赖的API在前面已经执行
        for dep in all_dependencies:
            if dep.target_api == api_id and dep.source_api in preceding_apis:
                dependencies.append(dep)
                
        return dependencies
        
    def _generate_dependence_data(self, dependencies: List[DataDependency]) -> Dict:
        """生成依赖数据"""
        if not dependencies:
            return None
            
        dependence_data = {
            'case_id': dependencies[0].source_api,
            'dependent_data': {}
        }
        
        for dep in dependencies:
            dependence_data['dependent_data'][dep.target_path] = {
                'source_path': dep.source_path,
                'description': dep.description
            }
            
        return dependence_data
        
    def _generate_cache_data(self, api: APIEndpoint) -> Dict:
        """生成缓存数据"""
        cache_data = {}
        
        # 根据API响应生成缓存数据
        if api.success_response and 'schema' in api.success_response:
            schema = api.success_response['schema']
            cache_paths = self._extract_cache_paths_from_schema(schema)
            
            for path in cache_paths:
                cache_data[path] = True  # 标记需要缓存
                
        return cache_data
        
    def _extract_cache_paths_from_schema(self, schema: Dict, prefix: str = "$") -> List[str]:
        """从schema中提取缓存路径"""
        # 简化实现，使用与断言路径相同的逻辑
        return self._extract_assert_paths_from_schema(schema, prefix)
        
    def export_test_cases(self) -> None:
        """导出测试用例到YAML文件"""
        try:
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            for suite in self.test_suites:
                # 创建测试套件目录
                suite_dir = os.path.join(self.output_dir, suite.suite_id)
                os.makedirs(suite_dir, exist_ok=True)
                
                # 创建YAML文件
                yaml_file = os.path.join(suite_dir, f"{suite.suite_id}.yaml")
                
                # 构建YAML数据结构
                yaml_data = {
                    'case_common': {
                        'allureEpic': suite.allure_epic,
                        'allureFeature': suite.allure_feature,
                        'allureStory': suite.allure_story
                    }
                }
                
                # 添加测试用例
                for case in suite.test_cases:
                    case_data = {
                        'host': case.host,
                        'url': case.api_path,
                        'method': case.api_method,
                        'headers': case.headers,
                        'requestType': case.request_type,
                        'is_run': case.is_run,
                        'data': case.data,
                        'dependence_case': case.dependence_case,
                        'assert': case.assert_data
                    }
                    
                    # 添加可选字段
                    if case.dependence_case_data:
                        case_data['dependence_case_data'] = case.dependence_case_data
                        
                    if case.current_request_set_cache:
                        case_data['current_request_set_cache'] = case.current_request_set_cache
                        
                    if case.sql:
                        case_data['sql'] = case.sql
                        
                    if case.setup_sql:
                        case_data['setup_sql'] = case.setup_sql
                        
                    if case.teardown:
                        case_data['teardown'] = case.teardown
                        
                    if case.teardown_sql:
                        case_data['teardown_sql'] = case.teardown_sql
                        
                    if case.sleep:
                        case_data['sleep'] = case.sleep
                        
                    yaml_data[case.case_id] = case_data
                    
                # 写入YAML文件
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
                    
                INFO.logger.info(f"测试套件已导出到: {yaml_file}")
                
        except Exception as e:
            ERROR.logger.error(f"导出测试用例失败: {str(e)}")
            raise TestGenerationError(f"导出测试用例失败: {str(e)}")


def generate_test_cases(api_doc_path: str, output_dir: str = None) -> List[TestSuite]:
    """
    生成测试用例
    :param api_doc_path: API文档路径
    :param output_dir: 输出目录
    :return: 测试套件列表
    """
    generator = TestCaseGenerator(api_doc_path, output_dir)
    test_suites = generator.generate_test_cases()
    generator.export_test_cases()
    return test_suites


if __name__ == '__main__':
    # 示例用法
    try:
        # 生成测试用例
        test_suites = generate_test_cases('path/to/swagger.yaml', './test_cases')
        print(f"生成了 {len(test_suites)} 个测试套件")
        
    except Exception as e:
        print(f"生成测试用例失败: {str(e)}")