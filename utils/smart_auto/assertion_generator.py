#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2025/12/03 10:00
# @Author : Smart Auto Platform
# @File   : assertion_generator.py
# @describe: 结果校验逻辑生成模块，根据API响应和业务规则自动生成断言
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from utils.logging_tool.log_control import INFO, ERROR, WARNING
from utils.other_tools.exceptions import AssertionGenerationError


class AssertionType(Enum):
    """断言类型枚举"""
    EQUALS = "equals"  # 等于
    NOT_EQUALS = "not_equals"  # 不等于
    CONTAINS = "contains"  # 包含
    NOT_CONTAINS = "not_contains"  # 不包含
    GREATER_THAN = "greater_than"  # 大于
    LESS_THAN = "less_than"  # 小于
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"  # 大于等于
    LESS_THAN_OR_EQUAL = "less_than_or_equal"  # 小于等于
    IN = "in"  # 在列表中
    NOT_IN = "not_in"  # 不在列表中
    IS_NULL = "is_null"  # 为空
    IS_NOT_NULL = "is_not_null"  # 不为空
    REGEX = "regex"  # 正则匹配
    TYPE_CHECK = "type_check"  # 类型检查
    LENGTH_CHECK = "length_check"  # 长度检查


@dataclass
class AssertionRule:
    """断言规则"""
    path: str  # JSONPath表达式
    type: AssertionType  # 断言类型
    expected_value: Any = None  # 期望值
    description: str = ""  # 断言描述
    priority: int = 1  # 优先级，1-5，1最高


@dataclass
class Assertion:
    """断言数据"""
    jsonpath: str  # JSONPath表达式
    type: str  # 断言类型
    value: Any  # 期望值
    AssertType: Optional[str] = None  # 断言类型（兼容旧格式）
    description: Optional[str] = None  # 断言描述


class AssertionGenerator:
    """断言生成器"""
    
    def __init__(self):
        """初始化断言生成器"""
        self.common_assertions = self._init_common_assertions()
        self.type_assertions = self._init_type_assertions()
        
    def _init_common_assertions(self) -> Dict[str, List[AssertionRule]]:
        """初始化通用断言规则"""
        return {
            "status": [
                AssertionRule("$.code", AssertionType.EQUALS, 0, "检查响应状态码是否为0"),
                AssertionRule("$.status", AssertionType.EQUALS, "success", "检查响应状态是否为success"),
                AssertionRule("$.success", AssertionType.EQUALS, True, "检查响应成功标志是否为True"),
            ],
            "message": [
                AssertionRule("$.message", AssertionType.NOT_EQUALS, None, "检查响应消息不为空"),
                AssertionRule("$.msg", AssertionType.NOT_EQUALS, None, "检查响应消息不为空"),
            ],
            "data": [
                AssertionRule("$.data", AssertionType.IS_NOT_NULL, None, "检查响应数据不为空"),
            ]
        }
        
    def _init_type_assertions(self) -> Dict[str, AssertionType]:
        """初始化类型断言规则"""
        return {
            "string": AssertionType.TYPE_CHECK,
            "integer": AssertionType.TYPE_CHECK,
            "number": AssertionType.TYPE_CHECK,
            "boolean": AssertionType.TYPE_CHECK,
            "array": AssertionType.TYPE_CHECK,
            "object": AssertionType.TYPE_CHECK,
        }
        
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
            
            # 2. 生成通用业务断言
            business_assertions = self._generate_business_assertions(api_info)
            assertions.extend(business_assertions)
            
            # 3. 生成响应结构断言
            if response_schema:
                structure_assertions = self._generate_structure_assertions(response_schema)
                assertions.extend(structure_assertions)
                
            # 4. 生成数据类型断言
            if response_schema:
                type_assertions = self._generate_type_assertions(response_schema)
                assertions.extend(type_assertions)
                
            # 5. 生成业务规则断言
            business_rule_assertions = self._generate_business_rule_assertions(api_info)
            assertions.extend(business_rule_assertions)
            
            INFO.logger.info(f"为API {api_info.get('path', '')} 生成了 {len(assertions)} 个断言")
            return assertions
            
        except Exception as e:
            ERROR.logger.error(f"生成断言失败: {str(e)}")
            raise AssertionGenerationError(f"生成断言失败: {str(e)}")
            
    def _generate_status_assertions(self, api_info: Dict) -> List[Assertion]:
        """生成状态码断言"""
        assertions = []
        
        # 从API文档中获取成功状态码
        response_codes = api_info.get('response_codes', [])
        success_code = 200  # 默认成功状态码
        
        if '200' in response_codes:
            success_code = 200
        elif '201' in response_codes:
            success_code = 201
        elif '204' in response_codes:
            success_code = 204
        elif response_codes:
            # 取第一个状态码作为成功状态码
            try:
                success_code = int(response_codes[0])
            except (ValueError, IndexError):
                pass
                
        # 添加状态码断言
        assertions.append(Assertion(
            jsonpath="status_code",
            type="equals",
            value=success_code,
            AssertType="status_code",
            description=f"检查HTTP状态码是否为{success_code}"
        ))
        
        return assertions
        
    def _generate_business_assertions(self, api_info: Dict) -> List[Assertion]:
        """生成通用业务断言"""
        assertions = []
        
        # 遍历通用断言规则
        for field, rules in self.common_assertions.items():
            for rule in rules:
                # 检查API信息中是否包含相关字段
                if self._should_apply_rule(rule, api_info):
                    assertion = self._convert_rule_to_assertion(rule)
                    assertions.append(assertion)
                    
        return assertions
        
    def _generate_structure_assertions(self, response_schema: Dict, prefix: str = "$") -> List[Assertion]:
        """生成响应结构断言"""
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
                    description=f"检查响应中是否包含{prop_name}字段"
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