#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2025/12/04 10:00
# @Author : Smart Auto Platform
# @File   : feishu_api_parser.py
# @describe: 飞书开放平台API文档解析器，支持从飞书API文档URL解析API接口
"""

import json
import re
import requests
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from utils.logging_tool.log_control import INFO, ERROR
from utils.other_tools.exceptions import APIParserError


@dataclass
class FeishuAPIEndpoint:
    """飞书API端点数据类"""
    path: str
    method: str
    summary: str = ""
    description: str = ""
    operation_id: str = ""
    tags: List[str] = None
    host: str = ""
    base_path: str = ""
    parameters: List[Dict] = None
    request_body: Dict = None
    response_codes: List[str] = None
    success_response: Dict = None
    security: List[Dict] = None
    api_category: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = []
        if self.response_codes is None:
            self.response_codes = []
        if self.security is None:
            self.security = []


class FeishuAPIParser:
    """飞书开放平台API文档解析器"""
    
    def __init__(self, api_doc_url: str):
        """
        初始化飞书API解析器
        :param api_doc_url: 飞书API文档URL
        """
        self.api_doc_url = api_doc_url
        self.api_data = None
        self.parsed_apis: List[FeishuAPIEndpoint] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def load_api_doc(self) -> Dict:
        """加载飞书API文档"""
        try:
            INFO.logger.info(f"正在加载飞书API文档: {self.api_doc_url}")
            
            # 解析URL，获取API分类和路径
            parsed_url = urlparse(self.api_doc_url)
            path_parts = parsed_url.path.split('/')
            
            # 从URL中提取API分类信息
            api_category = ""
            if "server-docs" in path_parts:
                server_docs_index = path_parts.index("server-docs")
                if len(path_parts) > server_docs_index + 1:
                    api_category = path_parts[server_docs_index + 1]
            
            # 请求API文档页面
            response = self.session.get(self.api_doc_url, timeout=30)
            response.raise_for_status()
            
            # 解析HTML内容
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取API文档数据
            self.api_data = {
                'url': self.api_doc_url,
                'api_category': api_category,
                'html_content': response.text,
                'soup': soup
            }
            
            INFO.logger.info(f"成功加载飞书API文档，分类: {api_category}")
            return self.api_data
            
        except Exception as e:
            ERROR.logger.error(f"加载飞书API文档失败: {str(e)}")
            raise APIParserError(f"加载飞书API文档失败: {str(e)}")
            
    def parse_apis(self) -> List[FeishuAPIEndpoint]:
        """解析飞书API文档中的所有API"""
        if not self.api_data:
            self.load_api_doc()
            
        try:
            soup = self.api_data['soup']
            api_category = self.api_data['api_category']
            
            # 查找API方法部分
            api_sections = soup.find_all('div', class_='api-method')
            if not api_sections:
                # 尝试其他可能的选择器
                api_sections = soup.find_all('section', class_='api-section')
            
            if not api_sections:
                # 如果没有找到明确的API部分，尝试解析整个页面
                api_sections = [soup]
            
            for section in api_sections:
                # 解析API端点信息
                api_endpoints = self._extract_api_endpoints(section, api_category)
                self.parsed_apis.extend(api_endpoints)
                
            INFO.logger.info(f"成功解析 {len(self.parsed_apis)} 个飞书API接口")
            return self.parsed_apis
            
        except Exception as e:
            ERROR.logger.error(f"解析飞书API文档失败: {str(e)}")
            raise APIParserError(f"解析飞书API文档失败: {str(e)}")
            
    def _extract_api_endpoints(self, section, api_category: str) -> List[FeishuAPIEndpoint]:
        """从HTML部分提取API端点信息"""
        endpoints = []
        
        try:
            # 查找HTTP方法和路径
            method_elements = section.find_all(['span', 'div'], class_=re.compile(r'(http-method|method|request-type)'))
            path_elements = section.find_all(['span', 'div', 'code'], class_=re.compile(r'(api-path|path|endpoint)'))
            
            # 如果没有找到明确的元素，尝试通过文本匹配
            if not method_elements:
                method_patterns = [r'\b(GET|POST|PUT|DELETE|PATCH)\b']
                for pattern in method_patterns:
                    matches = re.finditer(pattern, section.get_text())
                    for match in matches:
                        method = match.group(1)
                        # 尝试找到对应的路径
                        path = self._find_path_near_method(section, match)
                        if path:
                            endpoint = self._create_endpoint_from_section(section, method, path, api_category)
                            if endpoint:
                                endpoints.append(endpoint)
            
            # 如果找到了明确的元素，解析它们
            for i, method_elem in enumerate(method_elements):
                method = method_elem.get_text().strip().upper()
                if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    continue
                
                # 尝试找到对应的路径
                path = ""
                if i < len(path_elements):
                    path = path_elements[i].get_text().strip()
                else:
                    path = self._find_path_near_method(section, None, method_elem)
                
                if path:
                    endpoint = self._create_endpoint_from_section(section, method, path, api_category)
                    if endpoint:
                        endpoints.append(endpoint)
                        
        except Exception as e:
            ERROR.logger.error(f"提取API端点信息失败: {str(e)}")
            
        return endpoints
    
    def _find_path_near_method(self, section, match=None, method_elem=None) -> str:
        """在方法附近查找API路径"""
        try:
            # 如果有匹配对象，获取其位置
            if match:
                text = section.get_text()
                # 获取方法后面的文本，尝试找到路径
                after_method = text[match.end():match.end()+100]
                path_match = re.search(r'(/[a-zA-Z0-9/_{}-]+)', after_method)
                if path_match:
                    return path_match.group(1)
            
            # 如果有方法元素，查找附近的路径
            if method_elem:
                # 查找同级或父级元素中的路径
                parent = method_elem.parent
                if parent:
                    path_elements = parent.find_all(['code', 'span', 'div'], string=re.compile(r'^/[a-zA-Z0-9/_{}-]+$'))
                    if path_elements:
                        return path_elements[0].get_text().strip()
                    
                    # 尝试在父元素的文本中查找路径
                    parent_text = parent.get_text()
                    path_match = re.search(r'(/[a-zA-Z0-9/_{}-]+)', parent_text)
                    if path_match:
                        return path_match.group(1)
            
            # 如果以上方法都失败，尝试在整个部分中查找路径
            section_text = section.get_text()
            path_matches = re.findall(r'(/[a-zA-Z0-9/_{}-]+)', section_text)
            if path_matches:
                # 返回第一个看起来像API路径的匹配
                for path in path_matches:
                    if len(path) > 3:  # 过滤掉太短的匹配
                        return path
                        
            return ""
            
        except Exception as e:
            ERROR.logger.error(f"查找API路径失败: {str(e)}")
            return ""
    
    def _create_endpoint_from_section(self, section, method: str, path: str, api_category: str) -> Optional[FeishuAPIEndpoint]:
        """从HTML部分创建API端点对象"""
        try:
            # 提取标题和描述
            title_elem = section.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'(title|heading)'))
            title = title_elem.get_text().strip() if title_elem else ""
            
            desc_elem = section.find(['p', 'div'], class_=re.compile(r'(description|desc)'))
            description = desc_elem.get_text().strip() if desc_elem else ""
            
            # 提取参数信息
            parameters = self._extract_parameters(section)
            
            # 提取请求体信息
            request_body = self._extract_request_body(section)
            
            # 提取响应信息
            success_response = self._extract_response(section)
            
            # 创建API端点对象
            endpoint = FeishuAPIEndpoint(
                path=path,
                method=method,
                summary=title,
                description=description,
                parameters=parameters,
                request_body=request_body,
                success_response=success_response,
                api_category=api_category,
                host="https://open.feishu.cn",
                base_path="/open-apis"
            )
            
            return endpoint
            
        except Exception as e:
            ERROR.logger.error(f"创建API端点对象失败: {str(e)}")
            return None
    
    def _extract_parameters(self, section) -> List[Dict]:
        """提取API参数信息"""
        parameters = []
        
        try:
            # 查找参数表格
            param_tables = section.find_all('table', class_=re.compile(r'(parameter|param)'))
            
            for table in param_tables:
                rows = table.find_all('tr')
                if not rows:
                    continue
                
                # 获取表头
                headers = [th.get_text().strip().lower() for th in rows[0].find_all('th')]
                
                # 解析数据行
                for row in rows[1:]:
                    cells = row.find_all('td')
                    if len(cells) < len(headers):
                        continue
                    
                    param_data = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            param_data[headers[i]] = cell.get_text().strip()
                    
                    # 转换为标准格式
                    param_info = {
                        'name': param_data.get('name', param_data.get('参数名', '')),
                        'in': param_data.get('in', param_data.get('位置', 'query')),
                        'description': param_data.get('description', param_data.get('描述', '')),
                        'required': param_data.get('required', param_data.get('是否必填', 'false')).lower() == 'true',
                        'type': param_data.get('type', param_data.get('类型', 'string')),
                        'schema': {}
                    }
                    
                    if param_info['name']:
                        parameters.append(param_info)
            
            # 如果没有找到参数表格，尝试查找其他参数元素
            if not parameters:
                param_elements = section.find_all(['div', 'li'], class_=re.compile(r'(parameter|param)'))
                for elem in param_elements:
                    text = elem.get_text().strip()
                    # 尝试解析参数信息
                    param_match = re.match(r'(\w+)\s*\(([^)]+)\):\s*(.+)', text)
                    if param_match:
                        name = param_match.group(1)
                        type_info = param_match.group(2)
                        desc = param_match.group(3)
                        
                        param_info = {
                            'name': name,
                            'in': 'query',
                            'description': desc,
                            'required': 'required' in type_info.lower(),
                            'type': 'string',
                            'schema': {}
                        }
                        
                        parameters.append(param_info)
                        
        except Exception as e:
            ERROR.logger.error(f"提取API参数信息失败: {str(e)}")
            
        return parameters
    
    def _extract_request_body(self, section) -> Dict:
        """提取请求体信息"""
        request_body_info = {}
        
        try:
            # 查找请求体部分
            body_sections = section.find_all(['div', 'section'], class_=re.compile(r'(request-body|body)'))
            
            for body_section in body_sections:
                # 查找代码块
                code_blocks = body_section.find_all(['pre', 'code'])
                for code in code_blocks:
                    code_text = code.get_text().strip()
                    
                    # 尝试解析JSON
                    try:
                        json_data = json.loads(code_text)
                        request_body_info = {
                            'description': '',
                            'content_types': ['application/json'],
                            'required': True,
                            'schema': {
                                'type': 'object',
                                'example': json_data
                            }
                        }
                        break
                    except:
                        # 如果不是JSON，可能是其他格式
                        request_body_info = {
                            'description': code_text,
                            'content_types': ['text/plain'],
                            'required': True,
                            'raw': code_text
                        }
                
                if request_body_info:
                    break
                    
        except Exception as e:
            ERROR.logger.error(f"提取请求体信息失败: {str(e)}")
            
        return request_body_info
    
    def _extract_response(self, section) -> Dict:
        """提取响应信息"""
        response_info = {}
        
        try:
            # 查找响应部分
            response_sections = section.find_all(['div', 'section'], class_=re.compile(r'(response|response-body)'))
            
            for response_section in response_sections:
                # 查找代码块
                code_blocks = response_section.find_all(['pre', 'code'])
                for code in code_blocks:
                    code_text = code.get_text().strip()
                    
                    # 尝试解析JSON
                    try:
                        json_data = json.loads(code_text)
                        response_info = {
                            'description': '',
                            'content_types': ['application/json'],
                            'schema': {
                                'type': 'object',
                                'example': json_data
                            }
                        }
                        break
                    except:
                        # 如果不是JSON，可能是其他格式
                        response_info = {
                            'description': code_text,
                            'content_types': ['text/plain'],
                            'example': code_text
                        }
                
                if response_info:
                    break
                    
        except Exception as e:
            ERROR.logger.error(f"提取响应信息失败: {str(e)}")
            
        return response_info
    
    def parse(self) -> Dict:
        """解析飞书API文档并返回标准格式结果"""
        try:
            # 加载API文档
            self.load_api_doc()
            
            # 解析API接口
            self.parse_apis()
            
            # 转换为标准格式
            return self.convert_to_standard_format()
            
        except Exception as e:
            ERROR.logger.error(f"解析飞书API文档失败: {str(e)}")
            raise APIParserError(f"解析飞书API文档失败: {str(e)}")
    
    def convert_to_standard_format(self) -> Dict:
        """将解析结果转换为标准格式，兼容现有的API解析器"""
        if not self.parsed_apis:
            self.parse_apis()
            
        # 转换为标准格式
        apis_dict = []
        for api in self.parsed_apis:
            api_dict = {
                'path': api.path,
                'method': api.method,
                'operationId': api.operation_id,
                'parameters': api.parameters,
                'request_body': api.request_body,
                'success_response': api.success_response,
                'tags': api.tags + [api.api_category] if api.api_category else api.tags,
                'summary': api.summary,
                'description': api.description,
                'host': api.host,
                'base_path': api.base_path
            }
            apis_dict.append(api_dict)
            
        return {
            'openapi': '3.0.0',
            'info': {
                'title': f'飞书开放平台API - {self.api_data["api_category"] if self.api_data else ""}',
                'version': '1.0.0',
                'description': '从飞书开放平台API文档解析生成的接口文档'
            },
            'servers': [
                {
                    'url': f'{self.parsed_apis[0].host if self.parsed_apis else "https://open.feishu.cn"}{self.parsed_apis[0].base_path if self.parsed_apis else "/open-apis"}',
                    'description': '飞书开放平台API服务器'
                }
            ],
            'paths': self._convert_paths_to_openapi(apis_dict),
            'components': {
                'securitySchemes': {
                    'BearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT'
                    }
                }
            }
        }
    
    def _convert_paths_to_openapi(self, apis_dict: List[Dict]) -> Dict:
        """将API列表转换为OpenAPI格式的paths对象"""
        paths = {}
        
        for api in apis_dict:
            path = api['path']
            method = api['method'].lower()
            
            if path not in paths:
                paths[path] = {}
            
            # 构建方法对象
            method_obj = {
                'summary': api.get('summary', ''),
                'description': api.get('description', ''),
                'operationId': api.get('operationId', ''),
                'tags': api.get('tags', []),
                'parameters': api.get('parameters', []),
                'responses': {
                    '200': {
                        'description': '成功响应',
                        'content': {
                            'application/json': {
                                'schema': api.get('success_response', {}).get('schema', {})
                            }
                        }
                    }
                }
            }
            
            # 添加请求体
            if api.get('request_body'):
                method_obj['requestBody'] = {
                    'content': {
                        'application/json': {
                            'schema': api['request_body'].get('schema', {})
                        }
                    },
                    'required': api['request_body'].get('required', False)
                }
            
            # 添加安全要求
            method_obj['security'] = [{'BearerAuth': []}]
            
            paths[path][method] = method_obj
            
        return paths