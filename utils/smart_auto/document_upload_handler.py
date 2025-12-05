# -*- coding: utf-8 -*-
"""
文档上传处理器
处理上传的OpenAPI文档，使用OpenAPI Agent进行解析
"""

import os
import json
import logging
import yaml
from typing import Dict, Any, Optional

from utils.logging_tool.log_control import INFO, ERROR

# 导入OpenAPI Agent
try:
    from utils.smart_auto.api_agent_integration import create_openapi_agent
    OPENAPI_AGENT_AVAILABLE = True
except ImportError:
    OPENAPI_AGENT_AVAILABLE = False
    INFO.logger.warning("OpenAPI Agent不可用，将使用传统解析器")

# 导入传统解析器
from utils.smart_auto.api_parser import APIParserFactory

logger = logging.getLogger(__name__)


class DocumentUploadHandler:
    """文档上传处理器"""
    
    def __init__(self):
        self.agent = None
        if OPENAPI_AGENT_AVAILABLE:
            try:
                # 加载配置文件
                config_path = os.path.join(os.path.dirname(__file__), 'openapi_agent_config.yaml')
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 获取OpenAI API密钥
                openai_api_key = config.get('openai', {}).get('api_key', '')
                openai_model = config.get('openai', {}).get('model', 'gpt-3.5-turbo')
                base_url = config.get('openai', {}).get('base_url', None)
                
                if not openai_api_key:
                    INFO.logger.warning("OpenAI API密钥未配置，OpenAPI Agent不可用")
                    self.agent = None
                else:
                    self.agent = create_openapi_agent(
                        openai_api_key=openai_api_key, 
                        openai_model=openai_model,
                        base_url=base_url
                    )
                    INFO.logger.info("OpenAPI Agent初始化成功")
            except Exception as e:
                ERROR.logger.error(f"OpenAPI Agent初始化失败: {str(e)}")
                self.agent = None
    
    def is_openapi_agent_available(self) -> bool:
        """检查OpenAPI Agent是否可用"""
        return OPENAPI_AGENT_AVAILABLE and self.agent is not None
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        解析上传的文档
        
        Args:
            file_path: 文档路径
            
        Returns:
            解析结果
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': '文件不存在'
            }
        
        # 优先使用OpenAPI Agent
        if self.is_openapi_agent_available():
            try:
                INFO.logger.info("使用OpenAPI Agent解析文档")
                result = self.agent.parse_openapi(file_path)
                
                if result.get('success', False):
                    # 转换为统一格式
                    api_data = result.get('data', {})
                    return {
                        'success': True,
                        'parser': 'openapi_agent',
                        'info': api_data.get('info', {}),
                        'endpoints': api_data.get('endpoints', []),
                        'models': api_data.get('models', {}),
                        'endpoint_count': len(api_data.get('endpoints', [])),
                        'model_count': len(api_data.get('models', {})),
                        'raw_data': api_data
                    }
                else:
                    ERROR.logger.error(f"OpenAPI Agent解析失败: {result.get('error', '未知错误')}")
                    # 回退到传统解析器
                    return self._parse_with_traditional_parser(file_path)
                    
            except Exception as e:
                ERROR.logger.error(f"OpenAPI Agent解析异常: {str(e)}")
                # 回退到传统解析器
                return self._parse_with_traditional_parser(file_path)
        else:
            # 使用传统解析器
            return self._parse_with_traditional_parser(file_path)
    
    def _parse_with_traditional_parser(self, file_path: str) -> Dict[str, Any]:
        """
        使用传统解析器解析文档
        
        Args:
            file_path: 文档路径
            
        Returns:
            解析结果
        """
        try:
            INFO.logger.info("使用传统解析器解析文档")
            
            # 创建解析器
            parser = APIParserFactory.create_parser(file_path)
            apis = parser.parse_apis()
            
            # 转换为统一格式
            api_list = [api.__dict__ for api in apis]
            
            return {
                'success': True,
                'parser': 'traditional',
                'info': {
                    'title': parser.api_info.get('title', ''),
                    'version': parser.api_info.get('version', ''),
                    'description': parser.api_info.get('description', ''),
                    'host': parser.host,
                    'base_path': parser.base_path
                },
                'endpoints': api_list,
                'models': {},  # 传统解析器不提供模型信息
                'endpoint_count': len(api_list),
                'model_count': 0,
                'raw_data': {
                    'apis': api_list,
                    'info': parser.api_info,
                    'host': parser.host,
                    'base_path': parser.base_path
                }
            }
            
        except Exception as e:
            ERROR.logger.error(f"传统解析器解析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'parser': 'traditional'
            }
    
    def generate_test_cases(self, file_id: str, file_path: str) -> Dict[str, Any]:
        """
        为上传的文档生成测试用例
        
        Args:
            file_id: 文件ID
            file_path: 文件路径
            
        Returns:
            测试用例生成结果
        """
        if self.is_openapi_agent_available():
            try:
                INFO.logger.info(f"使用OpenAPI Agent为文件 {file_id} 生成测试用例")
                result = self.agent.generate_test_cases(file_path)
                
                if result.get('success', False):
                    return {
                        'success': True,
                        'file_id': file_id,
                        'test_cases': result.get('test_cases', []),
                        'test_case_count': len(result.get('test_cases', [])),
                        'parser': 'openapi_agent'
                    }
                else:
                    ERROR.logger.error(f"OpenAPI Agent生成测试用例失败: {result.get('error', '未知错误')}")
                    return {
                        'success': False,
                        'file_id': file_id,
                        'error': result.get('error', '未知错误'),
                        'parser': 'openapi_agent'
                    }
                    
            except Exception as e:
                ERROR.logger.error(f"OpenAPI Agent生成测试用例异常: {str(e)}")
                return {
                    'success': False,
                    'file_id': file_id,
                    'error': str(e),
                    'parser': 'openapi_agent'
                }
        else:
            return {
                'success': False,
                'file_id': file_id,
                'error': 'OpenAPI Agent不可用，无法生成测试用例',
                'parser': 'traditional'
            }
    
    def execute_test_cases(self, file_id: str, test_cases: list, environment: Dict = None) -> Dict[str, Any]:
        """
        执行测试用例
        
        Args:
            file_id: 文件ID
            test_cases: 测试用例列表
            environment: 测试环境配置
            
        Returns:
            测试执行结果
        """
        if self.is_openapi_agent_available():
            try:
                INFO.logger.info(f"使用OpenAPI Agent执行文件 {file_id} 的测试用例")
                result = self.agent.execute_test_cases(test_cases, environment)
                
                if result.get('success', False):
                    return {
                        'success': True,
                        'file_id': file_id,
                        'test_results': result.get('test_results', []),
                        'summary': result.get('summary', {}),
                        'parser': 'openapi_agent'
                    }
                else:
                    ERROR.logger.error(f"OpenAPI Agent执行测试用例失败: {result.get('error', '未知错误')}")
                    return {
                        'success': False,
                        'file_id': file_id,
                        'error': result.get('error', '未知错误'),
                        'parser': 'openapi_agent'
                    }
                    
            except Exception as e:
                ERROR.logger.error(f"OpenAPI Agent执行测试用例异常: {str(e)}")
                return {
                    'success': False,
                    'file_id': file_id,
                    'error': str(e),
                    'parser': 'openapi_agent'
                }
        else:
            return {
                'success': False,
                'file_id': file_id,
                'error': 'OpenAPI Agent不可用，无法执行测试用例',
                'parser': 'traditional'
            }
    
    def analyze_test_results(self, file_id: str, test_results: list) -> Dict[str, Any]:
        """
        分析测试结果
        
        Args:
            file_id: 文件ID
            test_results: 测试结果列表
            
        Returns:
            测试结果分析
        """
        if self.is_openapi_agent_available():
            try:
                INFO.logger.info(f"使用OpenAPI Agent分析文件 {file_id} 的测试结果")
                result = self.agent.analyze_test_results(test_results)
                
                if result.get('success', False):
                    return {
                        'success': True,
                        'file_id': file_id,
                        'analysis': result.get('analysis', {}),
                        'suggestions': result.get('suggestions', []),
                        'parser': 'openapi_agent'
                    }
                else:
                    ERROR.logger.error(f"OpenAPI Agent分析测试结果失败: {result.get('error', '未知错误')}")
                    return {
                        'success': False,
                        'file_id': file_id,
                        'error': result.get('error', '未知错误'),
                        'parser': 'openapi_agent'
                    }
                    
            except Exception as e:
                ERROR.logger.error(f"OpenAPI Agent分析测试结果异常: {str(e)}")
                return {
                    'success': False,
                    'file_id': file_id,
                    'error': str(e),
                    'parser': 'openapi_agent'
                }
        else:
            return {
                'success': False,
                'file_id': file_id,
                'error': 'OpenAPI Agent不可用，无法分析测试结果',
                'parser': 'traditional'
            }
    
    def full_test_workflow(self, file_id: str, file_path: str, test_type: str = "all", 
                          environment: Dict = None) -> Dict[str, Any]:
        """
        执行完整的测试工作流程：解析文档、生成测试用例、执行测试、分析结果
        
        Args:
            file_id: 文件ID
            file_path: 文件路径
            test_type: 测试类型 (all, smoke, regression, etc.)
            environment: 测试环境配置
            
        Returns:
            完整测试工作流程结果
        """
        if self.is_openapi_agent_available():
            try:
                INFO.logger.info("使用OpenAPI Agent执行完整测试工作流程")
                result = self.agent.full_test_workflow(file_path, "url", test_type, environment)
                
                if result.get('success', False):
                    return {
                        'success': True,
                        'file_id': file_id,
                        'test_results': result.get('test_results', {}),
                        'summary': result.get('summary', {}),
                        'parser': 'openapi_agent'
                    }
                else:
                    ERROR.logger.error(f"OpenAPI Agent完整工作流程失败: {result.get('error', '未知错误')}")
                    return {
                        'success': False,
                        'file_id': file_id,
                        'error': result.get('error', '未知错误'),
                        'parser': 'openapi_agent'
                    }
                    
            except Exception as e:
                ERROR.logger.error(f"OpenAPI Agent完整工作流程异常: {str(e)}")
                return {
                    'success': False,
                    'file_id': file_id,
                    'error': str(e),
                    'parser': 'openapi_agent'
                }
        else:
            return {
                'success': False,
                'file_id': file_id,
                'error': 'OpenAPI Agent不可用，无法执行完整测试工作流程',
                'parser': 'traditional'
            }


# 创建全局文档上传处理器实例
document_upload_handler = DocumentUploadHandler()