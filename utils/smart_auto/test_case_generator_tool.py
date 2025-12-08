"""
测试用例生成工具
支持从指定路径读取OpenAPI文档、API依赖关系和测试场景，并生成测试用例
"""

import os
import json
import yaml
import random
import string
from typing import Dict, List, Any, Optional, Tuple, Type
from pydantic import BaseModel
from langchain.tools import BaseTool
from dataclasses import dataclass


@dataclass
class GeneratedTestCase:
    """生成的测试用例"""
    name: str
    description: str
    method: str
    path: str
    headers: Dict[str, str]
    params: Dict[str, Any]
    body: Optional[Dict[str, Any]]
    expected_status: int
    expected_response: Optional[Dict[str, Any]]
    assertions: List[Dict[str, Any]]
    preconditions: List[Dict[str, Any]]
    postconditions: List[Dict[str, Any]]


@dataclass
class GeneratedTestSuite:
    """生成的测试套件"""
    name: str
    description: str
    test_cases: List[GeneratedTestCase]


class TestCaseGeneratorInput(BaseModel):
    """测试用例生成器的输入参数"""
    file_id: str  # 用于从指定路径读取OpenAPI文档、API依赖关系和测试场景
    test_type: str = "all"  # 测试类型: basic(基础测试), boundary(边界测试), error(错误测试), scene(场景测试), all(全部)


class TestCaseGeneratorTool(BaseTool):
    """测试用例生成工具"""
    name = "test_case_generator"
    description = "根据OpenAPI文档、API依赖关系和测试场景生成测试用例"
    args_schema: Type[BaseModel] = TestCaseGeneratorInput

    def _run(self, file_id: str, test_type: str = "all") -> Dict[str, Any]:
        """执行测试用例生成"""
        try:
            # 加载OpenAPI文档
            openapi_doc = self._load_openapi_document(file_id)
            if not openapi_doc:
                return {"error": "无法加载OpenAPI文档"}
            
            # 加载API依赖关系
            api_relation = self._load_api_relation(file_id)
            
            # 加载测试场景
            test_scene = self._load_test_scene(file_id)
            
            # 提取API端点信息
            endpoints = self._extract_endpoints(openapi_doc)
            
            # 根据测试类型生成测试用例
            test_suites = []
            
            if test_type in ["all", "basic"]:
                basic_suite = self._generate_basic_test_cases(endpoints)
                test_suites.append(basic_suite)
            
            if test_type in ["all", "boundary"]:
                boundary_suite = self._generate_boundary_test_cases(endpoints)
                test_suites.append(boundary_suite)
            
            if test_type in ["all", "error"]:
                error_suite = self._generate_error_test_cases(endpoints)
                test_suites.append(error_suite)
            
            if test_type in ["all", "scene"] and test_scene:
                scene_suite = self._generate_scene_based_test_cases(test_scene, endpoints)
                test_suites.extend(scene_suite)
            
            if test_type in ["all", "relation"] and api_relation:
                relation_suite = self._generate_relation_based_test_cases(api_relation, endpoints)
                test_suites.extend(relation_suite)
            
            # 生成测试统计信息
            stats = self._generate_test_statistics(test_suites)
            
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
                                "path": case.path,
                                "headers": case.headers,
                                "params": case.params,
                                "body": case.body,
                                "expected_status": case.expected_status,
                                "expected_response": case.expected_response,
                                "assertions": case.assertions,
                                "preconditions": case.preconditions,
                                "postconditions": case.postconditions
                            }
                            for case in suite.test_cases
                        ]
                    }
                    for suite in test_suites
                ],
                "statistics": stats
            }
        except Exception as e:
            return {"error": f"生成测试用例时出错: {str(e)}"}
    
    def _load_openapi_document(self, file_id: str) -> Optional[Dict]:
        """加载OpenAPI文档"""
        # 尝试YAML格式
        yaml_path = f"/Users/oss/code/PytestAutoApi/uploads/openapi/{file_id}.yaml"
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        # 尝试JSON格式
        json_path = f"/Users/oss/code/PytestAutoApi/uploads/openapi/{file_id}.json"
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def _load_api_relation(self, file_id: str) -> Optional[Dict]:
        """加载API依赖关系"""
        relation_path = f"/Users/oss/code/PytestAutoApi/uploads/relation/{file_id}.json"
        if os.path.exists(relation_path):
            with open(relation_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def _load_test_scene(self, file_id: str) -> Optional[Dict]:
        """加载测试场景"""
        scene_path = f"/Users/oss/code/PytestAutoApi/uploads/scene/{file_id}.json"
        if os.path.exists(scene_path):
            with open(scene_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def _extract_endpoints(self, openapi_doc: Dict) -> List[Dict]:
        """从OpenAPI文档中提取API端点信息"""
        endpoints = []
        
        if "paths" not in openapi_doc:
            return endpoints
        
        for path, path_item in openapi_doc["paths"].items():
            for method, endpoint in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "operation_id": endpoint.get("operationId", f"{method}_{path}"),
                        "summary": endpoint.get("summary", ""),
                        "description": endpoint.get("description", ""),
                        "parameters": endpoint.get("parameters", []),
                        "requestBody": endpoint.get("requestBody", {}),
                        "responses": endpoint.get("responses", {}),
                        "security": endpoint.get("security", []),
                        "tags": endpoint.get("tags", [])
                    })
        
        return endpoints
    
    def _generate_basic_test_cases(self, endpoints: List[Dict]) -> GeneratedTestSuite:
        """生成基础测试用例"""
        test_cases = []
        
        for endpoint in endpoints:
            # 生成基础请求参数
            params = self._generate_basic_params(endpoint.get("parameters", []))
            
            # 生成基础请求体
            body = self._generate_basic_body(endpoint.get("requestBody", {}))
            
            # 生成请求头
            headers = self._generate_headers(endpoint)
            
            # 获取预期成功状态码
            expected_status = self._get_expected_success_status(endpoint["method"])
            
            # 生成预期响应
            expected_response = self._generate_expected_response(endpoint, {}, expected_status)
            
            # 生成断言
            assertions = self._generate_assertions(endpoint, expected_status, expected_response)
            
            # 生成前置条件和后置条件
            preconditions = self._generate_preconditions(endpoint)
            postconditions = self._generate_postconditions(endpoint)
            
            test_case = GeneratedTestCase(
                name=f"基础测试 - {endpoint['summary'] or endpoint['operation_id']}",
                description=f"测试{endpoint['method']} {endpoint['path']}的基础功能",
                method=endpoint["method"],
                path=endpoint["path"],
                headers=headers,
                params=params,
                body=body,
                expected_status=expected_status,
                expected_response=expected_response,
                assertions=assertions,
                preconditions=preconditions,
                postconditions=postconditions
            )
            
            test_cases.append(test_case)
        
        return GeneratedTestSuite(
            name="基础测试套件",
            description="包含所有API的基础功能测试用例",
            test_cases=test_cases
        )
    
    def _generate_boundary_test_cases(self, endpoints: List[Dict]) -> GeneratedTestSuite:
        """生成边界测试用例"""
        test_cases = []
        
        for endpoint in endpoints:
            # 生成边界测试用例
            boundary_cases = [
                ("空参数测试", "测试空参数情况", "empty_params"),
                ("最大长度测试", "测试参数最大长度情况", "max_length"),
                ("最小长度测试", "测试参数最小长度情况", "min_length")
            ]
            
            for case_name, case_desc, case_type in boundary_cases:
                # 生成边界请求参数
                params = self._generate_boundary_params(endpoint.get("parameters", []), case_type)
                
                # 生成边界请求体
                body = self._generate_boundary_body(endpoint.get("requestBody", {}), case_type)
                
                # 生成请求头
                headers = self._generate_headers(endpoint)
                
                # 获取预期成功状态码
                expected_status = self._get_expected_success_status(endpoint["method"])
                
                # 生成预期响应
                expected_response = self._generate_expected_response(endpoint, {}, expected_status)
                
                # 生成断言
                assertions = self._generate_assertions(endpoint, expected_status, expected_response)
                
                # 生成前置条件和后置条件
                preconditions = self._generate_preconditions(endpoint)
                postconditions = self._generate_postconditions(endpoint)
                
                test_case = GeneratedTestCase(
                    name=f"{case_name} - {endpoint['summary'] or endpoint['operation_id']}",
                    description=f"{case_desc}: {endpoint['method']} {endpoint['path']}",
                    method=endpoint["method"],
                    path=endpoint["path"],
                    headers=headers,
                    params=params,
                    body=body,
                    expected_status=expected_status,
                    expected_response=expected_response,
                    assertions=assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                test_cases.append(test_case)
        
        return GeneratedTestSuite(
            name="边界测试套件",
            description="包含所有API的边界条件测试用例",
            test_cases=test_cases
        )
    
    def _generate_error_test_cases(self, endpoints: List[Dict]) -> GeneratedTestSuite:
        """生成错误测试用例"""
        test_cases = []
        
        for endpoint in endpoints:
            # 生成错误测试用例
            error_cases = [
                ("缺少必需参数测试", "测试缺少必需参数情况", "missing_required"),
                ("无效格式测试", "测试参数格式错误情况", "invalid_format"),
                ("未授权测试", "测试未授权访问情况", "unauthorized")
            ]
            
            for case_name, case_desc, case_type in error_cases:
                # 生成错误请求参数
                params = self._generate_error_params(endpoint.get("parameters", []), case_type)
                
                # 生成错误请求体
                body = self._generate_error_body(endpoint.get("requestBody", {}), case_type)
                
                # 生成请求头
                headers = self._generate_headers(endpoint)
                
                # 对于未授权测试，移除认证头
                if case_type == "unauthorized" and "Authorization" in headers:
                    del headers["Authorization"]
                
                # 获取预期错误状态码
                expected_status = self._get_expected_error_status(case_type)
                
                # 生成预期响应
                expected_response = self._generate_expected_response(endpoint, {}, expected_status)
                
                # 生成断言
                assertions = self._generate_assertions(endpoint, expected_status, expected_response)
                
                # 生成前置条件和后置条件
                preconditions = self._generate_preconditions(endpoint)
                postconditions = self._generate_postconditions(endpoint)
                
                test_case = GeneratedTestCase(
                    name=f"{case_name} - {endpoint['summary'] or endpoint['operation_id']}",
                    description=f"{case_desc}: {endpoint['method']} {endpoint['path']}",
                    method=endpoint["method"],
                    path=endpoint["path"],
                    headers=headers,
                    params=params,
                    body=body,
                    expected_status=expected_status,
                    expected_response=expected_response,
                    assertions=assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                test_cases.append(test_case)
        
        return GeneratedTestSuite(
            name="错误测试套件",
            description="包含所有API的错误情况测试用例",
            test_cases=test_cases
        )
    
    def _generate_scene_based_test_cases(self, test_scene: Dict, endpoints: List[Dict]) -> List[GeneratedTestSuite]:
        """基于测试场景生成测试用例"""
        test_suites = []
        
        # 提取业务场景
        business_scenes = test_scene.get("business_scenes", [])
        
        for scene in business_scenes:
            scene_name = scene.get("name", "")
            scene_description = scene.get("description", "")
            scene_apis = scene.get("apis", [])
            
            test_cases = []
            
            # 为每个场景中的API生成测试用例
            for api_info in scene_apis:
                api_path = api_info.get("path", "")
                api_method = api_info.get("method", "")
                api_params = api_info.get("params", {})
                api_body = api_info.get("body", {})
                
                # 查找匹配的端点
                matching_endpoint = None
                for endpoint in endpoints:
                    if endpoint["path"] == api_path and endpoint["method"].upper() == api_method.upper():
                        matching_endpoint = endpoint
                        break
                
                if not matching_endpoint:
                    continue
                
                # 生成请求头
                headers = self._generate_headers(matching_endpoint)
                
                # 获取预期成功状态码
                expected_status = self._get_expected_success_status(matching_endpoint["method"])
                
                # 生成预期响应
                expected_response = self._generate_expected_response(matching_endpoint, {}, expected_status)
                
                # 生成断言
                assertions = self._generate_assertions(matching_endpoint, expected_status, expected_response)
                
                # 生成场景特定的前置条件和后置条件
                preconditions = self._generate_scene_preconditions(scene, api_info)
                postconditions = self._generate_scene_postconditions(scene, api_info)
                
                test_case = GeneratedTestCase(
                    name=f"场景测试 - {scene_name} - {matching_endpoint['summary'] or matching_endpoint['operation_id']}",
                    description=f"测试场景'{scene_name}'中的API: {matching_endpoint['method']} {matching_endpoint['path']}",
                    method=matching_endpoint["method"],
                    path=matching_endpoint["path"],
                    headers=headers,
                    params=api_params,
                    body=api_body,
                    expected_status=expected_status,
                    expected_response=expected_response,
                    assertions=assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                test_cases.append(test_case)
            
            if test_cases:
                test_suite = GeneratedTestSuite(
                    name=f"场景测试套件 - {scene_name}",
                    description=scene_description,
                    test_cases=test_cases
                )
                test_suites.append(test_suite)
        
        return test_suites
    
    def _generate_relation_based_test_cases(self, api_relation: Dict, endpoints: List[Dict]) -> List[GeneratedTestSuite]:
        """基于API依赖关系生成测试用例"""
        test_suites = []
        
        # 提取全局依赖API
        global_dependencies = api_relation.get("global_dependencies", [])
        
        # 提取条件依赖API
        conditional_dependencies = api_relation.get("conditional_dependencies", [])
        
        # 提取数据流转
        data_flows = api_relation.get("data_flows", [])
        
        # 提取权限关系
        permission_relations = api_relation.get("permission_relations", [])
        
        # 为全局依赖API生成测试用例
        if global_dependencies:
            global_test_cases = []
            
            for dep_info in global_dependencies:
                api_path = dep_info.get("path", "")
                api_method = dep_info.get("method", "")
                dependency_description = dep_info.get("description", "")
                
                # 查找匹配的端点
                matching_endpoint = None
                for endpoint in endpoints:
                    if endpoint["path"] == api_path and endpoint["method"].upper() == api_method.upper():
                        matching_endpoint = endpoint
                        break
                
                if not matching_endpoint:
                    continue
                
                # 生成基础请求参数和请求体
                params = self._generate_basic_params(matching_endpoint.get("parameters", []))
                body = self._generate_basic_body(matching_endpoint.get("requestBody", {}))
                
                # 生成请求头
                headers = self._generate_headers(matching_endpoint)
                
                # 获取预期成功状态码
                expected_status = self._get_expected_success_status(matching_endpoint["method"])
                
                # 生成预期响应
                expected_response = self._generate_expected_response(matching_endpoint, {}, expected_status)
                
                # 生成断言
                assertions = self._generate_assertions(matching_endpoint, expected_status, expected_response)
                
                # 生成依赖特定的前置条件和后置条件
                preconditions = self._generate_dependency_preconditions(dep_info)
                postconditions = self._generate_dependency_postconditions(dep_info)
                
                test_case = GeneratedTestCase(
                    name=f"依赖测试 - 全局依赖 - {matching_endpoint['summary'] or matching_endpoint['operation_id']}",
                    description=f"测试全局依赖API: {dependency_description} - {matching_endpoint['method']} {matching_endpoint['path']}",
                    method=matching_endpoint["method"],
                    path=matching_endpoint["path"],
                    headers=headers,
                    params=params,
                    body=body,
                    expected_status=expected_status,
                    expected_response=expected_response,
                    assertions=assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                global_test_cases.append(test_case)
            
            if global_test_cases:
                test_suite = GeneratedTestSuite(
                    name="依赖测试套件 - 全局依赖",
                    description="测试全局依赖API的测试用例",
                    test_cases=global_test_cases
                )
                test_suites.append(test_suite)
        
        # 为条件依赖API生成测试用例
        if conditional_dependencies:
            conditional_test_cases = []
            
            for dep_info in conditional_dependencies:
                api_path = dep_info.get("path", "")
                api_method = dep_info.get("method", "")
                dependency_description = dep_info.get("description", "")
                condition = dep_info.get("condition", "")
                
                # 查找匹配的端点
                matching_endpoint = None
                for endpoint in endpoints:
                    if endpoint["path"] == api_path and endpoint["method"].upper() == api_method.upper():
                        matching_endpoint = endpoint
                        break
                
                if not matching_endpoint:
                    continue
                
                # 生成基础请求参数和请求体
                params = self._generate_basic_params(matching_endpoint.get("parameters", []))
                body = self._generate_basic_body(matching_endpoint.get("requestBody", {}))
                
                # 生成请求头
                headers = self._generate_headers(matching_endpoint)
                
                # 获取预期成功状态码
                expected_status = self._get_expected_success_status(matching_endpoint["method"])
                
                # 生成预期响应
                expected_response = self._generate_expected_response(matching_endpoint, {}, expected_status)
                
                # 生成断言
                assertions = self._generate_assertions(matching_endpoint, expected_status, expected_response)
                
                # 生成依赖特定的前置条件和后置条件
                preconditions = self._generate_dependency_preconditions(dep_info)
                postconditions = self._generate_dependency_postconditions(dep_info)
                
                test_case = GeneratedTestCase(
                    name=f"依赖测试 - 条件依赖 - {matching_endpoint['summary'] or matching_endpoint['operation_id']}",
                    description=f"测试条件依赖API: {dependency_description} (条件: {condition}) - {matching_endpoint['method']} {matching_endpoint['path']}",
                    method=matching_endpoint["method"],
                    path=matching_endpoint["path"],
                    headers=headers,
                    params=params,
                    body=body,
                    expected_status=expected_status,
                    expected_response=expected_response,
                    assertions=assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                conditional_test_cases.append(test_case)
            
            if conditional_test_cases:
                test_suite = GeneratedTestSuite(
                    name="依赖测试套件 - 条件依赖",
                    description="测试条件依赖API的测试用例",
                    test_cases=conditional_test_cases
                )
                test_suites.append(test_suite)
        
        # 为数据流转生成测试用例
        if data_flows:
            flow_test_cases = []
            
            for flow_info in data_flows:
                source_api = flow_info.get("source_api", {})
                target_api = flow_info.get("target_api", {})
                flow_description = flow_info.get("description", "")
                data_mapping = flow_info.get("data_mapping", {})
                
                # 查找匹配的源端点
                source_endpoint = None
                for endpoint in endpoints:
                    if endpoint["path"] == source_api.get("path", "") and endpoint["method"].upper() == source_api.get("method", "").upper():
                        source_endpoint = endpoint
                        break
                
                # 查找匹配的目标端点
                target_endpoint = None
                for endpoint in endpoints:
                    if endpoint["path"] == target_api.get("path", "") and endpoint["method"].upper() == target_api.get("method", "").upper():
                        target_endpoint = endpoint
                        break
                
                if not source_endpoint or not target_endpoint:
                    continue
                
                # 生成源API的请求参数和请求体
                source_params = self._generate_basic_params(source_endpoint.get("parameters", []))
                source_body = self._generate_basic_body(source_endpoint.get("requestBody", {}))
                
                # 生成源API的请求头
                source_headers = self._generate_headers(source_endpoint)
                
                # 获取源API的预期成功状态码
                source_expected_status = self._get_expected_success_status(source_endpoint["method"])
                
                # 生成源API的预期响应
                source_expected_response = self._generate_expected_response(source_endpoint, {}, source_expected_status)
                
                # 生成源API的断言
                source_assertions = self._generate_assertions(source_endpoint, source_expected_status, source_expected_response)
                
                # 生成数据流转特定的前置条件和后置条件
                preconditions = self._generate_flow_preconditions(flow_info, source_api)
                postconditions = self._generate_flow_postconditions(flow_info, target_api)
                
                test_case = GeneratedTestCase(
                    name=f"数据流转测试 - {source_endpoint['summary'] or source_endpoint['operation_id']}",
                    description=f"测试数据流转: {flow_description} - {source_endpoint['method']} {source_endpoint['path']} -> {target_endpoint['method']} {target_endpoint['path']}",
                    method=source_endpoint["method"],
                    path=source_endpoint["path"],
                    headers=source_headers,
                    params=source_params,
                    body=source_body,
                    expected_status=source_expected_status,
                    expected_response=source_expected_response,
                    assertions=source_assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                flow_test_cases.append(test_case)
            
            if flow_test_cases:
                test_suite = GeneratedTestSuite(
                    name="数据流转测试套件",
                    description="测试API间数据流转的测试用例",
                    test_cases=flow_test_cases
                )
                test_suites.append(test_suite)
        
        # 为权限关系生成测试用例
        if permission_relations:
            permission_test_cases = []
            
            for perm_info in permission_relations:
                api_path = perm_info.get("path", "")
                api_method = perm_info.get("method", "")
                permission_description = perm_info.get("description", "")
                required_permission = perm_info.get("required_permission", "")
                
                # 查找匹配的端点
                matching_endpoint = None
                for endpoint in endpoints:
                    if endpoint["path"] == api_path and endpoint["method"].upper() == api_method.upper():
                        matching_endpoint = endpoint
                        break
                
                if not matching_endpoint:
                    continue
                
                # 生成基础请求参数和请求体
                params = self._generate_basic_params(matching_endpoint.get("parameters", []))
                body = self._generate_basic_body(matching_endpoint.get("requestBody", {}))
                
                # 生成请求头（包含权限信息）
                headers = self._generate_headers(matching_endpoint)
                headers["X-Permission"] = required_permission
                
                # 获取预期成功状态码
                expected_status = self._get_expected_success_status(matching_endpoint["method"])
                
                # 生成预期响应
                expected_response = self._generate_expected_response(matching_endpoint, {}, expected_status)
                
                # 生成断言
                assertions = self._generate_assertions(matching_endpoint, expected_status, expected_response)
                
                # 生成权限特定的前置条件和后置条件
                preconditions = self._generate_permission_preconditions(perm_info)
                postconditions = self._generate_permission_postconditions(perm_info)
                
                test_case = GeneratedTestCase(
                    name=f"权限测试 - {matching_endpoint['summary'] or matching_endpoint['operation_id']}",
                    description=f"测试权限关系: {permission_description} (需要权限: {required_permission}) - {matching_endpoint['method']} {matching_endpoint['path']}",
                    method=matching_endpoint["method"],
                    path=matching_endpoint["path"],
                    headers=headers,
                    params=params,
                    body=body,
                    expected_status=expected_status,
                    expected_response=expected_response,
                    assertions=assertions,
                    preconditions=preconditions,
                    postconditions=postconditions
                )
                
                permission_test_cases.append(test_case)
            
            if permission_test_cases:
                test_suite = GeneratedTestSuite(
                    name="权限测试套件",
                    description="测试API权限关系的测试用例",
                    test_cases=permission_test_cases
                )
                test_suites.append(test_suite)
        
        return test_suites
    
    def _generate_test_statistics(self, test_suites: List[GeneratedTestSuite]) -> Dict[str, int]:
        """生成测试统计信息"""
        total_suites = len(test_suites)
        total_cases = sum(len(suite.test_cases) for suite in test_suites)
        
        # 按类型统计测试用例数量
        basic_cases = 0
        boundary_cases = 0
        error_cases = 0
        scene_cases = 0
        relation_cases = 0
        
        for suite in test_suites:
            for case in suite.test_cases:
                if "基础" in case.name:
                    basic_cases += 1
                elif "边界" in case.name:
                    boundary_cases += 1
                elif "错误" in case.name:
                    error_cases += 1
                elif "scene" in suite.name:
                    scene_cases += 1
                else:
                    relation_cases += 1
        
        return {
            "total_suites": total_suites,
            "total_cases": total_cases,
            "basic_cases": basic_cases,
            "boundary_cases": boundary_cases,
            "error_cases": error_cases,
            "scene_cases": scene_cases,
            "relation_cases": relation_cases
        }
    
    # 以下是辅助方法，用于生成各种测试数据
    
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
    
    def _get_expected_error_status(self, case_type: str) -> int:
        """获取预期错误状态码"""
        if case_type == "missing_required":
            return 400
        elif case_type == "invalid_format":
            return 400
        elif case_type == "unauthorized":
            return 401
        else:
            return 400
    
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
    
    def _generate_preconditions(self, endpoint: Dict) -> List[Dict[str, Any]]:
        """生成前置条件"""
        preconditions = []
        
        # 添加通用前置条件
        preconditions.append({
            "type": "api_available",
            "description": f"确保API {endpoint['method']} {endpoint['path']} 可用"
        })
        
        # 如果API需要认证，添加认证前置条件
        if endpoint.get("security"):
            preconditions.append({
                "type": "authenticated",
                "description": "确保用户已认证"
            })
        
        return preconditions
    
    def _generate_postconditions(self, endpoint: Dict) -> List[Dict[str, Any]]:
        """生成后置条件"""
        postconditions = []
        
        # 添加通用后置条件
        postconditions.append({
            "type": "response_received",
            "description": "确保收到响应"
        })
        
        return postconditions
    
    def _generate_scene_preconditions(self, scene: Dict, api_info: Dict) -> List[Dict[str, Any]]:
        """生成场景特定的前置条件"""
        preconditions = []
        
        # 添加场景前置条件
        scene_preconditions = scene.get("preconditions", [])
        for condition in scene_preconditions:
            preconditions.append({
                "type": "scene_condition",
                "description": condition.get("description", "")
            })
        
        # 添加API特定的前置条件
        api_preconditions = api_info.get("preconditions", [])
        for condition in api_preconditions:
            preconditions.append({
                "type": "api_condition",
                "description": condition.get("description", "")
            })
        
        return preconditions
    
    def _generate_scene_postconditions(self, scene: Dict, api_info: Dict) -> List[Dict[str, Any]]:
        """生成场景特定的后置条件"""
        postconditions = []
        
        # 添加场景后置条件
        scene_postconditions = scene.get("postconditions", [])
        for condition in scene_postconditions:
            postconditions.append({
                "type": "scene_condition",
                "description": condition.get("description", "")
            })
        
        # 添加API特定的后置条件
        api_postconditions = api_info.get("postconditions", [])
        for condition in api_postconditions:
            postconditions.append({
                "type": "api_condition",
                "description": condition.get("description", "")
            })
        
        return postconditions
    
    def _generate_dependency_preconditions(self, dep_info: Dict) -> List[Dict[str, Any]]:
        """生成依赖特定的前置条件"""
        preconditions = []
        
        # 添加依赖前置条件
        dependency_preconditions = dep_info.get("preconditions", [])
        for condition in dependency_preconditions:
            preconditions.append({
                "type": "dependency_condition",
                "description": condition.get("description", "")
            })
        
        return preconditions
    
    def _generate_dependency_postconditions(self, dep_info: Dict) -> List[Dict[str, Any]]:
        """生成依赖特定的后置条件"""
        postconditions = []
        
        # 添加依赖后置条件
        dependency_postconditions = dep_info.get("postconditions", [])
        for condition in dependency_postconditions:
            postconditions.append({
                "type": "dependency_condition",
                "description": condition.get("description", "")
            })
        
        return postconditions
    
    def _generate_flow_preconditions(self, flow_info: Dict, source_api: Dict) -> List[Dict[str, Any]]:
        """生成数据流转特定的前置条件"""
        preconditions = []
        
        # 添加数据流转前置条件
        flow_preconditions = flow_info.get("preconditions", [])
        for condition in flow_preconditions:
            preconditions.append({
                "type": "flow_condition",
                "description": condition.get("description", "")
            })
        
        # 添加源API特定的前置条件
        source_preconditions = source_api.get("preconditions", [])
        for condition in source_preconditions:
            preconditions.append({
                "type": "source_condition",
                "description": condition.get("description", "")
            })
        
        return preconditions
    
    def _generate_flow_postconditions(self, flow_info: Dict, target_api: Dict) -> List[Dict[str, Any]]:
        """生成数据流转特定的后置条件"""
        postconditions = []
        
        # 添加数据流转后置条件
        flow_postconditions = flow_info.get("postconditions", [])
        for condition in flow_postconditions:
            postconditions.append({
                "type": "flow_condition",
                "description": condition.get("description", "")
            })
        
        # 添加目标API特定的后置条件
        target_postconditions = target_api.get("postconditions", [])
        for condition in target_postconditions:
            postconditions.append({
                "type": "target_condition",
                "description": condition.get("description", "")
            })
        
        return postconditions
    
    def _generate_permission_preconditions(self, perm_info: Dict) -> List[Dict[str, Any]]:
        """生成权限特定的前置条件"""
        preconditions = []
        
        # 添加权限前置条件
        permission_preconditions = perm_info.get("preconditions", [])
        for condition in permission_preconditions:
            preconditions.append({
                "type": "permission_condition",
                "description": condition.get("description", "")
            })
        
        # 添加用户具有所需权限的前置条件
        required_permission = perm_info.get("required_permission", "")
        if required_permission:
            preconditions.append({
                "type": "user_has_permission",
                "description": f"确保用户具有权限: {required_permission}"
            })
        
        return preconditions
    
    def _generate_permission_postconditions(self, perm_info: Dict) -> List[Dict[str, Any]]:
        """生成权限特定的后置条件"""
        postconditions = []
        
        # 添加权限后置条件
        permission_postconditions = perm_info.get("postconditions", [])
        for condition in permission_postconditions:
            postconditions.append({
                "type": "permission_condition",
                "description": condition.get("description", "")
            })
        
        return postconditions
    
    def _generate_basic_params(self, parameters: List[Dict]) -> Dict[str, Any]:
        """生成基础请求参数"""
        params = {}
        
        for param in parameters:
            param_name = param.get("name", "")
            param_in = param.get("in", "")
            param_required = param.get("required", False)
            param_schema = param.get("schema", {})
            param_type = param_schema.get("type", "string")
            
            # 只生成必需参数和一些可选参数
            if param_required or random.random() > 0.3:
                if param_in == "query":
                    params[param_name] = self._generate_basic_value(param_type, param_schema)
        
        return params
    
    def _generate_boundary_params(self, parameters: List[Dict], case_type: str) -> Dict[str, Any]:
        """生成边界请求参数"""
        params = {}
        
        for param in parameters:
            param_name = param.get("name", "")
            param_in = param.get("in", "")
            param_required = param.get("required", False)
            param_schema = param.get("schema", {})
            param_type = param_schema.get("type", "string")
            
            # 只生成必需参数和一些可选参数
            if param_required or random.random() > 0.3:
                if param_in == "query":
                    params[param_name] = self._generate_boundary_value(param_type, param_schema, case_type)
        
        return params
    
    def _generate_error_params(self, parameters: List[Dict], case_type: str) -> Dict[str, Any]:
        """生成错误请求参数"""
        params = {}
        
        for param in parameters:
            param_name = param.get("name", "")
            param_in = param.get("in", "")
            param_required = param.get("required", False)
            param_schema = param.get("schema", {})
            param_type = param_schema.get("type", "string")
            
            # 对于缺少必需参数的情况，不生成该参数
            if case_type == "missing_required" and param_required:
                continue
            
            # 只生成必需参数和一些可选参数
            if param_required or random.random() > 0.3:
                if param_in == "query":
                    params[param_name] = self._generate_error_value(param_type, param_schema, case_type)
        
        return params
    
    def _generate_basic_body(self, request_body: Dict) -> Optional[Dict[str, Any]]:
        """生成基础请求体"""
        if not request_body:
            return None
        
        content = request_body.get("content", {})
        json_content = content.get("application/json")
        
        if not json_content:
            return None
        
        schema = json_content.get("schema", {})
        
        # 根据模式生成示例请求体
        return self._generate_basic_object(schema, {})
    
    def _generate_boundary_body(self, request_body: Dict, case_type: str) -> Optional[Dict[str, Any]]:
        """生成边界请求体"""
        if not request_body:
            return None
        
        content = request_body.get("content", {})
        json_content = content.get("application/json")
        
        if not json_content:
            return None
        
        schema = json_content.get("schema", {})
        
        # 根据模式生成边界请求体
        return self._generate_boundary_object(schema, {}, case_type)
    
    def _generate_error_body(self, request_body: Dict, case_type: str) -> Optional[Dict[str, Any]]:
        """生成错误请求体"""
        if not request_body:
            return None
        
        content = request_body.get("content", {})
        json_content = content.get("application/json")
        
        if not json_content:
            return None
        
        schema = json_content.get("schema", {})
        
        # 根据模式生成错误请求体
        return self._generate_error_object(schema, {}, case_type)


def create_test_generator_tools():
    """创建测试用例生成相关的工具集"""
    return [
        TestCaseGeneratorTool()
    ]