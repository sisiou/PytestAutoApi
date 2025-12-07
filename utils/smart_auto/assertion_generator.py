#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time   : 2023/10/15 10:00
@Author : 智能测试助手
@File   : assertion_generator.py
@Desc   : 结果校验逻辑生成模块
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from flask import Flask, request, jsonify

from utils.logging_tool.log_control import INFO, ERROR, WARNING


class AssertionType(Enum):
    """断言类型枚举"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    TYPE_CHECK = "type_check"
    REGEX_MATCH = "regex_match"


@dataclass
class AssertionRule:
    """断言规则"""
    path: str  # JSONPath表达式
    type: AssertionType  # 断言类型
    expected_value: Any  # 期望值
    description: str  # 断言描述


@dataclass
class Assertion:
    """断言对象"""
    jsonpath: str  # JSONPath表达式
    type: str  # 断言类型
    value: Any  # 期望值
    AssertType: str  # 断言分类
    description: str  # 断言描述


class AssertionGenerator:
    """断言生成器"""
    
    def __init__(self):
        """初始化断言生成器"""
        self.common_assertions = self._init_common_assertions()
        self.type_assertions = self._init_type_assertions()
        
    def _init_common_assertions(self) -> List[AssertionRule]:
        """初始化通用断言规则"""
        return [
            # 状态码断言
            AssertionRule(
                path="$.code",
                type=AssertionType.EQUALS,
                expected_value=0,
                description="检查响应状态码是否为0(成功)"
            ),
            AssertionRule(
                path="$.code",
                type=AssertionType.EQUALS,
                expected_value=200,
                description="检查HTTP状态码是否为200"
            ),
            # 消息断言
            AssertionRule(
                path="$.message",
                type=AssertionType.IS_NOT_NULL,
                expected_value=None,
                description="检查响应消息不为空"
            ),
            # 数据断言
            AssertionRule(
                path="$.data",
                type=AssertionType.IS_NOT_NULL,
                expected_value=None,
                description="检查响应数据不为空"
            )
        ]
    
    def _init_type_assertions(self) -> List[AssertionRule]:
        """初始化类型断言规则"""
        return [
            # 基础类型断言
            AssertionRule(
                path="$.code",
                type=AssertionType.TYPE_CHECK,
                expected_value="integer",
                description="检查状态码为整数类型"
            ),
            AssertionRule(
                path="$.message",
                type=AssertionType.TYPE_CHECK,
                expected_value="string",
                description="检查消息为字符串类型"
            )
        ]
    
    def generate_assertions(self, api_info: Dict, response_schema: Dict = None) -> List[Assertion]:
        """
        生成断言
        :param api_info: API信息
        :param response_schema: 响应模式
        :return: 断言列表
        """
        try:
            assertions = []
            
            # 1. 生成状态码断言
            status_assertions = self._generate_status_assertions(api_info)
            assertions.extend(status_assertions)
            
            # 2. 生成业务断言
            business_assertions = self._generate_business_assertions(api_info)
            assertions.extend(business_assertions)
            
            # 3. 如果有响应模式，生成结构断言
            if response_schema:
                structure_assertions = self._generate_structure_assertions(response_schema)
                assertions.extend(structure_assertions)
                
                # 4. 生成类型断言
                type_assertions = self._generate_type_assertions(response_schema)
                assertions.extend(type_assertions)
            
            # 5. 生成业务规则断言
            business_rule_assertions = self._generate_business_rule_assertions(api_info)
            assertions.extend(business_rule_assertions)
            
            INFO.logger.info(f"为API {api_info.get('path', '')} 生成了 {len(assertions)} 个断言")
            return assertions
            
        except Exception as e:
            ERROR.logger.error(f"生成断言失败: {str(e)}")
            return []
    
    def _generate_status_assertions(self, api_info: Dict) -> List[Assertion]:
        """生成状态码断言"""
        assertions = []
        
        # 获取可能的响应码
        response_codes = api_info.get('response_codes', ['200', '201', '204'])
        
        # 默认检查200状态码
        assertions.append(Assertion(
            jsonpath="$.code",
            type="equals",
            value=0,
            AssertType="status",
            description="检查响应状态码是否为0(成功)"
        ))
        
        # 如果API可能返回其他状态码，也添加相应的断言
        if '201' in response_codes:
            assertions.append(Assertion(
                jsonpath="$.code",
                type="equals",
                value=201,
                AssertType="status",
                description="检查响应状态码是否为201(创建成功)"
            ))
            
        if '204' in response_codes:
            assertions.append(Assertion(
                jsonpath="$.code",
                type="equals",
                value=204,
                AssertType="status",
                description="检查响应状态码是否为204(无内容)"
            ))
        
        return assertions
    
    def _generate_business_assertions(self, api_info: Dict) -> List[Assertion]:
        """生成业务断言"""
        assertions = []
        
        # 应用通用断言规则
        for rule in self.common_assertions:
            if self._should_apply_rule(rule, api_info):
                assertion = self._convert_rule_to_assertion(rule)
                assertions.append(assertion)
        
        return assertions
    
    def _generate_structure_assertions(self, response_schema: Dict, prefix: str = "$") -> List[Assertion]:
        """生成结构断言"""
        assertions = []
        
        if not response_schema:
            return assertions
            
        # 处理对象类型
        if response_schema.get('type') == 'object' and 'properties' in response_schema:
            properties = response_schema['properties']
            
            for prop_name, prop_schema in properties.items():
                path = f"{prefix}.{prop_name}"
                
                # 检查字段是否存在
                assertions.append(Assertion(
                    jsonpath=path,
                    type="is_not_null",
                    value=None,
                    AssertType="structure",
                    description=f"检查{prop_name}字段是否存在"
                ))
                
                # 递归处理嵌套对象
                if prop_schema.get('type') == 'object':
                    nested_assertions = self._generate_structure_assertions(prop_schema, path)
                    assertions.extend(nested_assertions)
                    
                # 处理数组类型
                elif prop_schema.get('type') == 'array':
                    items_schema = prop_schema.get('items', {})
                    array_path = f"{path}[0]"  # 检查第一个元素
                    
                    # 如果数组不为空，检查数组元素结构
                    assertions.append(Assertion(
                        jsonpath=array_path,
                        type="is_not_null",
                        value=None,
                        AssertType="structure",
                        description=f"检查{prop_name}数组元素结构"
                    ))
                    
                    # 递归处理数组元素
                    if items_schema.get('type') == 'object':
                        nested_assertions = self._generate_structure_assertions(items_schema, array_path)
                        assertions.extend(nested_assertions)
                        
        return assertions
        
    def _generate_type_assertions(self, response_schema: Dict, prefix: str = "$") -> List[Assertion]:
        """生成数据类型断言"""
        assertions = []
        
        if not response_schema:
            return assertions
            
        # 处理对象类型
        if response_schema.get('type') == 'object' and 'properties' in response_schema:
            properties = response_schema['properties']
            
            for prop_name, prop_schema in properties.items():
                path = f"{prefix}.{prop_name}"
                prop_type = prop_schema.get('type', 'string')
                
                # 添加类型断言
                assertions.append(Assertion(
                    jsonpath=path,
                    type="type_check",
                    value=prop_type,
                    AssertType="type",
                    description=f"检查{prop_name}字段类型是否为{prop_type}"
                ))
                
                # 递归处理嵌套对象
                if prop_schema.get('type') == 'object':
                    nested_assertions = self._generate_type_assertions(prop_schema, path)
                    assertions.extend(nested_assertions)
                    
                # 处理数组类型
                elif prop_schema.get('type') == 'array':
                    items_schema = prop_schema.get('items', {})
                    array_path = f"{path}[0]"  # 检查第一个元素
                    
                    # 添加数组类型断言
                    assertions.append(Assertion(
                        jsonpath=path,
                        type="type_check",
                        value="array",
                        AssertType="type",
                        description=f"检查{prop_name}字段类型是否为array"
                    ))
                    
                    # 递归处理数组元素
                    if items_schema.get('type') == 'object':
                        nested_assertions = self._generate_type_assertions(items_schema, array_path)
                        assertions.extend(nested_assertions)
                        
        return assertions
        
    def _generate_business_rule_assertions(self, api_info: Dict) -> List[Assertion]:
        """生成业务规则断言"""
        assertions = []
        
        # 根据API路径和方法生成特定业务规则断言
        path = api_info.get('path', '')
        method = api_info.get('method', '').upper()
        
        # 登录API断言
        if 'login' in path.lower() and method == 'POST':
            assertions.append(Assertion(
                jsonpath="$.data.token",
                type="is_not_null",
                value=None,
                AssertType="business",
                description="检查登录响应是否包含token"
            ))
            
            assertions.append(Assertion(
                jsonpath="$.data.user_id",
                type="is_not_null",
                value=None,
                AssertType="business",
                description="检查登录响应是否包含用户ID"
            ))
            
        # 用户信息API断言
        elif 'user' in path.lower() and method == 'GET':
            assertions.append(Assertion(
                jsonpath="$.data.id",
                type="is_not_null",
                value=None,
                AssertType="business",
                description="检查用户信息是否包含ID"
            ))
            
            assertions.append(Assertion(
                jsonpath="$.data.username",
                type="is_not_null",
                value=None,
                AssertType="business",
                description="检查用户信息是否包含用户名"
            ))
            
        # 创建资源API断言
        elif method == 'POST':
            assertions.append(Assertion(
                jsonpath="$.data.id",
                type="is_not_null",
                value=None,
                AssertType="business",
                description="检查创建资源是否返回ID"
            ))
            
        # 更新资源API断言
        elif method == 'PUT' or method == 'PATCH':
            assertions.append(Assertion(
                jsonpath="$.data.updated_at",
                type="is_not_null",
                value=None,
                AssertType="business",
                description="检查更新资源是否返回更新时间"
            ))
            
        # 删除资源API断言
        elif method == 'DELETE':
            assertions.append(Assertion(
                jsonpath="$.message",
                type="contains",
                value="success",
                AssertType="business",
                description="检查删除操作是否成功"
            ))
            
        return assertions
        
    def _should_apply_rule(self, rule: AssertionRule, api_info: Dict) -> bool:
        """判断是否应该应用断言规则"""
        # 简化实现，默认应用所有规则
        # 实际实现中可以根据API信息、业务场景等判断是否应用特定规则
        return True
        
    def _convert_rule_to_assertion(self, rule: AssertionRule) -> Assertion:
        """将断言规则转换为断言对象"""
        return Assertion(
            jsonpath=rule.path,
            type=rule.type.value,
            value=rule.expected_value,
            AssertType=rule.type.value,
            description=rule.description
        )
        
    def generate_custom_assertions(self, custom_rules: List[Dict]) -> List[Assertion]:
        """
        生成自定义断言
        :param custom_rules: 自定义规则列表
        :return: 断言列表
        """
        assertions = []
        
        for rule in custom_rules:
            try:
                path = rule.get('path', '')
                type_str = rule.get('type', 'equals')
                value = rule.get('value', None)
                description = rule.get('description', '')
                
                # 转换断言类型
                try:
                    assertion_type = AssertionType(type_str)
                except ValueError:
                    WARNING.logger.warning(f"未知的断言类型: {type_str}，使用默认类型equals")
                    assertion_type = AssertionType.EQUALS
                    
                # 创建断言
                assertion = Assertion(
                    jsonpath=path,
                    type=assertion_type.value,
                    value=value,
                    AssertType=assertion_type.value,
                    description=description
                )
                
                assertions.append(assertion)
                
            except Exception as e:
                ERROR.logger.error(f"生成自定义断言失败: {str(e)}")
                
        return assertions
        
    def optimize_assertions(self, assertions: List[Assertion]) -> List[Assertion]:
        """
        优化断言列表
        :param assertions: 原始断言列表
        :return: 优化后的断言列表
        """
        # 去重
        unique_assertions = []
        seen_paths = set()
        
        for assertion in assertions:
            # 创建唯一标识
            unique_key = f"{assertion.jsonpath}_{assertion.type}_{assertion.value}"
            
            if unique_key not in seen_paths:
                unique_assertions.append(assertion)
                seen_paths.add(unique_key)
                
        # 按优先级排序
        # 这里简化处理，实际可以根据断言类型、重要性等排序
        
        return unique_assertions


def generate_assertions_for_api(api_info: Dict, response_schema: Dict = None) -> Dict[str, Any]:
    """
    为API生成断言
    :param api_info: API信息
    :param response_schema: 响应模式
    :return: 断言字典
    """
    generator = AssertionGenerator()
    assertions = generator.generate_assertions(api_info, response_schema)
    assertions = generator.optimize_assertions(assertions)
    
    # 转换为断言字典
    assert_dict = {}
    
    for assertion in assertions:
        assert_key = assertion.jsonpath
        assert_dict[assert_key] = {
            'jsonpath': assertion.jsonpath,
            'type': assertion.type,
            'value': assertion.value,
            'AssertType': assertion.AssertType,
            'description': assertion.description
        }
        
    return assert_dict


if __name__ == '__main__':
    # 示例用法
    try:
        # API信息
        api_info = {
            'path': '/api/login',
            'method': 'POST',
            'response_codes': ['200', '400', '401']
        }
        
        # 响应模式
        response_schema = {
            'type': 'object',
            'properties': {
                'code': {'type': 'integer'},
                'message': {'type': 'string'},
                'data': {
                    'type': 'object',
                    'properties': {
                        'token': {'type': 'string'},
                        'user_id': {'type': 'integer'},
                        'username': {'type': 'string'}
                    }
                }
            }
        }
        
        # 生成断言
        assertions = generate_assertions_for_api(api_info, response_schema)
        print(f"生成了 {len(assertions)} 个断言:")
        for key, value in assertions.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"生成断言失败: {str(e)}")