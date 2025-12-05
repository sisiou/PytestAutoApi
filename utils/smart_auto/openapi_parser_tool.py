"""
OpenAPI 3.0.0 API文档解析功能模块
基于LangChain工具实现，用于解析OpenAPI 3.0.0文档并提取API信息
"""

import json
import yaml
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import requests
from urllib.parse import urljoin, urlparse
from .api_parser import OpenAPIParser, APIEndpoint


@dataclass
class ParsedAPIInfo:
    """解析后的API信息"""
    title: str
    version: str
    description: str
    base_url: str
    endpoints: List[APIEndpoint]
    schemas: Dict[str, Any]
    security_schemes: Dict[str, Any]
    openapi_version: str = "3.0.0"


class OpenAPIInput(BaseModel):
    """OpenAPI解析工具输入模型"""
    openapi_source: str = Field(description="OpenAPI 3.0.0文档来源，可以是URL、文件路径或JSON/YAML字符串")
    source_type: str = Field(description="来源类型：url、file或content")


class OpenAPIParseTool(BaseTool):
    """OpenAPI 3.0.0文档解析工具"""
    name = "openapi_parse_tool"
    description = "解析OpenAPI 3.0.0文档，提取API接口信息"
    args_schema: type[BaseModel] = OpenAPIInput
    
    def _run(self, openapi_source: str, source_type: str) -> Dict[str, Any]:
        """执行OpenAPI 3.0.0文档解析"""
        try:
            # 根据来源类型获取OpenAPI文档内容
            if source_type == "url":
                openapi_content = self._fetch_from_url(openapi_source)
            elif source_type == "file":
                openapi_content = self._load_from_file(openapi_source)
            elif source_type == "content":
                openapi_content = openapi_source
            else:
                return {"error": f"不支持的来源类型: {source_type}"}
            
            # 解析OpenAPI内容
            # 注意：这里我们不需要创建解析器实例，因为我们会直接解析内容
            if source_type == "file" and (openapi_source.endswith('.yaml') or openapi_source.endswith('.yml')):
                openapi_dict = yaml.safe_load(openapi_content)
            elif source_type == "content":
                if isinstance(openapi_content, str):
                    if "yaml" in openapi_content[:50].lower():
                        openapi_dict = yaml.safe_load(openapi_content)
                    else:
                        openapi_dict = json.loads(openapi_content)
                else:
                    # 如果已经是字典，直接使用
                    openapi_dict = openapi_content
            else:
                openapi_dict = json.loads(openapi_content)
            
            # 验证OpenAPI版本
            openapi_version = openapi_dict.get("openapi", "")
            swagger_version = openapi_dict.get("swagger", "")
            
            # 支持OpenAPI 3.0.x和Swagger 2.0
            if openapi_version and not openapi_version.startswith("3.0."):
                return {"error": f"不支持的OpenAPI版本: {openapi_version}，仅支持3.0.x版本"}
            elif swagger_version and not swagger_version.startswith("2.0"):
                return {"error": f"不支持的Swagger版本: {swagger_version}，仅支持2.0版本"}
            elif not openapi_version and not swagger_version:
                return {"error": "无法确定API文档版本，仅支持OpenAPI 3.0.x和Swagger 2.0"}
            
            # 统一使用openapi_version变量，对于Swagger 2.0设置为"2.0"
            if swagger_version:
                openapi_version = swagger_version
            
            # 提取基本信息
            info = openapi_dict.get("info", {})
            title = info.get("title", "未知API")
            version = info.get("version", "1.0.0")
            description = info.get("description", "")
            
            # 提取服务器信息
            if openapi_version.startswith("3.0."):
                # OpenAPI 3.0.x
                servers = openapi_dict.get("servers", [])
                base_url = servers[0].get("url", "") if servers else ""
                # 提取模式定义
                schemas = openapi_dict.get("components", {}).get("schemas", {})
                # 提取安全方案
                security_schemes = openapi_dict.get("components", {}).get("securitySchemes", {})
            else:
                # Swagger 2.0
                host = openapi_dict.get("host", "")
                base_path = openapi_dict.get("basePath", "")
                schemes = openapi_dict.get("schemes", ["https"])
                base_url = f"{schemes[0] if schemes else 'https'}://{host}{base_path}" if host else ""
                # 提取模式定义
                schemas = openapi_dict.get("definitions", {})
                # 提取安全方案
                security_schemes = openapi_dict.get("securityDefinitions", {})
            
            # 提取路径信息
            paths = openapi_dict.get("paths", {})
            endpoints = []
            
            for path, path_item in paths.items():
                for method, operation in path_item.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        endpoint = self._extract_endpoint_info(path, method, operation, openapi_dict)
                        endpoints.append(endpoint)
            
            # 构建解析结果
            parsed_info = ParsedAPIInfo(
                title=title,
                version=version,
                description=description,
                base_url=base_url,
                endpoints=endpoints,
                schemas=schemas,
                security_schemes=security_schemes,
                openapi_version=openapi_version
            )
            
            # 转换为字典返回
            return {
                "title": parsed_info.title,
                "version": parsed_info.version,
                "description": parsed_info.description,
                "base_url": parsed_info.base_url,
                "openapi_version": parsed_info.openapi_version,
                "endpoints": [
                    {
                        "path": ep.path,
                        "method": ep.method,
                        "summary": ep.summary,
                        "description": ep.description,
                        "operation_id": ep.operation_id,
                        "tags": ep.tags,
                        "parameters": ep.parameters,
                        "request_body": ep.request_body,
                        "response_codes": ep.response_codes,
                        "success_response": ep.success_response,
                        "security": ep.security
                    } for ep in parsed_info.endpoints
                ],
                "schemas": parsed_info.schemas,
                "security_schemes": parsed_info.security_schemes
            }
            
        except Exception as e:
            return {"error": f"解析OpenAPI 3.0.0文档失败: {str(e)}"}
    
    def _fetch_from_url(self, url: str) -> str:
        """从URL获取OpenAPI文档"""
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    
    def _load_from_file(self, file_path: str) -> str:
        """从文件加载OpenAPI文档"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_endpoint_info(self, path: str, method: str, operation: Dict, openapi_dict: Dict) -> APIEndpoint:
        """提取单个API端点信息"""
        summary = operation.get("summary", "")
        description = operation.get("description", "")
        tags = operation.get("tags", [])
        operation_id = operation.get("operationId", "")
        
        # 检查OpenAPI版本
        openapi_version = openapi_dict.get("openapi", "")
        swagger_version = openapi_dict.get("swagger", "")
        is_swagger2 = bool(swagger_version)
        
        # 提取参数
        parameters = []
        request_body = {}
        
        if is_swagger2:
            # Swagger 2.0处理
            for param in operation.get("parameters", []):
                param_in = param.get("in", "")
                param_obj = {
                    "name": param.get("name"),
                    "in": param_in,
                    "description": param.get("description", ""),
                    "required": param.get("required", False),
                    "type": param.get("type", ""),
                    "schema": param.get("schema", {})
                }
                
                if param_in == "body":
                    # 在Swagger 2.0中，body参数相当于OpenAPI 3.0的requestBody
                    schema = param.get("schema", {})
                    request_body = {
                        "description": param.get("description", ""),
                        "content_types": ["application/json"],
                        "required": param.get("required", False),
                        "schema": schema
                    }
                else:
                    # 其他类型的参数
                    parameters.append(param_obj)
        else:
            # OpenAPI 3.0.x处理
            for param in operation.get("parameters", []):
                param_obj = {
                    "name": param.get("name"),
                    "in": param.get("in"),
                    "description": param.get("description", ""),
                    "required": param.get("required", False),
                    "type": param.get("schema", {}).get("type", ""),
                    "schema": param.get("schema", {})
                }
                parameters.append(param_obj)
            
            # 提取请求体
            request_body_dict = operation.get("requestBody", {})
            if request_body_dict:
                content = request_body_dict.get("content", {})
                content_types = list(content.keys())
                request_body = {
                    "description": request_body_dict.get("description", ""),
                    "content_types": content_types,
                    "required": request_body_dict.get("required", False)
                }
                if content_types:
                    request_body["schema"] = content[content_types[0]].get("schema", {})
        
        # 提取响应
        responses = operation.get("responses", {})
        response_codes = list(responses.keys())
        success_response = {}
        
        # 尝试找到成功的响应（2xx）
        for code in response_codes:
            if code.startswith("2"):
                success_response = responses[code]
                break
        
        # 提取安全要求
        security = operation.get("security", [])
        
        return APIEndpoint(
            path=path,
            method=method.upper(),
            summary=summary,
            description=description,
            operation_id=operation_id,
            tags=tags,
            parameters=parameters,
            request_body=request_body,
            response_codes=response_codes,
            success_response=success_response,
            security=security
        )


class OpenAPIAnalyzerTool(BaseTool):
    """OpenAPI 3.0.0文档分析工具，用于提取API的依赖关系和测试场景"""
    name = "openapi_analyzer_tool"
    description = "分析OpenAPI 3.0.0文档，提取API依赖关系和测试场景"
    args_schema: type[BaseModel] = OpenAPIInput
    
    def _run(self, openapi_source: str, source_type: str) -> Dict[str, Any]:
        """执行OpenAPI 3.0.0文档分析"""
        try:
            # 首先解析OpenAPI文档
            parse_tool = OpenAPIParseTool()
            parse_result = parse_tool._run(openapi_source, source_type)
            
            if "error" in parse_result:
                return parse_result
            
            endpoints = parse_result.get("endpoints", [])
            schemas = parse_result.get("schemas", {})
            
            # 分析API依赖关系
            dependencies = self._analyze_dependencies(endpoints, schemas)
            
            # 识别测试场景
            test_scenarios = self._identify_test_scenarios(endpoints, dependencies)
            
            # 生成测试优先级
            test_priorities = self._generate_test_priorities(endpoints, dependencies)
            
            return {
                "api_count": len(endpoints),
                "dependencies": dependencies,
                "test_scenarios": test_scenarios,
                "test_priorities": test_priorities,
                "complexity_analysis": self._analyze_complexity(endpoints)
            }
            
        except Exception as e:
            return {"error": f"分析OpenAPI 3.0.0文档失败: {str(e)}"}
    
    def _analyze_dependencies(self, endpoints: List[Dict], schemas: Dict) -> Dict[str, List[str]]:
        """分析API之间的依赖关系"""
        dependencies = {}
        
        for endpoint in endpoints:
            path = endpoint["path"]
            method = endpoint["method"]
            endpoint_key = f"{method} {path}"
            
            deps = []
            
            # 检查请求体中的引用
            request_body = endpoint.get("request_body", {})
            content = request_body.get("content", {})
            for media_type, media_obj in content.items():
                schema = media_obj.get("schema", {})
                refs = self._extract_refs(schema)
                deps.extend(refs)
            
            # 检查响应中的引用
            responses = endpoint.get("responses", {})
            for status_code, response in responses.items():
                content = response.get("content", {})
                for media_type, media_obj in content.items():
                    schema = media_obj.get("schema", {})
                    refs = self._extract_refs(schema)
                    deps.extend(refs)
            
            # 检查参数中的引用
            for param in endpoint.get("parameters", []):
                schema = param.get("schema", {})
                refs = self._extract_refs(schema)
                deps.extend(refs)
            
            dependencies[endpoint_key] = list(set(deps))  # 去重
        
        return dependencies
    
    def _extract_refs(self, schema: Dict) -> List[str]:
        """从模式中提取引用"""
        refs = []
        
        if not isinstance(schema, dict):
            return refs
        
        if "$ref" in schema:
            refs.append(schema["$ref"])
        
        for key, value in schema.items():
            if isinstance(value, dict):
                refs.extend(self._extract_refs(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        refs.extend(self._extract_refs(item))
        
        return refs
    
    def _identify_test_scenarios(self, endpoints: List[Dict], dependencies: Dict) -> List[Dict]:
        """识别测试场景"""
        scenarios = []
        
        # 按标签分组
        tag_groups = {}
        for endpoint in endpoints:
            for tag in endpoint.get("tags", ["default"]):
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(endpoint)
        
        # 为每个标签创建测试场景
        for tag, tag_endpoints in tag_groups.items():
            scenario = {
                "name": f"{tag}功能测试",
                "description": f"测试{tag}相关的所有API接口",
                "endpoints": [f"{ep['method']} {ep['path']}" for ep in tag_endpoints],
                "priority": "high" if len(tag_endpoints) > 5 else "medium"
            }
            scenarios.append(scenario)
        
        # 创建完整API测试场景
        all_endpoints = [f"{ep['method']} {ep['path']}" for ep in endpoints]
        scenarios.append({
            "name": "完整API测试",
            "description": "测试所有API接口",
            "endpoints": all_endpoints,
            "priority": "medium"
        })
        
        return scenarios
    
    def _generate_test_priorities(self, endpoints: List[Dict], dependencies: Dict) -> Dict[str, str]:
        """生成测试优先级"""
        priorities = {}
        
        for endpoint in endpoints:
            path = endpoint["path"]
            method = endpoint["method"]
            endpoint_key = f"{method} {path}"
            
            # 基于多个因素确定优先级
            priority_score = 0
            
            # GET方法通常优先级较低
            if method == "GET":
                priority_score += 1
            # POST/PUT方法优先级中等
            elif method in ["POST", "PUT"]:
                priority_score += 2
            # DELETE方法优先级较高
            elif method == "DELETE":
                priority_score += 3
            
            # 有依赖的API优先级较高
            if endpoint_key in dependencies and dependencies[endpoint_key]:
                priority_score += 2
            
            # 有认证要求的API优先级较高
            if endpoint.get("security"):
                priority_score += 1
            
            # 根据分数确定优先级
            if priority_score >= 5:
                priority = "high"
            elif priority_score >= 3:
                priority = "medium"
            else:
                priority = "low"
            
            priorities[endpoint_key] = priority
        
        return priorities
    
    def _analyze_complexity(self, endpoints: List[Dict]) -> Dict[str, Any]:
        """分析API复杂度"""
        complexity = {
            "simple": 0,    # 简单API：无参数或只有查询参数
            "medium": 0,    # 中等API：有请求体或多个参数
            "complex": 0    # 复杂API：有复杂请求体、多个参数或响应
        }
        
        for endpoint in endpoints:
            endpoint_complexity = "simple"
            
            # 检查参数数量
            param_count = len(endpoint.get("parameters", []))
            
            # 检查是否有请求体
            has_request_body = bool(endpoint.get("request_body"))
            
            # 检查响应数量
            response_count = len(endpoint.get("responses", {}))
            
            # 计算复杂度
            if has_request_body or param_count > 3:
                endpoint_complexity = "medium"
            
            if has_request_body and param_count > 2 or response_count > 3:
                endpoint_complexity = "complex"
            
            complexity[endpoint_complexity] += 1
        
        return complexity


def create_openapi_tools():
    """创建OpenAPI 3.0.0相关的工具集"""
    return [
        OpenAPIParseTool(),
        OpenAPIAnalyzerTool()
    ]