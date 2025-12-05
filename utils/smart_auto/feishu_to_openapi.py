"""
飞书API到OpenAPI 3.0.0转换工具
实现从飞书API URL到OpenAPI 3.0.0文档的完整转换流程
"""

import json
import os
import sys
import logging
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import yaml

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.smart_auto.feishu_api_parser import FeishuAPIParser, APIParserError
from utils.smart_auto.openapi_parser_tool import OpenAPIInput, OpenAPIParseTool
from utils.logging_tool.log_control import INFO, ERROR

class FeishuToOpenAPIConverter:
    """飞书API到OpenAPI 3.0.0转换器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化转换器
        
        Args:
            config: 配置信息，包含请求头、代理等设置
        """
        self.config = config or {}
        self.headers = self.config.get('headers', {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = self.config.get('timeout', 30)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_feishu_api_page(self, api_url: str) -> str:
        """
        获取飞书API文档页面内容
        
        Args:
            api_url: 飞书API文档URL
            
        Returns:
            页面HTML内容
        """
        try:
            INFO.logger.info(f"正在获取飞书API文档页面: {api_url}")
            response = self.session.get(api_url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            ERROR.logger.error(f"获取飞书API文档页面失败: {str(e)}")
            raise APIParserError(f"获取飞书API文档页面失败: {str(e)}")
    
    def extract_api_data_from_page(self, html_content: str, api_url: str) -> Dict:
        """
        从飞书API文档页面提取API数据
        
        Args:
            html_content: 页面HTML内容
            api_url: API URL
            
        Returns:
            提取的API数据
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取API基本信息
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "飞书API"
            
            # 提取API分类
            path_parts = urlparse(api_url).path.split('/')
            api_category = path_parts[-1] if path_parts else ""
            
            # 提取API描述
            desc_elem = soup.find('meta', attrs={'name': 'description'})
            description = desc_elem.get('content', '') if desc_elem else ""
            
            # 提取API文档内容
            content_elem = soup.find('div', class_='markdown-body') or soup.find('div', class_='api-doc')
            content = content_elem.get_text() if content_elem else html_content
            
            return {
                'title': title,
                'api_category': api_category,
                'description': description,
                'content': content,
                'url': api_url
            }
        except Exception as e:
            ERROR.logger.error(f"从页面提取API数据失败: {str(e)}")
            raise APIParserError(f"从页面提取API数据失败: {str(e)}")
    
    def convert_to_openapi(self, api_url: str, save_path: Optional[str] = None) -> Dict:
        """
        将飞书API URL转换为OpenAPI 3.0.0文档
        
        Args:
            api_url: 飞书API文档URL
            save_path: 保存路径（可选）
            
        Returns:
            OpenAPI 3.0.0格式文档
        """
        try:
            # 1. 获取飞书API文档页面
            html_content = self.fetch_feishu_api_page(api_url)
            
            # 2. 从页面提取API数据
            api_data = self.extract_api_data_from_page(html_content, api_url)
            
            # 3. 使用FeishuAPIParser解析API
            parser = FeishuAPIParser(source_type='content', source=html_content, api_data=api_data)
            openapi_doc = parser.parse()
            
            # 4. 优化OpenAPI文档
            openapi_doc = self._optimize_openapi_doc(openapi_doc, api_url)
            
            # 5. 保存文档（如果指定了路径）
            if save_path:
                self._save_openapi_doc(openapi_doc, save_path)
            
            return openapi_doc
            
        except Exception as e:
            ERROR.logger.error(f"转换飞书API到OpenAPI文档失败: {str(e)}")
            raise APIParserError(f"转换飞书API到OpenAPI文档失败: {str(e)}")
    
    def _optimize_openapi_doc(self, openapi_doc: Dict, api_url: str) -> Dict:
        """
        优化OpenAPI文档
        
        Args:
            openapi_doc: 原始OpenAPI文档
            api_url: API URL
            
        Returns:
            优化后的OpenAPI文档
        """
        try:
            # 确保版本是3.0.0
            openapi_doc['openapi'] = '3.0.0'
            
            # 添加更多信息
            if 'info' not in openapi_doc:
                openapi_doc['info'] = {}
            
            # 添加来源URL
            openapi_doc['info']['x-source-url'] = api_url
            
            # 添加生成工具信息
            if 'x-generator' not in openapi_doc['info']:
                openapi_doc['info']['x-generator'] = 'FeishuToOpenAPIConverter'
            
            # 确保有servers
            if 'servers' not in openapi_doc or not openapi_doc['servers']:
                openapi_doc['servers'] = [
                    {
                        'url': 'https://open.feishu.cn/open-apis',
                        'description': '飞书开放平台API服务器'
                    }
                ]
            
            # 确保有components
            if 'components' not in openapi_doc:
                openapi_doc['components'] = {}
            
            # 添加安全方案
            if 'securitySchemes' not in openapi_doc['components']:
                openapi_doc['components']['securitySchemes'] = {
                    'BearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT',
                        'description': '飞书开放平台访问令牌'
                    }
                }
            
            # 为所有操作添加安全要求
            if 'paths' in openapi_doc:
                for path, path_item in openapi_doc['paths'].items():
                    for method, operation in path_item.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            if 'security' not in operation:
                                operation['security'] = [{'BearerAuth': []}]
            
            return openapi_doc
            
        except Exception as e:
            ERROR.logger.error(f"优化OpenAPI文档失败: {str(e)}")
            return openapi_doc
    
    def _save_openapi_doc(self, openapi_doc: Dict, save_path: str) -> None:
        """
        保存OpenAPI文档到文件
        
        Args:
            openapi_doc: OpenAPI文档
            save_path: 保存路径
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 根据文件扩展名决定保存格式
            if save_path.endswith('.json'):
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(openapi_doc, f, ensure_ascii=False, indent=2)
            elif save_path.endswith('.yaml') or save_path.endswith('.yml'):
                with open(save_path, 'w', encoding='utf-8') as f:
                    yaml.dump(openapi_doc, f, default_flow_style=False, allow_unicode=True)
            else:
                # 默认保存为JSON
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(openapi_doc, f, ensure_ascii=False, indent=2)
            
            INFO.logger.info(f"OpenAPI文档已保存到: {save_path}")
            
        except Exception as e:
            ERROR.logger.error(f"保存OpenAPI文档失败: {str(e)}")
            raise APIParserError(f"保存OpenAPI文档失败: {str(e)}")
    
    def batch_convert(self, api_urls: List[str], output_dir: str) -> List[Dict]:
        """
        批量转换飞书API URL到OpenAPI文档
        
        Args:
            api_urls: API URL列表
            output_dir: 输出目录
            
        Returns:
            OpenAPI文档列表
        """
        results = []
        
        for i, api_url in enumerate(api_urls):
            try:
                INFO.logger.info(f"正在处理第 {i+1}/{len(api_urls)} 个API: {api_url}")
                
                # 生成文件名
                parsed_url = urlparse(api_url)
                filename = f"{parsed_url.path.replace('/', '_').strip('_')}.json"
                save_path = os.path.join(output_dir, filename)
                
                # 转换API
                openapi_doc = self.convert_to_openapi(api_url, save_path)
                results.append({
                    'url': api_url,
                    'success': True,
                    'doc': openapi_doc,
                    'path': save_path
                })
                
            except Exception as e:
                ERROR.logger.error(f"转换API失败 {api_url}: {str(e)}")
                results.append({
                    'url': api_url,
                    'success': False,
                    'error': str(e)
                })
        
        return results


def create_feishu_to_openapi_tool(config: Optional[Dict] = None):
    """
    创建飞书API到OpenAPI转换工具
    
    Args:
        config: 配置信息
        
    Returns:
        转换器实例
    """
    return FeishuToOpenAPIConverter(config)


# 便捷函数
def convert_feishu_api_to_openapi(api_url: str, save_path: Optional[str] = None, config: Optional[Dict] = None) -> Dict:
    """
    将飞书API URL转换为OpenAPI 3.0.0文档
    
    Args:
        api_url: 飞书API文档URL
        save_path: 保存路径（可选）
        config: 配置信息（可选）
        
    Returns:
        OpenAPI 3.0.0格式文档
    """
    converter = FeishuToOpenAPIConverter(config)
    return converter.convert_to_openapi(api_url, save_path)


if __name__ == "__main__":
    # 示例用法
    api_url = "https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/api-docs"
    
    try:
        openapi_doc = convert_feishu_api_to_openapi(api_url, "feishu_api_openapi.json")
        print("转换成功!")
        print(json.dumps(openapi_doc, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"转换失败: {str(e)}")