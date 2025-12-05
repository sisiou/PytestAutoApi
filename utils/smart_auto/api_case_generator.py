"""
API用例生成器模块

该模块负责根据API文档生成测试用例，支持多种测试场景和测试类型。
"""

import json
import logging
from typing import Dict, List, Any, Optional
import requests
from utils.smart_auto.ai_client import AIClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APICaseGenerator:
    """API用例生成器"""
    
    def __init__(self, openapi_spec):
        """
        初始化API用例生成器
        
        Args:
            openapi_spec: OpenAPI规范文档内容，可以是JSON字符串或字典对象
        """
        # 处理不同类型的输入
        if isinstance(openapi_spec, str):
            self.openapi_spec = openapi_spec
        elif isinstance(openapi_spec, dict):
            self.openapi_spec = json.dumps(openapi_spec)
        else:
            raise ValueError("openapi_spec必须是字符串或字典对象")
            
        self.ai_client = AIClient()
    
    def generate_test_scenes(self) -> List[Dict[str, Any]]:
        """
        生成测试场景
        
        Returns:
            测试场景列表
        """
        try:
            # 构建提示词
            prompt = f"""
[角色描述]
你是一个API测试场景分析工具，请你根据以下我提供的OpenAPI规范文档，分析出这些API的主要测试场景。
[OpenAPI规范文档]
{self.openapi_spec}
[输出格式]
请返回JSON格式的测试场景列表，每个场景包含以下字段：
- scene_id: 场景ID
- scene_name: 场景名称
- description: 场景描述
- api_endpoints: 涉及的API端点列表
- test_points: 测试点列表
"""
            
            # 调用AI生成测试场景
            response = self.ai_client.generate_text(prompt)
            
            # 检查响应是否为None或空
            if response is None or not response.strip():
                logger.warning("AI返回了空响应")
                return self._fallback_generate_test_scenes()
            
            logger.info(f"AI响应长度: {len(response)}")
            logger.info(f"AI响应前100个字符: {response[:100]}")
            
            # 尝试解析JSON响应
            try:
                # 首先尝试直接解析
                scenes = json.loads(response)
                if isinstance(scenes, list):
                    logger.info(f"直接解析成功，场景数量: {len(scenes)}")
                    return scenes
                elif isinstance(scenes, dict):
                    # 尝试多种可能的键名
                    for key in ['scenes', 'test_scenarios', 'scenarios', 'test_scenes']:
                        if key in scenes and isinstance(scenes[key], list):
                            logger.info(f"解析为字典，使用键'{key}'，场景数量: {len(scenes[key])}")
                            return scenes[key]
                    
                    logger.warning(f"AI返回的字典格式不符合预期，包含的键: {list(scenes.keys())}")
                    return self._fallback_generate_test_scenes()
                else:
                    logger.warning(f"AI返回的格式不符合预期: {type(scenes)}")
                    return self._fallback_generate_test_scenes()
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试从markdown代码块中提取JSON
                try:
                    import re
                    # 查找JSON代码块，尝试多种模式
                    patterns = [
                        r'```json\s*(.*?)\s*```',
                        r'```\s*(.*?)\s*```',
                        r'```json\s*\n(.*?)\n```'
                    ]
                    
                    json_str = None
                    for pattern in patterns:
                        json_match = re.search(pattern, response, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            break
                    
                    if json_str:
                        logger.info(f"从代码块提取JSON成功，JSON长度: {len(json_str)}")
                        scenes = json.loads(json_str)
                        if isinstance(scenes, list):
                            logger.info(f"解析为列表，场景数量: {len(scenes)}")
                            return scenes
                        elif isinstance(scenes, dict):
                            # 尝试多种可能的键名
                            for key in ['scenes', 'test_scenarios', 'scenarios', 'test_scenes']:
                                if key in scenes and isinstance(scenes[key], list):
                                    logger.info(f"解析为字典，使用键'{key}'，场景数量: {len(scenes[key])}")
                                    return scenes[key]
                            
                            logger.warning(f"AI返回的字典格式不符合预期，包含的键: {list(scenes.keys())}")
                            return self._fallback_generate_test_scenes()
                        else:
                            logger.warning(f"AI返回的不是预期的格式: {type(scenes)}")
                            return self._fallback_generate_test_scenes()
                    else:
                        logger.warning(f"AI返回的不是有效的JSON: {response}")
                        return self._fallback_generate_test_scenes()
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"AI返回的不是有效的JSON: {response}, 错误: {str(e)}")
                    return self._fallback_generate_test_scenes()
                
        except Exception as e:
            logger.error(f"生成测试场景失败: {str(e)}")
            return self._fallback_generate_test_scenes()
    
    def _fallback_generate_test_scenes(self) -> List[Dict[str, Any]]:
        """
        备用测试场景生成方法
        
        Returns:
            默认测试场景列表
        """
        try:
            # 尝试解析OpenAPI文档
            if isinstance(self.openapi_spec, str):
                openapi_data = json.loads(self.openapi_spec)
            else:
                openapi_data = self.openapi_spec
                
            # 获取API端点信息
            apis = []
            
            # 尝试从标准OpenAPI格式获取
            paths = openapi_data.get('paths', {})
            if paths:
                for path, path_item in paths.items():
                    for method, operation in path_item.items():
                        if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                            apis.append({
                                'method': method.upper(),
                                'path': path,
                                'summary': operation.get('summary', ''),
                                'description': operation.get('description', ''),
                                'operationId': operation.get('operationId', '')
                            })
            
            # 尝试从自定义格式获取
            if not apis:
                apis_data = openapi_data.get('apis', [])
                if apis_data:
                    apis = apis_data
            
            # 尝试从endpoints字段获取
            if not apis:
                endpoints_data = openapi_data.get('endpoints', [])
                if endpoints_data:
                    apis = endpoints_data
            
            scenes = []
            scene_id = 1
            
            # 为每个API端点创建基本场景
            for api in apis:
                method = api.get('method', 'GET')
                path = api.get('path', '/')
                summary = api.get('summary', api.get('description', ''))
                
                scene_name = f"{method} {path}"
                description = summary or f"{method} {path}的测试场景"
                
                scene = {
                    'scene_id': f'scene_{scene_id}',
                    'scene_name': scene_name,
                    'description': description,
                    'api_endpoints': [f"{method} {path}"],
                    'test_points': [
                        '正常流程测试',
                        '参数验证测试',
                        '权限验证测试'
                    ]
                }
                
                scenes.append(scene)
                scene_id += 1
            
            return scenes
            
        except Exception as e:
            logger.error(f"备用测试场景生成失败: {str(e)}")
            # 返回一个默认场景
            return [{
                'scene_id': 'scene_default',
                'scene_name': '默认测试场景',
                'description': '默认API测试场景',
                'api_endpoints': [],
                'test_points': ['基本功能测试']
            }]
    
    def generate_test_cases(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据测试场景生成测试用例
        
        Args:
            scenes: 测试场景列表
            
        Returns:
            测试用例列表
        """
        test_cases = []
        
        for scene in scenes:
            scene_id = scene.get('scene_id', '')
            scene_name = scene.get('scene_name', '')
            api_endpoints = scene.get('api_endpoints', [])
            test_points = scene.get('test_points', [])
            
            for test_point in test_points:
                test_case = {
                    'case_id': f"{scene_id}_{test_point}",
                    'case_name': f"{scene_name} - {test_point}",
                    'scene_id': scene_id,
                    'test_point': test_point,
                    'api_endpoints': api_endpoints,
                    'test_steps': self._generate_test_steps(api_endpoints, test_point),
                    'expected_results': self._generate_expected_results(test_point)
                }
                
                test_cases.append(test_case)
        
        return test_cases
    
    def _generate_test_steps(self, api_endpoints: List[Any], test_point: str) -> List[Dict[str, Any]]:
        """
        生成测试步骤
        
        Args:
            api_endpoints: API端点列表，可能是字符串列表或对象列表
            test_point: 测试点
            
        Returns:
            测试步骤列表
        """
        steps = []
        
        for endpoint in api_endpoints:
            # 处理不同格式的端点
            if isinstance(endpoint, str):
                # 字符串格式: "GET /users"
                parts = endpoint.split(' ', 1)
                if len(parts) != 2:
                    continue
                method, path = parts
            elif isinstance(endpoint, dict):
                # 对象格式: {"method": "GET", "path": "/users"}
                method = endpoint.get('method', 'GET')
                path = endpoint.get('path', '/')
            else:
                continue
                
            step = {
                'step_id': f"step_{len(steps) + 1}",
                'action': method.upper(),
                'endpoint': path,
                'description': f"执行{method.upper()}请求到{path}",
                'test_type': test_point
            }
            
            steps.append(step)
        
        return steps
    
    def _generate_expected_results(self, test_point: str) -> List[Dict[str, Any]]:
        """
        生成预期结果
        
        Args:
            test_point: 测试点
            
        Returns:
            预期结果列表
        """
        if test_point == '正常流程测试':
            return [
                {
                    'result_id': 'result_1',
                    'type': 'status_code',
                    'value': 200,
                    'description': '请求成功'
                },
                {
                    'result_id': 'result_2',
                    'type': 'response_time',
                    'value': '< 2000ms',
                    'description': '响应时间小于2秒'
                }
            ]
        elif test_point == '参数验证测试':
            return [
                {
                    'result_id': 'result_1',
                    'type': 'status_code',
                    'value': 400,
                    'description': '无效参数请求返回400错误'
                }
            ]
        elif test_point == '权限验证测试':
            return [
                {
                    'result_id': 'result_1',
                    'type': 'status_code',
                    'value': 401 or 403,
                    'description': '无权限请求返回401或403错误'
                }
            ]
        else:
            return [
                {
                    'result_id': 'result_1',
                    'type': 'status_code',
                    'value': 200,
                    'description': '请求成功'
                }
            ]