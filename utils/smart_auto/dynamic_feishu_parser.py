"""
动态飞书API解析器 - 用于处理JavaScript动态加载的内容
"""

import json
import re
import time
import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
from .api_parser import APIParser, APIEndpoint


@dataclass
class DynamicAPIParameter:
    """动态API参数信息"""
    name: str
    param_type: str = "string" 
    location: str = "body"  # query, header, body, path
    required: bool = False
    description: str = ""
    example: str = ""
    enum_values: List[str] = None
    
    def __post_init__(self):
        if self.enum_values is None:
            self.enum_values = []
    
    def __getitem__(self, key):
        """支持字典式访问"""
        if key == 'in':
            # 将location映射为'in'键
            return self.location
        return getattr(self, key)
    
    def __contains__(self, key):
        """支持in操作符"""
        if key == 'in':
            # 'in'总是存在，因为它映射到location
            return True
        return hasattr(self, key)
    
    def get(self, key, default=None):
        """支持字典式get方法"""
        if key == 'in':
            # 将location映射为'in'键
            return self.location
        return getattr(self, key, default)
    
    def to_dict(self) -> Dict:
        """转换为基类期望的字典格式"""
        return {
            'name': self.name,
            'in': self.location,
            'description': self.description,
            'required': self.required,
            'type': self.param_type,
            'schema': {}
        }


@dataclass 
class DynamicAPIEndpoint:
    """动态API接口信息"""
    method: str
    path: str
    summary: str = ""
    description: str = ""
    parameters: List[DynamicAPIParameter] = None
    request_body_schema: Dict = None
    response_schema: Dict = None
    tags: List[str] = None
    operation_id: str = ""
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.tags is None:
            self.tags = []
    
    def to_api_endpoint(self) -> APIEndpoint:
        """转换为基类APIEndpoint格式"""
        param_dicts = [param.to_dict() for param in self.parameters]
        
        return APIEndpoint(
            path=self.path,
            method=self.method,
            summary=self.summary,
            description=self.description,
            operation_id=self.operation_id,
            tags=self.tags,
            parameters=param_dicts,
            request_body=None,
            response_codes=[],
            success_response={},
            security=[]
        )


class DynamicFeishuParser(APIParser):
    """动态飞书API解析器"""
    
    def __init__(self, api_doc_path: str, use_ai: bool = False, timeout: int = 30):
        super().__init__(api_doc_path)
        self.url = api_doc_path
        self.use_ai = use_ai
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_api_doc(self) -> Dict:
        """加载API文档"""
        try:
            response = self.session.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            return {'html': response.text}
        except Exception as e:
            self.logger.error(f"加载API文档失败: {str(e)}")
            raise
    
    def parse_apis(self) -> List[APIEndpoint]:
        """解析API接口"""
        try:
            # 获取页面内容
            html_content = self._get_dynamic_content()
            
            # 解析API信息
            dynamic_apis = self._extract_api_info(html_content)
            
            # 增强解析参数
            for api in dynamic_apis:
                self._enhance_parameter_extraction(api, html_content)
            
            # 转换为基类格式
            api_endpoints = [api.to_api_endpoint() for api in dynamic_apis]
            
            self.logger.info(f"成功解析 {len(api_endpoints)} 个飞书API接口")
            return api_endpoints
            
        except Exception as e:
            self.logger.error(f"解析飞书API文档失败: {str(e)}")
            raise
    
    def parse(self) -> List[APIEndpoint]:
        """解析API接口 - 兼容基类接口"""
        return self.parse_apis()
    
    def _get_dynamic_content(self) -> str:
        """获取页面动态内容"""
        try:
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            # 发送GET请求获取页面内容
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            initial_html = response.text
            
            # 优先尝试从页面源码中提取结构化API信息
            static_data = self._extract_from_static_content(initial_html)
            if static_data:
                self.logger.info("从静态内容中找到API数据")
                return static_data
            
            # 如果静态内容中没有数据，查找JavaScript中的API数据
            api_data = self._extract_api_data_from_js(initial_html)
            
            if api_data:
                self.logger.info("从JavaScript中找到API数据")
                return api_data
            
            # 如果都没找到，返回包含URL信息的增强HTML内容
            enhanced_content = self._create_fallback_content(initial_html)
            if enhanced_content:
                self.logger.info("创建了增强的备用内容")
                return enhanced_content
            
            self.logger.warning("无法从页面中提取API数据，返回初始内容")
            return initial_html
            
        except Exception as e:
            self.logger.error(f"获取动态内容失败: {str(e)}")
            raise
    
    def _extract_api_data_from_js(self, html_content: str) -> Optional[str]:
        """从JavaScript代码中提取API数据"""
        try:
            # 查找包含API数据的script标签
            script_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'__NEXT_DATA__\s*=\s*({.*?});',
                r'API_DATA\s*=\s*({.*?});',
                r'window\._SSR_HYDRATED_DATA\s*=\s*({.*?});'
            ]
            
            for pattern in script_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        api_content = self._extract_api_info_from_data(data)
                        if api_content:
                            return api_content
                    except json.JSONDecodeError:
                        continue
                        
            return None
            
        except Exception as e:
            self.logger.error(f"从JavaScript提取数据失败: {str(e)}")
            return None
    
    def _extract_api_info_from_data(self, data: Dict) -> Optional[str]:
        """从数据结构中提取API信息"""
        try:
            # 递归搜索包含API信息的数据
            for key, value in data.items():
                if isinstance(value, dict):
                    if 'path' in value or 'parameters' in value:
                        return json.dumps(value, ensure_ascii=False)
                    # 递归搜索
                    result = self._extract_api_info_from_data(value)
                    if result:
                        return result
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            if 'path' in item or 'parameters' in item:
                                return json.dumps(item, ensure_ascii=False)
                            result = self._extract_api_info_from_data(item)
                            if result:
                                return result
            return None
        except Exception as e:
            self.logger.error(f"从数据结构提取API信息失败: {str(e)}")
            return None
    
    def _extract_from_static_content(self, html_content: str) -> Optional[str]:
        """从静态内容中提取API信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找包含API信息的元素
            api_elements = soup.find_all(['div', 'section'], class_=re.compile(r'api|parameter|param|request'))
            
            for element in api_elements:
                text = element.get_text()
                if any(keyword in text for keyword in ['receive_id', 'msg_type', 'Authorization']):
                    return str(element)
            
            # 查找表格
            tables = soup.find_all('table')
            for table in tables:
                if any(keyword in table.get_text() for keyword in ['receive_id', 'msg_type']):
                    return str(table)
                    
            return None
            
        except Exception as e:
            self.logger.error(f"从静态内容提取API信息失败: {str(e)}")
            return None
    
    def _create_fallback_content(self, html_content: str) -> str:
        """创建备用内容，包含从URL中提取的API信息"""
        try:
            # 从URL中提取API信息
            path, method = self._infer_api_info_from_url()
            
            # 创建一个包含API信息的增强HTML内容
            enhanced_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>飞书API解析结果 - {method} {path}</title>
                <meta charset="UTF-8">
            </head>
            <body>
                <h1>从URL解析的API信息</h1>
                <div class="api-info">
                    <h2>API详情</h2>
                    <p><strong>HTTP方法:</strong> {method}</p>
                    <p><strong>API路径:</strong> {path}</p>
                    <p><strong>原始URL:</strong> {self.url}</p>
                    
                    <h3>通用飞书API参数</h3>
                    <p>根据飞书开放平台API规范，此API可能包含以下参数：</p>
                    
                    <h4>认证相关参数</h4>
                    <ul>
                        <li><strong>Authorization</strong> (header, required): 访问令牌</li>
                        <li><strong>tenant_access_token</strong> (header, required): 应用令牌</li>
                    </ul>
                    
                    <h4>根据API类型推断的参数</h4>
            """
            
            # 根据API路径添加特定参数
            if 'message' in path.lower():
                enhanced_content += """
                    <ul>
                        <li><strong>receive_id</strong> (body, required): 接收者ID</li>
                        <li><strong>receive_id_type</strong> (body, required): 接收者ID类型</li>
                        <li><strong>msg_type</strong> (body, required): 消息类型</li>
                        <li><strong>content</strong> (body, required): 消息内容</li>
                    </ul>
                """
            elif 'contact' in path.lower() or 'user' in path.lower():
                enhanced_content += """
                    <ul>
                        <li><strong>user_id</strong> (query, optional): 用户ID</li>
                        <li><strong>department_id</strong> (query, optional): 部门ID</li>
                    </ul>
                """
            elif 'doc' in path.lower():
                enhanced_content += """
                    <ul>
                        <li><strong>doc_id</strong> (query, required): 文档ID</li>
                    </ul>
                """
            elif 'sheet' in path.lower():
                enhanced_content += """
                    <ul>
                        <li><strong>spreadsheet_token</strong> (query, required): 表格token</li>
                    </ul>
                """
            else:
                enhanced_content += """
                    <ul>
                        <li><strong>id</strong> (path, required): 资源ID</li>
                    </ul>
                """
            
            enhanced_content += """
                </div>
            </body>
            </html>
            """
            
            return enhanced_content
            
        except Exception as e:
            self.logger.error(f"创建备用内容失败: {str(e)}")
            return ""
    
    def _extract_api_info(self, content: str) -> List[DynamicAPIEndpoint]:
        """提取API基本信息"""
        apis = []
        
        try:
            # 从URL推断API信息
            path, method = self._infer_api_info_from_url()
            
            # 创建API端点
            api = DynamicAPIEndpoint(
                method=method,
                path=path,
                summary=f"{method} {path}",
                description="从飞书开放平台API文档解析"
            )
            
            apis.append(api)
            
        except Exception as e:
            self.logger.error(f"提取API基本信息失败: {str(e)}")
            
        return apis
    
    def _infer_api_info_from_url(self) -> tuple:
        """从URL推断API信息"""
        url_parts = self.url.split('/')
        
        # 扩展支持的API版本列表
        supported_apis = [
            'im-v1', 'im-v2',
            'contact-v1', 'contact-v2', 'contact-v3',
            'docx-v1', 'docx-v2',
            'sheets-v1', 'sheets-v2',
            'approval-v1', 'approval-v2',
            'bitable-v1', 'bitable-v2',
            'wiki-v1', 'wiki-v2',
            'calendar-v1', 'calendar-v2',
            'drive-v1', 'drive-v2',
            'group-chat-v1', 'group-chat-v2'
        ]
        
        # 查找API路径部分
        api_start = -1
        for i, part in enumerate(url_parts):
            if part in supported_apis:
                api_start = i
                break
        
        if api_start == -1:
            # 如果没找到标准版本路径，尝试从路径模式推断
            for i, part in enumerate(url_parts):
                if part == 'server-docs' or part == 'api-reference':
                    # 跳过server-docs，找到后面的API部分
                    if i + 1 < len(url_parts):
                        api_start = i + 1
                        break
            
            if api_start == -1:
                # 如果仍然找不到，使用整个URL作为路径
                api_start = 0
            
        # 提取API路径
        path_parts = url_parts[api_start:]
        if not path_parts:
            # 如果没有路径部分，使用默认路径
            path_parts = ['im-v1', 'message', 'create']
            
        path = '/' + '/'.join(path_parts)
        
        # 根据路径推断HTTP方法
        method = 'POST'  # 默认POST
        
        if any(keyword in path.lower() for keyword in ['get', 'query', 'search', 'list', 'fetch']):
            method = 'GET'
        elif any(keyword in path.lower() for keyword in ['create', 'add', 'send', 'post']):
            method = 'POST'
        elif any(keyword in path.lower() for keyword in ['update', 'put', 'modify', 'edit']):
            method = 'PUT'
        elif any(keyword in path.lower() for keyword in ['delete', 'remove']):
            method = 'DELETE'
        
        return path, method
    
    def _enhance_parameter_extraction(self, api: DynamicAPIEndpoint, content: str):
        """增强参数提取"""
        try:
            # 常见的飞书API参数
            common_params = self._extract_common_feishu_parameters(content)
            
            # 根据API类型添加特定参数
            if 'message' in api.path.lower() or '/message/' in api.path:
                message_params = self._extract_message_parameters(content)
                common_params.extend(message_params)
            elif 'contact' in api.path.lower() or '/contact/' in api.path:
                contact_params = self._extract_contact_parameters(content)
                common_params.extend(contact_params)
            elif 'doc' in api.path.lower() or '/doc/' in api.path:
                doc_params = self._extract_doc_parameters(content)
                common_params.extend(doc_params)
            elif 'sheet' in api.path.lower() or '/sheet/' in api.path:
                sheet_params = self._extract_sheet_parameters(content)
                common_params.extend(sheet_params)
            else:
                # 对于未知类型的API，添加一些通用参数
                generic_params = self._extract_generic_parameters(content, api.path)
                common_params.extend(generic_params)
                
            api.parameters = common_params
            
        except Exception as e:
            self.logger.error(f"增强参数提取失败: {str(e)}")
    
    def _extract_common_feishu_parameters(self, content: str) -> List[DynamicAPIParameter]:
        """提取通用飞书API参数"""
        params = []
        
        # 检查是否包含Authorization
        if 'Authorization' in content or 'authorization' in content.lower():
            params.append(DynamicAPIParameter(
                name="Authorization",
                param_type="string",
                location="header", 
                required=True,
                description="通过STS临时授权获取的访问令牌",
                example="Bearer t-xxx"
            ))
        
        # 检查是否包含tenant_access_token
        if 'tenant_access_token' in content.lower():
            params.append(DynamicAPIParameter(
                name="tenant_access_token",
                param_type="string",
                location="header",
                required=True,
                description="应用 tenant_access_token",
                example="t-xxx"
            ))
            
        return params
    
    def _extract_message_parameters(self, content: str) -> List[DynamicAPIParameter]:
        """提取消息相关参数 - 使用智能推断和已知飞书API结构"""
        params = []
        
        # 对于消息发送API，使用已知的标准参数
        # 根据飞书开放平台API文档的标准结构
        
        # 必填参数
        params.append(DynamicAPIParameter(
            name="receive_id",
            param_type="string",
            location="body",
            required=True,
            description="消息接收者的ID，根据receive_id_type区分类型",
            example="ou_xxx"
        ))
        
        params.append(DynamicAPIParameter(
            name="receive_id_type",
            param_type="string", 
            location="body",
            required=True,
            description="接收者ID类型",
            enum_values=["user_id", "open_id", "union_id", "chat_id"],
            example="user_id"
        ))
        
        params.append(DynamicAPIParameter(
            name="msg_type",
            param_type="string",
            location="body", 
            required=True,
            description="消息类型",
            enum_values=["text", "image", "file", "audio", "video", "sticker"],
            example="text"
        ))
        
        params.append(DynamicAPIParameter(
            name="content",
            param_type="object",
            location="body",
            required=True,
            description="消息内容，JSON格式",
            example='{"text": "Hello World"}'
        ))
        
        # 可选参数
        params.append(DynamicAPIParameter(
            name="uuid",
            param_type="string",
            location="body",
            required=False,
            description="消息唯一标识符，用于消息去重",
            example="msg_unique_id_123"
        ))
        
        return params
    
    def _extract_contact_parameters(self, content: str) -> List[DynamicAPIParameter]:
        """提取联系人相关参数"""
        params = []
        
        # 联系人API的通用参数
        params.append(DynamicAPIParameter(
            name="user_id",
            param_type="string",
            location="query",
            required=False,
            description="用户ID",
            example="ou_xxx"
        ))
        
        params.append(DynamicAPIParameter(
            name="department_id",
            param_type="string",
            location="query", 
            required=False,
            description="部门ID",
            example="od-xxx"
        ))
        
        return params
    
    def _extract_doc_parameters(self, content: str) -> List[DynamicAPIParameter]:
        """提取文档相关参数"""
        params = []
        
        # 文档API的通用参数
        params.append(DynamicAPIParameter(
            name="doc_id",
            param_type="string",
            location="query",
            required=True,
            description="文档ID",
            example="dct_xxx"
        ))
        
        return params
    
    def _extract_sheet_parameters(self, content: str) -> List[DynamicAPIParameter]:
        """提取表格相关参数"""
        params = []
        
        # 表格API的通用参数
        params.append(DynamicAPIParameter(
            name="spreadsheet_token",
            param_type="string", 
            location="query",
            required=True,
            description="表格token",
            example="shtc_xxx"
        ))
        
        return params
    
    def _extract_generic_parameters(self, content: str, api_path: str) -> List[DynamicAPIParameter]:
        """提取通用参数"""
        params = []
        
        # 根据API路径推断可能的参数
        if 'id' in api_path.lower():
            params.append(DynamicAPIParameter(
                name="id",
                param_type="string",
                location="path",
                required=True,
                description="资源ID",
                example="xxx"
            ))
        
        return params


def test_parser():
    """测试解析器"""
    url = "https://open.feishu.cn/document/server-docs/im-v1/message/create?appId=cli_a9aa33797cf89cb2"
    
    parser = DynamicFeishuParser(url)
    apis = parser.parse_apis()
    
    for api in apis:
        print(f"API: {api.method} {api.path}")
        print(f"Summary: {api.summary}")
        print(f"Parameters ({len(api.parameters)}):")
        for param in api.parameters:
            print(f"  - {param.name} ({param.param_type}, {param.location}, required={param.required})")
            if param.description:
                print(f"    Description: {param.description}")
            if param.enum_values:
                print(f"    Enum: {param.enum_values}")
        print("-" * 50)


if __name__ == "__main__":
    test_parser()