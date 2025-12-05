# -*- coding: utf-8 -*-
"""
@Time   : 2025/12/04
@Author : 
@File   : ai_client.py
@Desc   : AI客户端，用于调用大模型API
"""
import os
import json
import yaml
import requests
from typing import Dict, Any, Optional
from utils.logging_tool.log_control import INFO, ERROR


class AIClient:
    """AI客户端，用于调用大模型API"""
    
    def __init__(self, config_path: str = None):
        """
        初始化AI客户端
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的configs/config.yaml
        """
        if config_path is None:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, "configs", "config.yaml")
        
        self.config = self._load_config(config_path)
        self.model_name = self.config.get("ai_config", {}).get("model_name", "deepseek-chat")
        self.api_key = self.config.get("ai_config", {}).get("api_key", "")
        self.temperature = self.config.get("ai_config", {}).get("temperature", 0.7)
        self.max_tokens = self.config.get("ai_config", {}).get("max_tokens", 8192)
        self.base_url = self.config.get("ai_config", {}).get("base_url", "https://api.siliconflow.cn/v1")
        
        INFO.logger.info(f"AI客户端初始化完成，文本模型: {self.model_name}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            INFO.logger.info(f"成功加载配置文件: {config_path}")
            return config
        except Exception as e:
            ERROR.logger.error(f"加载配置文件失败: {str(e)}")
            return {}
    
    def _make_api_request(self, messages: list) -> Optional[Dict[str, Any]]:
        """向AI API发送请求"""
        if not self.api_key or self.api_key in ["your-deepseek-api-key", "sk-your-siliconflow-api-key"]:
            ERROR.logger.error("API密钥未配置或使用默认值，请检查config.yaml文件")
            return None
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            # 增加连接和读取超时时间
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=(60, 180)  # 连接超时60秒，读取超时180秒
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                ERROR.logger.error(f"API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
        except Exception as e:
            ERROR.logger.error(f"API请求异常: {str(e)}")
            return None
    
    def parse_api_documentation(self, url: str, html_content: str, api_info: Dict) -> Optional[Dict[str, Any]]:
        """
        使用大模型解析API文档
        
        Args:
            url: API文档URL
            html_content: HTML内容
            api_info: 从URL推断的API信息
            
        Returns:
            解析后的API信息，如果解析失败则返回None
        """
        # 构建提示词
        prompt = f"""
        请分析以下飞书API文档页面，提取API的详细信息。

URL: {url}
API路径: {api_info.get('path', '未知')}
HTTP方法: {api_info.get('method', '未知')}

页面内容:
{html_content[:4000]}  # 进一步限制长度避免token过多

请提取以下信息，以JSON格式返回：
{{
    "summary": "API摘要",
    "description": "API详细描述",
    "parameters": [
        {{
            "name": "参数名",
            "in": "path/query/header",
            "required": true/false,
            "type": "string/integer/object/array",
            "description": "参数描述"
        }}
    ],
    "request_body": {{
        "required": true/false,
        "content": {{
            "application/json": {{
                "schema": {{
                    "type": "object",
                    "properties": {{
                        "字段名": {{
                            "type": "string/integer/object/array",
                            "description": "字段描述"
                        }}
                    }}
                }}
            }}
        }}
    }},
    "responses": {{
        "200": {{
            "description": "成功响应",
            "content": {{
                "application/json": {{
                    "schema": {{
                        "type": "object",
                        "properties": {{
                            "code": {{
                                "type": "integer",
                                "description": "错误码，0表示成功"
                            }},
                            "msg": {{
                                "type": "string",
                                "description": "错误信息"
                            }},
                            "data": {{
                                "type": "object",
                                "description": "响应数据"
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }},
    "security": [
        {{
            "type": "oauth2",
            "description": "需要OAuth2认证"
        }}
    ]
}}

注意：
1. 如果某些信息在页面中不存在，请根据API类型和常见模式进行合理推断
2. 确保返回的是有效的JSON格式
3. 根据URL中的API类型推断可能的参数和响应结构
"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的API文档解析助手，擅长从飞书API文档中提取结构化的API信息。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用API
        response = self._make_api_request(messages)
        
        if not response:
            ERROR.logger.error("调用大模型API失败")
            return None
            
        try:
            # 提取响应内容
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 尝试解析JSON
            try:
                result = json.loads(content)
                INFO.logger.info("使用大模型成功解析API文档")
                return result
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分
                import re
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                    INFO.logger.info("使用大模型成功解析API文档（提取JSON部分）")
                    return result
                else:
                    # 如果还是失败，尝试查找{...}模式
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                        INFO.logger.info("使用大模型成功解析API文档（查找JSON模式）")
                        return result
                    else:
                        ERROR.logger.error(f"无法从大模型响应中提取有效的JSON: {content}")
                        return None
                        
        except Exception as e:
            ERROR.logger.error(f"解析大模型响应失败: {str(e)}")
            return None
    
    def parse_api_documentation_with_fallback(self, url: str = "", html_content: str = "", api_info: Dict = None) -> Optional[Dict[str, Any]]:
        """
        使用文本解析来解析API文档
        
        Args:
            url: API文档URL
            html_content: HTML内容（用于文本解析）
            api_info: 从URL推断的API信息
            
        Returns:
            解析后的API信息，如果失败则返回None
        """
        if api_info is None:
            api_info = {}
        
        # 尝试文本解析（如果提供了HTML内容）
        if html_content:
            INFO.logger.info("尝试使用文本模型解析API文档")
            text_result = self.parse_api_documentation(url, html_content, api_info)
            if text_result:
                INFO.logger.info("文本解析成功")
                return text_result
            else:
                ERROR.logger.error("文本解析失败")
        
        # 如果没有提供HTML内容，提供错误信息
        if not html_content:
            ERROR.logger.error("没有提供HTML内容，无法进行解析")
        
        return None
    
    def generate_text(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        生成文本响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词，可选
            
        Returns:
            生成的文本响应，如果失败则返回None
        """
        messages = []
        
        # 添加系统提示词（如果提供）
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加用户提示词
        messages.append({"role": "user", "content": prompt})
        
        # 调用API
        response = self._make_api_request(messages)
        
        if not response:
            ERROR.logger.error("调用大模型API失败")
            return None
            
        try:
            # 提取响应内容
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
        except Exception as e:
            ERROR.logger.error(f"提取大模型响应内容失败: {str(e)}")
            return None
    
    def _get_api_type_from_url(self, url: str) -> str:
        """
        从URL中推断API类型
        
        Args:
            url: API文档URL
            
        Returns:
            API类型字符串
        """
        url_lower = url.lower() if url else ""
        
        if "feishu" in url_lower or "open.feishu" in url_lower:
            return "feishu"
        elif "openai" in url_lower:
            return "openai"
        elif "github" in url_lower:
            return "github"
        elif "baidu" in url_lower:
            return "baidu"
        elif "tencent" in url_lower:
            return "tencent"
        else:
            return "unknown"