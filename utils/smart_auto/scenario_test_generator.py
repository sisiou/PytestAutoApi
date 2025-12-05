#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2025/01/06 10:00
# @Author : Smart Auto Platform
# @File   : scenario_test_generator.py
# @describe: 基于场景和关联关系的智能测试用例生成模块
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from utils.smart_auto.api_parser import APIEndpoint, parse_api_document
from utils.smart_auto.test_generator import TestCaseGenerator, TestCase, TestSuite, TestDataGenerator
from utils.smart_auto.dependency_analyzer import analyze_api_dependencies, BusinessFlow, DataDependency
from utils.logging_tool.log_control import INFO, ERROR, WARNING
from utils.other_tools.exceptions import TestGenerationError

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class TestScenario:
    """测试场景数据类"""
    scenario_id: str
    scenario_name: str
    description: str
    api_endpoints: List[str]  # API端点列表，格式为 "method_path"
    preconditions: List[str] = field(default_factory=list)  # 前置条件
    postconditions: List[str] = field(default_factory=list)  # 后置条件
    test_data: Dict[str, Any] = field(default_factory=dict)  # 测试数据
    expected_results: Dict[str, Any] = field(default_factory=dict)  # 预期结果
    priority: str = "medium"  # 优先级：high, medium, low
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class APIRelationship:
    """API关联关系数据类"""
    relationship_id: str
    source_api: str  # 源API，格式为 "method_path"
    target_api: str  # 目标API，格式为 "method_path"
    relationship_type: str  # 关系类型：data_flow, sequence, dependency, etc.
    data_mapping: Dict[str, str] = field(default_factory=dict)  # 数据映射，源字段 -> 目标字段
    condition: Optional[str] = None  # 关联条件
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ScenarioTestGenerator:
    """基于场景和关联关系的测试用例生成器"""
    
    def __init__(self, api_doc_path: str, output_dir: str = None):
        """
        初始化场景测试用例生成器
        :param api_doc_path: API文档路径
        :param output_dir: 输出目录
        """
        self.api_doc_path = api_doc_path
        self.output_dir = output_dir or os.path.join(os.getcwd(), "generated_test_cases")
        self.apis = []
        self.api_dict = {}  # 将API存储为字典，便于查找
        self.test_generator = None
        self.scenarios = []
        self.relationships = []
        self.test_suites = []
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
    def parse_api_document(self) -> bool:
        """解析API文档"""
        try:
            INFO.logger.info(f"开始解析API文档: {self.api_doc_path}")
            
            # 使用现有的API解析器解析文档
            self.apis = parse_api_document(self.api_doc_path)
            
            # 将API转换为字典格式，便于查找
            self.api_dict = {}
            for api in self.apis:
                api_id = f"{api.method}_{api.path}"
                self.api_dict[api_id] = api
                
            INFO.logger.info(f"解析完成，共解析到 {len(self.apis)} 个API")
            return True
            
        except Exception as e:
            ERROR.logger.error(f"解析API文档失败: {str(e)}")
            return False
    
    def add_scenario(self, scenario: TestScenario) -> bool:
        """添加测试场景"""
        try:
            # 验证场景中的API端点是否存在
            for endpoint in scenario.api_endpoints:
                if endpoint not in self.api_dict:
                    ERROR.logger.error(f"场景中的API端点不存在: {endpoint}")
                    return False
            
            self.scenarios.append(scenario)
            INFO.logger.info(f"添加测试场景: {scenario.scenario_name}")
            return True
            
        except Exception as e:
            ERROR.logger.error(f"添加测试场景失败: {str(e)}")
            return False
    
    def add_relationship(self, relationship: APIRelationship) -> bool:
        """添加API关联关系"""
        try:
            # 验证关联关系中的API端点是否存在
            if relationship.source_api not in self.api_dict:
                ERROR.logger.error(f"关联关系中的源API端点不存在: {relationship.source_api}")
                return False
                
            if relationship.target_api not in self.api_dict:
                ERROR.logger.error(f"关联关系中的目标API端点不存在: {relationship.target_api}")
                return False
            
            self.relationships.append(relationship)
            INFO.logger.info(f"添加API关联关系: {relationship.source_api} -> {relationship.target_api}")
            return True
            
        except Exception as e:
            ERROR.logger.error(f"添加API关联关系失败: {str(e)}")
            return False
    
    def generate_test_cases(self) -> List[TestSuite]:
        """基于场景和关联关系生成测试用例"""
        try:
            INFO.logger.info("开始基于场景和关联关系生成测试用例...")
            
            # 确保API文档已解析
            if not self.apis:
                if not self.parse_api_document():
                    raise TestGenerationError("API文档解析失败")
            
            # 初始化测试用例生成器
            self.test_generator = TestCaseGenerator(self.api_doc_path, self.output_dir)
            
            # 为每个场景生成测试用例
            for scenario in self.scenarios:
                self._generate_test_cases_for_scenario(scenario)
            
            # 基于关联关系生成额外的测试用例
            self._generate_test_cases_for_relationships()
            
            INFO.logger.info(f"测试用例生成完成，共生成 {len(self.test_suites)} 个测试套件")
            return self.test_suites
            
        except Exception as e:
            ERROR.logger.error(f"生成测试用例失败: {str(e)}")
            raise TestGenerationError(f"生成测试用例失败: {str(e)}")
    
    def _generate_test_cases_for_scenario(self, scenario: TestScenario) -> None:
        """为特定场景生成测试用例"""
        INFO.logger.info(f"为场景生成测试用例: {scenario.scenario_name}")
        
        # 创建测试用例列表
        test_cases = []
        
        # 为场景中的每个API生成测试用例
        for i, api_endpoint in enumerate(scenario.api_endpoints):
            api = self.api_dict[api_endpoint]
            
            # 生成测试数据
            test_data = self._generate_test_data_for_scenario(scenario, api, i)
            
            # 如果不是第一个API，则需要依赖前面的API
            if i > 0:
                # 查找依赖关系
                dependencies = self._find_dependencies_for_api(api_endpoint, scenario.api_endpoints[:i])
                
                # 生成依赖数据
                dependence_case_data = self._generate_dependence_data(dependencies, scenario)
                
                # 设置当前请求缓存
                current_request_set_cache = self._generate_cache_data(api, scenario)
            else:
                dependencies = []
                dependence_case_data = None
                current_request_set_cache = None
            
            # 生成断言数据
            assert_data = self._generate_assert_data_for_scenario(scenario, api, i)
            
            # 创建测试用例
            case_id = f"scenario_{scenario.scenario_id}_{api_endpoint.replace('/', '_').replace('{', '_').replace('}', '_')}"
            
            test_case = TestCase(
                case_id=case_id,
                case_name=f"测试{api.summary} - {scenario.scenario_name}",
                api_method=api.method,
                api_path=api.path,
                host="${host()}",
                headers=self._generate_headers_for_api(api),
                request_type=self._get_request_type(api),
                data=test_data,
                is_run=True,
                detail=f"测试{api.summary}，场景: {scenario.scenario_name}",
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
            suite_id=f"suite_scenario_{scenario.scenario_id}",
            suite_name=scenario.scenario_name,
            description=scenario.description,
            test_cases=test_cases,
            allure_epic="场景测试",
            allure_feature=scenario.scenario_name,
            allure_story=scenario.description
        )
        
        self.test_suites.append(test_suite)
    
    def _generate_test_cases_for_relationships(self) -> None:
        """基于关联关系生成测试用例"""
        INFO.logger.info("基于关联关系生成测试用例...")
        
        # 按关系类型分组
        relationship_groups = {}
        for rel in self.relationships:
            rel_type = rel.relationship_type
            if rel_type not in relationship_groups:
                relationship_groups[rel_type] = []
            relationship_groups[rel_type].append(rel)
        
        # 为每种关系类型生成测试用例
        for rel_type, rels in relationship_groups.items():
            self._generate_test_cases_for_relationship_type(rel_type, rels)
    
    def _generate_test_cases_for_relationship_type(self, rel_type: str, relationships: List[APIRelationship]) -> None:
        """为特定类型的关联关系生成测试用例"""
        INFO.logger.info(f"为关联关系类型生成测试用例: {rel_type}")
        
        # 创建测试用例列表
        test_cases = []
        
        # 为每个关联关系生成测试用例
        for rel in relationships:
            source_api = self.api_dict[rel.source_api]
            target_api = self.api_dict[rel.target_api]
            
            # 生成源API的测试数据
            source_test_data = self._generate_test_data_for_relationship(rel, source_api, is_source=True)
            
            # 生成源API的断言数据
            source_assert_data = self._generate_assert_data_for_relationship(rel, source_api, is_source=True)
            
            # 创建源API的测试用例
            source_case_id = f"rel_{rel.relationship_id}_{rel.source_api.replace('/', '_').replace('{', '_').replace('}', '_')}"
            
            source_test_case = TestCase(
                case_id=source_case_id,
                case_name=f"测试{source_api.summary} - {rel.description}",
                api_method=source_api.method,
                api_path=source_api.path,
                host="${host()}",
                headers=self._generate_headers_for_api(source_api),
                request_type=self._get_request_type(source_api),
                data=source_test_data,
                is_run=True,
                detail=f"测试{source_api.summary}，关联关系: {rel.description}",
                dependence_case=False,
                dependence_case_data=None,
                current_request_set_cache={"response": {"source_data": True}},
                sql=None,
                assert_data=source_assert_data,
                setup_sql=None,
                teardown=None,
                teardown_sql=None,
                sleep=None
            )
            
            test_cases.append(source_test_case)
            
            # 生成目标API的测试数据
            target_test_data = self._generate_test_data_for_relationship(rel, target_api, is_source=False)
            
            # 生成目标API的断言数据
            target_assert_data = self._generate_assert_data_for_relationship(rel, target_api, is_source=False)
            
            # 创建目标API的测试用例
            target_case_id = f"rel_{rel.relationship_id}_{rel.target_api.replace('/', '_').replace('{', '_').replace('}', '_')}"
            
            # 生成依赖数据
            dependence_case_data = {
                "case_id": source_case_id,
                "dependent_type": "response",
                "dependent_data": {
                    "source_data": True
                },
                "jsonpath": {
                    **rel.data_mapping
                }
            }
            
            target_test_case = TestCase(
                case_id=target_case_id,
                case_name=f"测试{target_api.summary} - {rel.description}",
                api_method=target_api.method,
                api_path=target_api.path,
                host="${host()}",
                headers=self._generate_headers_for_api(target_api),
                request_type=self._get_request_type(target_api),
                data=target_test_data,
                is_run=True,
                detail=f"测试{target_api.summary}，关联关系: {rel.description}",
                dependence_case=True,
                dependence_case_data=dependence_case_data,
                current_request_set_cache=None,
                sql=None,
                assert_data=target_assert_data,
                setup_sql=None,
                teardown=None,
                teardown_sql=None,
                sleep=None
            )
            
            test_cases.append(target_test_case)
        
        # 创建测试套件
        test_suite = TestSuite(
            suite_id=f"suite_relationship_{rel_type}",
            suite_name=f"{rel_type}关联关系测试",
            description=f"测试{rel_type}类型的API关联关系",
            test_cases=test_cases,
            allure_epic="关联关系测试",
            allure_feature=rel_type,
            allure_story=f"{rel_type}关联关系测试"
        )
        
        self.test_suites.append(test_suite)
    
    def _generate_test_data_for_scenario(self, scenario: TestScenario, api: APIEndpoint, index: int) -> Dict:
        """为场景中的API生成测试数据"""
        # 使用场景中定义的测试数据
        test_data = scenario.test_data.copy()
        
        # 如果场景中没有定义测试数据，则使用默认生成器
        if not test_data:
            if self.test_generator:
                test_data = self.test_generator._generate_test_data_for_api(api)
            else:
                test_data = {}
        
        # 应用场景特定的数据增强
        test_data = self._enhance_test_data_for_scenario(test_data, scenario, api, index)
        
        return test_data
    
    def _generate_test_data_for_relationship(self, relationship: APIRelationship, api: APIEndpoint, is_source: bool) -> Dict:
        """为关联关系中的API生成测试数据"""
        # 使用默认生成器生成基础测试数据
        if self.test_generator:
            test_data = self.test_generator._generate_test_data_for_api(api)
        else:
            test_data = {}
        
        # 应用关联关系特定的数据增强
        test_data = self._enhance_test_data_for_relationship(test_data, relationship, api, is_source)
        
        return test_data
    
    def _enhance_test_data_for_scenario(self, test_data: Dict, scenario: TestScenario, api: APIEndpoint, index: int) -> Dict:
        """为场景中的API增强测试数据"""
        # 根据场景中的前置条件和后置条件调整测试数据
        # 这里可以根据具体需求实现更复杂的逻辑
        
        # 示例：如果是第一个API，确保包含认证信息
        if index == 0 and api.path.startswith('/open-apis/authen'):
            if 'data' not in test_data:
                test_data['data'] = {}
            if 'app_id' not in test_data['data']:
                test_data['data']['app_id'] = 'test_app_id'
            if 'app_secret' not in test_data['data']:
                test_data['data']['app_secret'] = 'test_app_secret'
        
        return test_data
    
    def _enhance_test_data_for_relationship(self, test_data: Dict, relationship: APIRelationship, api: APIEndpoint, is_source: bool) -> Dict:
        """为关联关系中的API增强测试数据"""
        # 如果是目标API，需要使用数据映射
        if not is_source and relationship.data_mapping:
            # 这里可以应用数据映射逻辑
            # 实际实现中，可能需要从源API的响应中提取数据
            pass
        
        return test_data
    
    def _generate_assert_data_for_scenario(self, scenario: TestScenario, api: APIEndpoint, index: int) -> Dict:
        """为场景中的API生成断言数据"""
        # 使用场景中定义的预期结果
        assert_data = scenario.expected_results.copy()
        
        # 如果场景中没有定义预期结果，则使用默认断言
        if not assert_data:
            assert_data = {"status_code": 200}
        
        return assert_data
    
    def _generate_assert_data_for_relationship(self, relationship: APIRelationship, api: APIEndpoint, is_source: bool) -> Dict:
        """为关联关系中的API生成断言数据"""
        # 使用默认断言
        assert_data = {"status_code": 200}
        
        return assert_data
    
    def _find_dependencies_for_api(self, api_endpoint: str, previous_endpoints: List[str]) -> List[str]:
        """查找API的依赖关系"""
        dependencies = []
        
        # 查找与当前API有关联关系的前置API
        for rel in self.relationships:
            if rel.target_api == api_endpoint and rel.source_api in previous_endpoints:
                dependencies.append(rel.source_api)
        
        return dependencies
    
    def _generate_dependence_data(self, dependencies: List[str], scenario: TestScenario = None) -> Optional[Dict]:
        """生成依赖数据"""
        if not dependencies:
            return None
        
        # 这里可以根据具体需求实现更复杂的依赖数据生成逻辑
        # 简化实现，返回基本的依赖信息
        return {
            "dependencies": dependencies,
            "scenario_id": scenario.scenario_id if scenario else None
        }
    
    def _generate_cache_data(self, api: APIEndpoint, scenario: TestScenario = None) -> Optional[Dict]:
        """生成缓存数据"""
        # 这里可以根据具体需求实现更复杂的缓存数据生成逻辑
        # 简化实现，返回基本的缓存信息
        return {
            "cache_response": True,
            "scenario_id": scenario.scenario_id if scenario else None
        }
    
    def _generate_headers_for_api(self, api: APIEndpoint) -> Dict:
        """为API生成请求头"""
        # 使用测试生成器的方法生成请求头
        if self.test_generator:
            return self.test_generator._generate_headers_for_api(api)
        else:
            return {"Content-Type": "application/json"}
    
    def _get_request_type(self, api: APIEndpoint) -> str:
        """获取API的请求类型"""
        # 使用测试生成器的方法获取请求类型
        if self.test_generator:
            return self.test_generator._get_request_type(api)
        else:
            return "JSON"
    
    def save_test_suites(self) -> bool:
        """保存测试套件到文件"""
        try:
            # 创建输出目录
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 保存每个测试套件到单独的文件
            for suite in self.test_suites:
                suite_dir = os.path.join(self.output_dir, suite.suite_id)
                os.makedirs(suite_dir, exist_ok=True)
                
                # 转换测试套件为可序列化的格式
                suite_data = {
                    "suite_id": suite.suite_id,
                    "suite_name": suite.suite_name,
                    "description": suite.description,
                    "allure_epic": suite.allure_epic,
                    "allure_feature": suite.allure_feature,
                    "allure_story": suite.allure_story,
                    "test_cases": []
                }
                
                # 转换测试用例为可序列化的格式
                for case in suite.test_cases:
                    case_data = {
                        "case_id": case.case_id,
                        "case_name": case.case_name,
                        "api_method": case.api_method,
                        "api_path": case.api_path,
                        "host": case.host,
                        "headers": case.headers,
                        "request_type": case.request_type,
                        "data": case.data,
                        "is_run": case.is_run,
                        "detail": case.detail,
                        "dependence_case": case.dependence_case,
                        "dependence_case_data": case.dependence_case_data,
                        "current_request_set_cache": case.current_request_set_cache,
                        "sql": case.sql,
                        "assert_data": case.assert_data,
                        "setup_sql": case.setup_sql,
                        "teardown": case.teardown,
                        "teardown_sql": case.teardown_sql,
                        "sleep": case.sleep
                    }
                    suite_data["test_cases"].append(case_data)
                
                # 保存测试套件到JSON文件
                suite_file = os.path.join(suite_dir, f"{suite.suite_id}.json")
                with open(suite_file, 'w', encoding='utf-8') as f:
                    json.dump(suite_data, f, ensure_ascii=False, indent=2)
                
                # 保存测试套件到YAML文件
                yaml_file = os.path.join(suite_dir, f"{suite.suite_id}.yaml")
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    import yaml
                    yaml.dump(suite_data, f, default_flow_style=False, allow_unicode=True)
            
            INFO.logger.info(f"测试套件保存完成，共保存 {len(self.test_suites)} 个测试套件")
            return True
            
        except Exception as e:
            ERROR.logger.error(f"保存测试套件失败: {str(e)}")
            return False


def create_scenario_from_dict(scenario_dict: Dict) -> TestScenario:
    """从字典创建测试场景"""
    return TestScenario(
        scenario_id=scenario_dict.get('scenario_id', str(uuid.uuid4())),
        scenario_name=scenario_dict.get('scenario_name', ''),
        description=scenario_dict.get('description', ''),
        api_endpoints=scenario_dict.get('api_endpoints', []),
        preconditions=scenario_dict.get('preconditions', []),
        postconditions=scenario_dict.get('postconditions', []),
        test_data=scenario_dict.get('test_data', {}),
        expected_results=scenario_dict.get('expected_results', {}),
        priority=scenario_dict.get('priority', 'medium'),
        tags=scenario_dict.get('tags', []),
        created_at=scenario_dict.get('created_at', datetime.now().isoformat())
    )


def create_relationship_from_dict(relationship_dict: Dict) -> APIRelationship:
    """从字典创建API关联关系"""
    return APIRelationship(
        relationship_id=relationship_dict.get('relationship_id', str(uuid.uuid4())),
        source_api=relationship_dict.get('source_api', ''),
        target_api=relationship_dict.get('target_api', ''),
        relationship_type=relationship_dict.get('relationship_type', ''),
        data_mapping=relationship_dict.get('data_mapping', {}),
        condition=relationship_dict.get('condition'),
        description=relationship_dict.get('description', ''),
        created_at=relationship_dict.get('created_at', datetime.now().isoformat())
    )