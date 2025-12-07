<<<<<<< HEAD
# -*- coding: utf-8 -*-
"""
API依赖关系分析器
用于分析API之间的依赖关系，以便生成更合理的测试用例
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
=======
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2023/07/01 10:00
# @Author : Smart Auto Platform
# @File   : dependency_analyzer.py
# @describe: 接口依赖关系分析模块，用于分析接口间的数据依赖和调用关系
"""

import json
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from utils.logging_tool.log_control import INFO, ERROR
from utils.other_tools.exceptions import DependencyAnalysisError


@dataclass
class APIEndpoint:
    """API端点数据类"""
    path: str
    method: str
    operation_id: str
    parameters: List[Dict]
    request_body: Optional[Dict]
    response_schema: Optional[Dict]
    tags: List[str]
    summary: str


@dataclass
class DataDependency:
    """数据依赖关系数据类"""
    source_api: str  # 源API标识
    target_api: str  # 目标API标识
    dependency_type: str  # 依赖类型: 'response_to_request', 'parameter_to_parameter', etc.
    source_path: str  # 源数据路径 (JSONPath)
    target_path: str  # 目标数据路径 (JSONPath)
    description: str  # 依赖描述
>>>>>>> origin/feature/zht1206


@dataclass
class BusinessFlow:
    """业务流程数据类"""
    flow_id: str
    flow_name: str
<<<<<<< HEAD
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
=======
    apis: List[str]  # API标识列表
    description: str
    critical_path: bool  # 是否为关键路径


class DependencyAnalyzer:
    """接口依赖关系分析器"""
    
    def __init__(self, apis: List[Dict]):
        """
        初始化依赖分析器
        :param apis: API信息列表，由api_parser模块解析得到
        """
        self.apis = apis
        self.api_endpoints = self._create_api_endpoints()
        self.dependency_graph = defaultdict(set)  # 依赖关系图
        self.reverse_dependency_graph = defaultdict(set)  # 反向依赖关系图
        self.data_dependencies = []  # 数据依赖关系列表
        self.business_flows = []  # 业务流程列表
        
    def _create_api_endpoints(self) -> Dict[str, APIEndpoint]:
        """创建API端点对象"""
        endpoints = {}
        for api in self.apis:
            api_id = f"{api['method']}_{api['path']}"
            
            # 提取响应schema
            response_schema = None
            if 'success_response' in api and 'schema' in api['success_response']:
                response_schema = api['success_response']['schema']
                
            # 提取请求体schema
            request_body = None
            if 'request_body' in api and 'schema' in api['request_body']:
                request_body = api['request_body']
                
            endpoint = APIEndpoint(
                path=api['path'],
                method=api['method'],
                operation_id=api.get('operationId', ''),
                parameters=api.get('parameters', []),
                request_body=request_body,
                response_schema=response_schema,
                tags=api.get('tags', []),
                summary=api.get('summary', '')
            )
            
            endpoints[api_id] = endpoint
            
        return endpoints
        
    def analyze_dependencies(self) -> None:
        """分析API间的依赖关系"""
        try:
            INFO.logger.info("开始分析API依赖关系...")
            
            # 1. 分析参数依赖关系
            self._analyze_parameter_dependencies()
            
            # 2. 分析响应与请求的依赖关系
            self._analyze_response_request_dependencies()
            
            # 3. 分析业务流程
            self._analyze_business_flows()
            
            INFO.logger.info(f"依赖关系分析完成，发现 {len(self.data_dependencies)} 个依赖关系")
            
        except Exception as e:
            ERROR.logger.error(f"依赖关系分析失败: {str(e)}")
            raise DependencyAnalysisError(f"依赖关系分析失败: {str(e)}")
            
    def _analyze_parameter_dependencies(self) -> None:
        """分析参数依赖关系"""
        # 分析路径参数和查询参数的依赖关系
        for api_id, endpoint in self.api_endpoints.items():
            for param in endpoint.parameters:
                param_name = param.get('name', '')
                param_in = param.get('in', '')  # path, query, header, cookie
                
                # 检查参数是否引用了其他API的响应
                if param_name.lower() in ['id', 'userid', 'token', 'sessionid']:
                    # 查找可能提供此参数的API
                    potential_sources = self._find_potential_parameter_sources(param_name, param_in)
                    for source_api_id in potential_sources:
                        if source_api_id != api_id:  # 排除自引用
                            dependency = DataDependency(
                                source_api=source_api_id,
                                target_api=api_id,
                                dependency_type="parameter_dependency",
                                source_path=self._extract_path_from_schema(
                                    self.api_endpoints[source_api_id].response_schema, 
                                    param_name
                                ),
                                target_path=f"$.{param_in}.{param_name}",
                                description=f"参数 {param_name} 可能来源于 {source_api_id} 的响应"
                            )
                            self.data_dependencies.append(dependency)
                            self.dependency_graph[source_api_id].add(api_id)
                            self.reverse_dependency_graph[api_id].add(source_api_id)
                            
    def _analyze_response_request_dependencies(self) -> None:
        """分析响应与请求的依赖关系"""
        for api_id, endpoint in self.api_endpoints.items():
            if not endpoint.request_body:
                continue
                
            # 分析请求体中的字段
            request_schema = endpoint.request_body.get('schema', {})
            request_fields = self._extract_fields_from_schema(request_schema)
            
            for field_name in request_fields:
                # 查找可能提供此字段的API
                potential_sources = self._find_potential_field_sources(field_name)
                for source_api_id in potential_sources:
                    if source_api_id != api_id:  # 排除自引用
                        dependency = DataDependency(
                            source_api=source_api_id,
                            target_api=api_id,
                            dependency_type="response_to_request",
                            source_path=self._extract_path_from_schema(
                                self.api_endpoints[source_api_id].response_schema, 
                                field_name
                            ),
                            target_path=f"$.request.body.{field_name}",
                            description=f"请求字段 {field_name} 可能来源于 {source_api_id} 的响应"
                        )
                        self.data_dependencies.append(dependency)
                        self.dependency_graph[source_api_id].add(api_id)
                        self.reverse_dependency_graph[api_id].add(source_api_id)
                        
    def _analyze_business_flows(self) -> None:
        """分析业务流程"""
        # 使用图算法识别关键业务流程
        visited = set()
        
        # 查找起始节点（没有入边的节点）
        start_nodes = [
            api_id for api_id in self.api_endpoints.keys() 
            if not self.reverse_dependency_graph[api_id]
        ]
        
        # 从每个起始节点开始，构建业务流程
        for start_node in start_nodes:
            if start_node in visited:
                continue
                
            flow = self._build_flow_from_start_node(start_node, visited)
            if flow and len(flow.apis) > 1:  # 只保留包含多个API的流程
                self.business_flows.append(flow)
                
        # 如果没有找到明显的起始节点，尝试基于标签分组
        if not self.business_flows:
            self._analyze_flows_by_tags()
            
    def _build_flow_from_start_node(self, start_node: str, visited: Set[str]) -> Optional[BusinessFlow]:
        """从起始节点构建业务流程"""
        # 使用广度优先搜索构建流程
        queue = deque([(start_node, [start_node])])
        visited.add(start_node)
        
        while queue:
            current_node, path = queue.popleft()
            
            # 获取当前节点的所有未访问的下游节点
            next_nodes = [
                node for node in self.dependency_graph[current_node] 
                if node not in visited
            ]
            
            for next_node in next_nodes:
                new_path = path + [next_node]
                visited.add(next_node)
                queue.append((next_node, new_path))
                
        # 构建业务流程对象
        if len(path) > 1:
            start_endpoint = self.api_endpoints[start_node]
            flow_name = f"流程_{start_endpoint.summary}_{start_node}"
            
            return BusinessFlow(
                flow_id=f"flow_{len(self.business_flows) + 1}",
                flow_name=flow_name,
                apis=path,
                description=f"从 {start_node} 开始的业务流程",
                critical_path=self._is_critical_path(path)
            )
            
        return None
        
    def _analyze_flows_by_tags(self) -> None:
        """基于标签分析业务流程"""
        # 按标签分组API
        tag_groups = defaultdict(list)
        for api_id, endpoint in self.api_endpoints.items():
            for tag in endpoint.tags:
                tag_groups[tag].append(api_id)
                
        # 为每个标签组创建业务流程
        for tag, api_ids in tag_groups.items():
            if len(api_ids) > 1:
                flow = BusinessFlow(
                    flow_id=f"flow_{len(self.business_flows) + 1}",
                    flow_name=f"标签流程_{tag}",
                    apis=api_ids,
                    description=f"基于标签 '{tag}' 的API流程",
                    critical_path=False
                )
                self.business_flows.append(flow)
                
    def _find_potential_parameter_sources(self, param_name: str, param_in: str) -> List[str]:
        """查找可能提供指定参数的API"""
        potential_sources = []
        
        for api_id, endpoint in self.api_endpoints.items():
            if not endpoint.response_schema:
                continue
                
            # 检查响应schema中是否包含参数名
            if self._schema_contains_field(endpoint.response_schema, param_name):
                potential_sources.append(api_id)
                
        return potential_sources
        
    def _find_potential_field_sources(self, field_name: str) -> List[str]:
        """查找可能提供指定字段的API"""
        potential_sources = []
        
        for api_id, endpoint in self.api_endpoints.items():
            if not endpoint.response_schema:
                continue
                
            # 检查响应schema中是否包含字段名
            if self._schema_contains_field(endpoint.response_schema, field_name):
                potential_sources.append(api_id)
                
        return potential_sources
        
    def _schema_contains_field(self, schema: Dict, field_name: str) -> bool:
        """检查schema中是否包含指定字段"""
        if not schema:
            return False
            
        # 简单的字段名匹配
        if 'properties' in schema:
            properties = schema['properties']
            if field_name in properties:
                return True
                
        # 递归检查嵌套对象
        if 'properties' in schema:
            for prop_name, prop_schema in schema['properties'].items():
                if self._schema_contains_field(prop_schema, field_name):
                    return True
                    
        # 检查数组元素
        if schema.get('type') == 'array' and 'items' in schema:
            return self._schema_contains_field(schema['items'], field_name)
            
        return False
        
    def _extract_fields_from_schema(self, schema: Dict) -> List[str]:
        """从schema中提取所有字段名"""
        fields = []
        
        if not schema:
            return fields
            
        # 提取对象的属性
        if 'properties' in schema:
            properties = schema['properties']
            fields.extend(properties.keys())
            
            # 递归提取嵌套对象的字段
            for prop_name, prop_schema in properties.items():
                nested_fields = self._extract_fields_from_schema(prop_schema)
                fields.extend([f"{prop_name}.{field}" for field in nested_fields])
                
        # 提取数组元素的字段
        if schema.get('type') == 'array' and 'items' in schema:
            nested_fields = self._extract_fields_from_schema(schema['items'])
            fields.extend([f"[].{field}" for field in nested_fields])
            
        return fields
        
    def _extract_path_from_schema(self, schema: Dict, field_name: str) -> str:
        """从schema中提取字段的路径"""
        if not schema:
            return f"$.{field_name}"
            
        # 简单实现，实际可能需要更复杂的逻辑
        if 'properties' in schema and field_name in schema['properties']:
            return f"$.{field_name}"
            
        # 递归查找
        if 'properties' in schema:
            for prop_name, prop_schema in schema['properties'].items():
                nested_path = self._extract_path_from_schema(prop_schema, field_name)
                if nested_path != f"$.{field_name}":
                    return f"$.{prop_name}.{nested_path[2:]}"  # 去掉$.
                    
        return f"$.{field_name}"
        
    def _is_critical_path(self, path: List[str]) -> bool:
        """判断是否为关键路径"""
        # 简单实现：如果路径中有认证相关的API，则认为是关键路径
        for api_id in path:
            endpoint = self.api_endpoints[api_id]
            if any(keyword in endpoint.summary.lower() for keyword in ['login', 'auth', 'token']):
                return True
        return False
        
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """获取依赖关系图"""
        return dict(self.dependency_graph)
        
    def get_data_dependencies(self) -> List[DataDependency]:
        """获取数据依赖关系列表"""
        return self.data_dependencies
        
    def get_business_flows(self) -> List[BusinessFlow]:
        """获取业务流程列表"""
        return self.business_flows
        
    def get_api_dependencies(self, api_id: str) -> List[str]:
        """获取指定API的依赖API列表"""
        return list(self.dependency_graph[api_id])
        
    def get_api_dependents(self, api_id: str) -> List[str]:
        """获取依赖指定API的API列表"""
        return list(self.reverse_dependency_graph[api_id])
        
    def export_dependency_graph(self, file_path: str) -> None:
        """导出依赖关系到文件"""
        try:
            graph_data = {
                'nodes': [
                    {
                        'id': api_id,
                        'method': self.api_endpoints[api_id].method,
                        'path': self.api_endpoints[api_id].path,
                        'summary': self.api_endpoints[api_id].summary
                    }
                    for api_id in self.api_endpoints.keys()
                ],
                'edges': [
                    {
                        'source': source,
                        'target': target,
                        'type': next(
                            (dep.dependency_type for dep in self.data_dependencies 
                             if dep.source_api == source and dep.target_api == target),
                            'unknown'
                        )
                    }
                    for source, targets in self.dependency_graph.items()
                    for target in targets
                ],
                'data_dependencies': [
                    {
                        'source_api': dep.source_api,
                        'target_api': dep.target_api,
                        'dependency_type': dep.dependency_type,
                        'source_path': dep.source_path,
                        'target_path': dep.target_path,
                        'description': dep.description
                    }
                    for dep in self.data_dependencies
                ],
                'business_flows': [
                    {
                        'flow_id': flow.flow_id,
                        'flow_name': flow.flow_name,
                        'apis': flow.apis,
                        'description': flow.description,
                        'critical_path': flow.critical_path
                    }
                    for flow in self.business_flows
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
                
            INFO.logger.info(f"依赖关系已导出到: {file_path}")
            
        except Exception as e:
            ERROR.logger.error(f"导出依赖关系失败: {str(e)}")
            raise DependencyAnalysisError(f"导出依赖关系失败: {str(e)}")


def analyze_api_dependencies(apis: List[Dict]) -> DependencyAnalyzer:
    """
    分析API依赖关系
    :param apis: API信息列表
    :return: 依赖分析器对象
    """
    analyzer = DependencyAnalyzer(apis)
    analyzer.analyze_dependencies()
    return analyzer


if __name__ == '__main__':
    # 示例用法
    try:
        # 假设已经通过api_parser解析了API文档
        from utils.smart_auto.api_parser import parse_api_document
        
        # 解析API文档
        apis = parse_api_document('path/to/swagger.yaml')
        
        # 分析依赖关系
        analyzer = analyze_api_dependencies(apis)
        
        # 获取业务流程
        flows = analyzer.get_business_flows()
        print(f"发现 {len(flows)} 个业务流程")
        
        # 导出依赖关系
        analyzer.export_dependency_graph('dependency_graph.json')
        
    except Exception as e:
        print(f"分析API依赖关系失败: {str(e)}")
>>>>>>> origin/feature/zht1206
