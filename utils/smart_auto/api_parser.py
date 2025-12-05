#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2025/12/03 10:00
# @Author : Smart Auto Platform
# @File   : api_parser.py
# @describe: API文档解析模块，支持多种API文档格式的解析
"""

import json
import yaml
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from jsonpath import jsonpath
from utils.logging_tool.log_control import INFO, ERROR
from utils.other_tools.exceptions import APIParserError
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse


@dataclass
class APIEndpoint:
    """API端点数据类"""
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
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = []
        if self.response_codes is None:
            self.response_codes = []
        if self.security is None:
            self.security = []


class APIParser:
    """API文档解析器基类"""
    
    def __init__(self, api_doc_path: str):
        """
        初始化API解析器
        :param api_doc_path: API文档路径
        """
        self.api_doc_path = api_doc_path
        self.api_data = None
        self.parsed_apis: List[APIEndpoint] = []
        
    def load_api_doc(self) -> Dict:
        """加载API文档"""
        raise NotImplementedError("子类必须实现此方法")
        
    def parse_apis(self) -> List[APIEndpoint]:
        """解析API文档，返回API信息列表"""
        raise NotImplementedError("子类必须实现此方法")
        
    def extract_api_info(self, api_path: str, api_method: str, api_detail: Dict) -> Dict:
        """提取单个API的详细信息"""
        raise NotImplementedError("子类必须实现此方法")


class OpenAPIParser(APIParser):
    """OpenAPI文档解析器（兼容Swagger/OpenAPI）"""
    
    def __init__(self, api_doc_path: str):
        super().__init__(api_doc_path)
        self.api_info = {}
        self.host = ""
        self.base_path = ""
        
    def load_api_doc(self) -> Dict:
        """加载OpenAPI/Swagger文档"""
        try:
            # 检查是否为URL
            if self.api_doc_path.startswith(('http://', 'https://')):
                # 从URL加载文档
                import requests
                response = requests.get(self.api_doc_path)
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    self.api_data = response.json()
                else:
                    self.api_data = yaml.safe_load(response.text)
            else:
                # 从本地文件加载文档
                path = Path(self.api_doc_path)
                if not path.exists():
                    raise FileNotFoundError(f"API文档文件不存在: {self.api_doc_path}")
                    
                with open(path, 'r', encoding='utf-8') as f:
                    if path.suffix.lower() in ['.yaml', '.yml']:
                        self.api_data = yaml.safe_load(f)
                    elif path.suffix.lower() == '.json':
                        self.api_data = json.load(f)
                    else:
                        raise APIParserError(f"不支持的文件格式: {path.suffix}")
                    
            # 提取基本信息
            self.api_info = {
                'title': self.api_data.get('info', {}).get('title', ''),
                'version': self.api_data.get('info', {}).get('version', ''),
                'description': self.api_data.get('info', {}).get('description', '')
            }
            
            # 提取服务器信息
            servers = self.api_data.get('servers', [])
            if servers:
                self.host = servers[0].get('url', '')
            else:
                # 兼容旧版Swagger
                self.host = self.api_data.get('host', '')
                self.base_path = self.api_data.get('basePath', '')
                
            INFO.logger.info(f"成功加载API文档: {self.api_info['title']} v{self.api_info['version']}")
            return self.api_data
            
        except Exception as e:
            ERROR.logger.error(f"加载API文档失败: {str(e)}")
            # 提供更详细的错误信息
            if isinstance(e, FileNotFoundError):
                raise APIParserError(f"API文档文件不存在: {self.api_doc_path}")
            elif isinstance(e, yaml.YAMLError):
                raise APIParserError(f"YAML格式错误: {str(e)}")
            elif isinstance(e, json.JSONDecodeError):
                raise APIParserError(f"JSON格式错误: {str(e)}")
            elif isinstance(e, requests.exceptions.RequestException):
                raise APIParserError(f"网络请求错误: {str(e)}")
            else:
                raise APIParserError(f"加载API文档失败: {str(e)}")
            
    def parse_apis(self) -> List[APIEndpoint]:
        """解析OpenAPI/Swagger文档中的所有API"""
        if not self.api_data:
            self.load_api_doc()
            
        try:
            paths = self.api_data.get('paths', {})
            for path, path_item in paths.items():
                for method, api_detail in path_item.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        api_info = self.extract_api_info(path, method.upper(), api_detail)
                        self.parsed_apis.append(api_info)
                        
            INFO.logger.info(f"成功解析 {len(self.parsed_apis)} 个API接口")
            return self.parsed_apis
            
        except Exception as e:
            ERROR.logger.error(f"解析API文档失败: {str(e)}")
            # 提供更详细的错误信息
            if isinstance(e, KeyError):
                raise APIParserError(f"API文档格式不正确，缺少必要的字段: {str(e)}")
            elif isinstance(e, AttributeError):
                raise APIParserError(f"API文档结构不正确: {str(e)}")
            elif isinstance(e, TypeError):
                raise APIParserError(f"API文档数据类型错误: {str(e)}")
            else:
                raise APIParserError(f"解析API文档失败: {str(e)}")
            
    def extract_api_info(self, api_path: str, api_method: str, api_detail: Dict) -> APIEndpoint:
        """提取单个API的详细信息"""
        # 提取基本信息
        parameters = api_detail.get('parameters', [])
        params = []
        for param in parameters:
            param_info = {
                'name': param.get('name', ''),
                'in': param.get('in', ''),  # query, header, path, cookie
                'description': param.get('description', ''),
                'required': param.get('required', False),
                'type': param.get('type', ''),
                'schema': param.get('schema', {})
            }
            params.append(param_info)
        
        # 提取请求体信息
        request_body = api_detail.get('requestBody', {})
        request_body_info = {}
        if request_body:
            content = request_body.get('content', {})
            content_types = list(content.keys())
            request_body_info = {
                'description': request_body.get('description', ''),
                'content_types': content_types,
                'required': request_body.get('required', False)
            }
            
            # 提取请求体schema
            if content_types:
                schema = content[content_types[0]].get('schema', {})
                request_body_info['schema'] = schema
        
        # 提取响应信息
        responses = api_detail.get('responses', {})
        response_codes = list(responses.keys())
        
        # 提取成功响应的schema
        success_response_info = {}
        if '200' in responses:
            success_response = responses['200']
            content = success_response.get('content', {})
            if content:
                content_types = list(content.keys())
                success_response_info = {
                    'description': success_response.get('description', ''),
                    'content_types': content_types
                }
                
                if content_types:
                    schema = content[content_types[0]].get('schema', {})
                    success_response_info['schema'] = schema
        
        # 提取安全认证信息
        security = api_detail.get('security', [])
        
        # 创建APIEndpoint对象
        endpoint = APIEndpoint(
            path=api_path,
            method=api_method,
            summary=api_detail.get('summary', ''),
            description=api_detail.get('description', ''),
            operation_id=api_detail.get('operationId', ''),
            tags=api_detail.get('tags', []),
            host=self.host,
            base_path=self.base_path,
            parameters=params,
            request_body=request_body_info,
            response_codes=response_codes,
            success_response=success_response_info,
            security=security
        )
        
        return endpoint


# 为了向后兼容，保留SwaggerParser作为OpenAPIParser的别名
SwaggerParser = OpenAPIParser


class PostmanParser(APIParser):
    """Postman集合文档解析器"""
    
    def __init__(self, api_doc_path: str):
        super().__init__(api_doc_path)
        
    def load_api_doc(self) -> Dict:
        """加载Postman集合文档"""
        try:
            path = Path(self.api_doc_path)
            if not path.exists():
                raise FileNotFoundError(f"API文档文件不存在: {self.api_doc_path}")
                
            with open(path, 'r', encoding='utf-8') as f:
                self.api_data = json.load(f)
                
            INFO.logger.info(f"成功加载Postman集合: {self.api_data.get('info', {}).get('name', '')}")
            return self.api_data
            
        except Exception as e:
            ERROR.logger.error(f"加载Postman集合失败: {str(e)}")
            raise APIParserError(f"加载Postman集合失败: {str(e)}")
            
    def parse_apis(self) -> List[APIEndpoint]:
        """解析Postman集合中的所有API"""
        if not self.api_data:
            self.load_api_doc()
            
        try:
            items = self.api_data.get('item', [])
            self._parse_items(items)
            
            INFO.logger.info(f"成功解析 {len(self.parsed_apis)} 个API接口")
            return self.parsed_apis
            
        except Exception as e:
            ERROR.logger.error(f"解析Postman集合失败: {str(e)}")
            raise APIParserError(f"解析Postman集合失败: {str(e)}")
            
    def _parse_items(self, items: List[Dict], folder: str = ""):
        """递归解析Postman集合中的项目"""
        for item in items:
            if 'item' in item:  # 文件夹
                folder_name = f"{folder}/{item.get('name', '')}" if folder else item.get('name', '')
                self._parse_items(item.get('item', []), folder_name)
            else:  # API请求
                api_info = self._extract_request_info(item, folder)
                self.parsed_apis.append(api_info)
                
    def _extract_request_info(self, item: Dict, folder: str) -> APIEndpoint:
        """提取Postman请求的详细信息"""
        request = item.get('request', {})
        
        # 提取URL信息
        url_info = request.get('url', {})
        url_raw = self._extract_url(url_info)
        
        # 解析URL，获取路径和主机
        if isinstance(url_info, str):
            path = url_info
            host = ""
        else:
            # 从URL中提取路径
            raw_path = url_info.get('raw', '')
            # 简单处理，假设host是第一部分
            parts = raw_path.split('/')
            if len(parts) > 3:
                path = '/' + '/'.join(parts[3:])
                host = '/'.join(parts[:3])
            else:
                path = raw_path
                host = '/'.join(parts[:3])
        
        # 提取参数信息
        params = []
        if isinstance(url_info, dict) and 'query' in url_info:
            for param in url_info['query']:
                param_info = {
                    'name': param.get('key', ''),
                    'in': 'query',
                    'description': param.get('description', ''),
                    'required': param.get('disabled', True) == False,
                    'type': 'string',
                    'schema': {}
                }
                params.append(param_info)
        
        # 提取请求头信息
        headers = request.get('header', [])
        for header in headers:
            header_info = {
                'name': header.get('key', ''),
                'in': 'header',
                'description': header.get('description', ''),
                'required': header.get('disabled', True) == False,
                'type': 'string',
                'schema': {}
            }
            params.append(header_info)
        
        # 提取请求体信息
        body_info = self._extract_body(request)
        request_body_info = {}
        if body_info:
            mode = body_info.get('mode', '')
            request_body_info = {
                'description': '',
                'content_types': [],
                'required': False,
                'mode': mode
            }
            
            if mode == 'raw' and 'raw' in body_info:
                request_body_info['content_types'] = ['text/plain']
                request_body_info['raw'] = body_info['raw']
            elif mode == 'json' and 'raw' in body_info:
                request_body_info['content_types'] = ['application/json']
                request_body_info['raw'] = body_info['raw']
            elif mode == 'formdata' and 'formdata' in body_info:
                request_body_info['content_types'] = ['multipart/form-data']
                request_body_info['formdata'] = body_info['formdata']
        
        # 提取响应信息
        responses = item.get('response', [])
        response_codes = []
        success_response_info = {}
        
        for response in responses:
            code = response.get('code', '')
            if code:
                response_codes.append(str(code))
                if code == 200 and not success_response_info:
                    success_response_info = {
                        'description': response.get('name', ''),
                        'content_types': ['application/json'],
                        'body': response.get('body', '')
                    }
        
        # 创建APIEndpoint对象
        endpoint = APIEndpoint(
            path=path,
            method=request.get('method', ''),
            summary=item.get('name', ''),
            description=item.get('description', ''),
            operation_id='',
            tags=[folder] if folder else [],
            host=host,
            base_path="",
            parameters=params,
            request_body=request_body_info,
            response_codes=response_codes,
            success_response=success_response_info,
            security=[]
        )
        
        return endpoint
        
    def _extract_url(self, url_info: Union[str, Dict]) -> str:
        """提取URL信息"""
        if isinstance(url_info, str):
            return url_info
        elif isinstance(url_info, dict):
            return url_info.get('raw', '')
        return ''
        
    def _extract_headers(self, headers: List[Dict]) -> Dict:
        """提取请求头信息"""
        header_dict = {}
        for header in headers:
            key = header.get('key', '')
            value = header.get('value', '')
            if key and value:
                header_dict[key] = value
        return header_dict
        
    def _extract_body(self, request: Dict) -> Dict:
        """提取请求体信息"""
        body = request.get('body', {})
        if not body:
            return {}
            
        mode = body.get('mode', '')
        body_info = {'mode': mode}
        
        if mode == 'raw':
            body_info['raw'] = body.get('raw', '')
            body_info['options'] = body.get('options', {})
        elif mode == 'formdata':
            body_info['formdata'] = body.get('formdata', [])
        elif mode == 'urlencoded':
            body_info['urlencoded'] = body.get('urlencoded', [])
        elif mode == 'file':
            body_info['file'] = body.get('file', {})
            
        return body_info


class APIParserFactory:
    """API解析器工厂类"""
    
    @staticmethod
    def create_parser(api_doc_path: str) -> APIParser:
        """根据API文档类型创建对应的解析器"""
        # 检查是否为URL
        if api_doc_path.startswith(('http://', 'https://')):
            parsed_url = urlparse(api_doc_path)
            
            # 检查是否为飞书开放平台API文档
            if 'open.feishu.cn' in parsed_url.netloc and 'document' in parsed_url.path:
                from .dynamic_feishu_parser import DynamicFeishuParser
                return DynamicFeishuParser(api_doc_path)
            else:
                # 其他URL类型，默认使用OpenAPI解析器
                return OpenAPIParser(api_doc_path)
        
        # 处理本地文件
        path = Path(api_doc_path)
        
        if not path.exists():
            raise FileNotFoundError(f"API文档文件不存在: {api_doc_path}")
            
        # 尝试根据文件扩展名判断文档类型
        if path.suffix.lower() in ['.yaml', '.yml', '.json']:
            # 进一步判断是否为OpenAPI/Swagger文档
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    if path.suffix.lower() in ['.yaml', '.yml']:
                        doc = yaml.safe_load(f)
                    else:
                        doc = json.load(f)
                        
                # 检查是否包含OpenAPI/Swagger的关键字段
                if 'swagger' in doc or 'openapi' in doc:
                    return OpenAPIParser(api_doc_path)
                elif 'info' in doc and 'item' in doc:  # Postman集合
                    return PostmanParser(api_doc_path)
                else:
                    # 默认使用OpenAPI解析器
                    return OpenAPIParser(api_doc_path)
            except:
                # 如果解析失败，默认使用OpenAPI解析器
                return OpenAPIParser(api_doc_path)
        else:
            raise APIParserError(f"不支持的API文档格式: {path.suffix}")


def parse_api_document(api_doc_path: str) -> List[APIEndpoint]:
    """
    解析API文档，返回API信息列表
    :param api_doc_path: API文档路径
    :return: API信息列表
    """
    parser = APIParserFactory.create_parser(api_doc_path)
    return parser.parse_apis()


if __name__ == '__main__':
    # 示例用法
    try:
        # 解析OpenAPI/Swagger文档
        apis = parse_api_document('path/to/openapi.yaml')
        print(f"解析到 {len(apis)} 个API")
        
        # 解析Postman集合
        # apis = parse_api_document('path/to/postman_collection.json')
        # print(f"解析到 {len(apis)} 个API")
        
    except Exception as e:
        print(f"解析API文档失败: {str(e)}")