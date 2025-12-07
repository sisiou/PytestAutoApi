# -*- coding: utf-8 -*-
"""
API依赖关系分析器
用于分析API之间的依赖关系，以便生成更合理的测试用例
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class BusinessFlow:
    """业务流程数据类"""
    flow_id: str
    flow_name: str
    description: str
    apis: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]


@dataclass
class DataDependency:
    """数据依赖关系数据类"""
    source_api: str
    target_api: str
    data_field: str
    dependency_type: str


class DependencyAnalyzer:
    """API依赖关系分析器"""
    
    def __init__(self, apis: List[Dict[str, Any]]):
        """
        初始化依赖关系分析器
        :param apis: API列表
        """
        self.apis = apis
        self.dependencies = []
        self.business_flows = []
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """
        分析API依赖关系
        :return: 依赖关系分析结果
        """
        # 简单实现：基于API路径和参数推断依赖关系
        for api in self.apis:
            path = api.get('path', '')
            method = api.get('method', '').upper()
            
            # 简单规则：如果API路径包含ID参数，可能依赖于创建API
            if '{id}' in path and method in ['GET', 'PUT', 'DELETE']:
                # 查找可能的创建API
                create_path = path.split('{id}')[0]
                for other_api in self.apis:
                    other_path = other_api.get('path', '')
                    other_method = other_api.get('method', '').upper()
                    
                    if other_path == create_path and other_method == 'POST':
                        dependency = {
                            'source_api': f"{other_method}_{other_path}",
                            'target_api': f"{method}_{path}",
                            'data_field': 'id',
                            'dependency_type': 'resource_id'
                        }
                        self.dependencies.append(dependency)
        
        return {
            'dependencies': self.dependencies,
            'business_flows': self.business_flows
        }


def analyze_api_dependencies(apis: List[Dict[str, Any]]) -> DependencyAnalyzer:
    """
    分析API依赖关系的便捷函数
    :param apis: API列表
    :return: 依赖关系分析器实例
    """
    analyzer = DependencyAnalyzer(apis)
    analyzer.analyze_dependencies()
    return analyzer