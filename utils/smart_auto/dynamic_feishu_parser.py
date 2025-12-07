# -*- coding: utf-8 -*-
"""
# @Time   : 2025/12/06 14:30
# @Author : Smart Auto Platform
# @File   : dynamic_feishu_parser.py
# @describe: 动态飞书API文档解析器
"""

import json
import os
from urllib.parse import quote
from typing import List, Dict, Any
from .api_parser import APIParser, APIEndpoint
from utils.logging_tool.log_control import INFO, ERROR
from utils.other_tools.exceptions import APIParserError
from utils.parse.feishu_parse import transform_feishu_url, download_json


class DynamicFeishuParser(APIParser):
    """动态飞书API文档解析器"""
    
    def __init__(self, api_doc_path: str):
        super().__init__(api_doc_path)
        self.api_data = None
        self.parsed_apis = []
        
    def load_api_doc(self) -> Dict:
        """加载飞书API文档"""
        try:
            # 使用现有的transform_feishu_url函数转换URL
            api_url, path = transform_feishu_url(self.api_doc_path)
            
            # 使用现有的download_json函数获取JSON数据
            data = download_json(api_url)
            
            if not data:
                raise APIParserError("无法获取飞书API文档数据")
                
            # 将数据转换为OpenAPI格式
            openapi_doc = self._convert_to_openapi_format(data, path)
            
            # 设置解析结果
            self.api_data = openapi_doc
            self.content = json.dumps(data, ensure_ascii=False, indent=2)
            
            INFO.logger.info(f"成功加载飞书API文档: {path}")
            return self.api_data
            
        except Exception as e:
            ERROR.logger.error(f"加载飞书API文档失败: {str(e)}")
            raise APIParserError(f"加载飞书API文档失败: {str(e)}")
            
    def parse_apis(self) -> List[APIEndpoint]:
        """解析飞书API文档中的所有API"""
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
            ERROR.logger.error(f"解析飞书API文档失败: {str(e)}")
            raise APIParserError(f"解析飞书API文档失败: {str(e)}")
            
    def extract_api_info(self, api_path: str, api_method: str, api_detail: Dict) -> APIEndpoint:
        """提取单个API的详细信息"""
        # 提取基本信息
        summary = api_detail.get('summary', '')
        description = api_detail.get('description', '')
        operation_id = api_detail.get('operationId', '')
        tags = api_detail.get('tags', [])
        
        # 提取参数信息
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
            
            # 提取schema信息
            if 'application/json' in content:
                request_body_info['schema'] = content['application/json'].get('schema', {})
        
        # 提取响应信息
        responses = api_detail.get('responses', {})
        response_codes = list(responses.keys())
        success_response_info = {}
        
        if '200' in responses:
            success_response = responses['200']
            success_response_info = {
                'description': success_response.get('description', ''),
                'content_types': list(success_response.get('content', {}).keys())
            }
            
            # 提取schema信息
            if 'application/json' in success_response.get('content', {}):
                success_response_info['schema'] = success_response['content']['application/json'].get('schema', {})
        
        # 提取安全信息
        security = api_detail.get('security', [])
        
        # 创建APIEndpoint对象
        endpoint = APIEndpoint(
            path=api_path,
            method=api_method,
            summary=summary,
            description=description,
            operation_id=operation_id,
            tags=tags,
            host="open.feishu.cn",
            base_path="/open-apis",
            parameters=params,
            request_body=request_body_info,
            response_codes=response_codes,
            success_response=success_response_info,
            security=security
        )
        
        return endpoint
        
    def _convert_to_openapi_format(self, data: Dict, path: str) -> Dict:
        """
        将飞书API文档JSON数据转换为OpenAPI格式
        
        Args:
            data: 飞书API文档JSON数据
            path: API路径
            
        Returns:
            OpenAPI格式的文档
        """
        # 创建基本的OpenAPI文档结构
        openapi_doc = {
            'openapi': '3.0.0',
            'info': {
                'title': f'飞书API文档 - {path}',
                'version': '1.0.0',
                'description': '从飞书开放平台获取的API文档'
            },
            'servers': [
                {
                    'url': 'https://open.feishu.cn/open-apis',
                    'description': '飞书开放平台API服务器'
                }
            ],
            'paths': {}
        }
        
        # 根据飞书API返回的数据结构进行解析
        try:
            # 检查是否有数据
            if 'data' not in data:
                raise APIParserError("飞书API返回数据格式不正确")
                
            api_data = data['data']
            
            # 尝试解析内容
            if 'content' in api_data:
                content = api_data['content']
                
                # 尝试解析为JSON
                try:
                    parsed_content = json.loads(content)
                    
                    # 如果内容已经是OpenAPI格式，直接使用
                    if 'paths' in parsed_content:
                        openapi_doc['paths'] = parsed_content['paths']
                        if 'info' in parsed_content:
                            openapi_doc['info'].update(parsed_content['info'])
                    else:
                        # 如果不是OpenAPI格式，创建一个基本的API结构
                        openapi_doc['paths'] = {
                            '/api': {
                                'get': {
                                    'summary': '从飞书API获取的接口',
                                    'description': content,
                                    'responses': {
                                        '200': {
                                            'description': '成功响应'
                                        }
                                    }
                                }
                            }
                        }
                except json.JSONDecodeError:
                    # 如果不是JSON，直接作为描述使用
                    openapi_doc['paths'] = {
                        '/api': {
                            'get': {
                                'summary': '从飞书API获取的接口',
                                'description': content,
                                'responses': {
                                    '200': {
                                        'description': '成功响应'
                                    }
                                }
                            }
                        }
                    }
            else:
                # 如果没有content字段，创建一个基本的API结构
                openapi_doc['paths'] = {
                    '/api': {
                        'get': {
                            'summary': '从飞书API获取的接口',
                            'description': '无法解析API内容',
                            'responses': {
                                '200': {
                                    'description': '成功响应'
                                }
                            }
                        }
                    }
                }
                
        except Exception as e:
            ERROR.logger.error(f"转换飞书API文档为OpenAPI格式失败: {str(e)}")
            # 如果转换失败，返回一个基本的API结构
            openapi_doc['paths'] = {
                '/api': {
                    'get': {
                        'summary': '从飞书API获取的接口',
                        'description': f'解析失败: {str(e)}',
                        'responses': {
                            '200': {
                                'description': '成功响应'
                            }
                        }
                    }
                }
            }
        
        return openapi_doc