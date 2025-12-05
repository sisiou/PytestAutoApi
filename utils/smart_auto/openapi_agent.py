# -*- coding: utf-8 -*-
"""
@Time   : 2025/12/04
@Author : Smart Auto Platform
@File   : openapi_agent.py
@Desc   : 基于LangChain的OpenAPI 3.0.0测试智能代理
"""

import os
import json
import yaml
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    NEW_LANGCHAIN = True
except ImportError:
    # 尝试兼容旧版本
    from langchain.agents import AgentExecutor, initialize_agent
    NEW_LANGCHAIN = False
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory

from utils.smart_auto.api_parser import OpenAPIParser
from utils.smart_auto.test_generator import TestCaseGenerator
from utils.smart_auto.dependency_analyzer import DependencyAnalyzer
from utils.smart_auto.assertion_generator import AssertionGenerator
from utils.smart_auto.ai_client import AIClient
from utils.logging_tool.log_control import INFO, ERROR
try:
    from utils.other_tools.exceptions import OpenAPIAgentError
except ImportError:
    # 如果异常类不存在，创建一个简单的
    class OpenAPIAgentError(Exception):
        pass


@dataclass
class TestResult:
    """测试结果数据类"""
    test_case_id: str
    test_case_name: str
    api_path: str
    api_method: str
    status: str  # passed, failed, error
    response_time: float
    status_code: int
    response_data: Dict
    assertion_results: List[Dict]
    error_message: Optional[str] = None


@dataclass
class TestSuiteResult:
    """测试套件结果数据类"""
    suite_id: str
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    execution_time: float
    test_results: List[TestResult]
    coverage_score: float


class OpenAPIAgent:
    """基于LangChain的OpenAPI 3.0.0 API测试智能代理"""
    
    def __init__(self, config_path: str = None):
        """
        初始化OpenAPI代理
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, "configs", "config.yaml")
        
        self.config = self._load_config(config_path)
        
        # 初始化LangChain组件
        # 使用AIClient而不是ChatOpenAI
        self.ai_client = AIClient(config_path)
        
        # 创建一个简单的LLM包装器，兼容LangChain接口
        from langchain.llms.base import LLM
        from typing import Optional, List, Any, Dict, Mapping
        from langchain.schema import Generation, LLMResult
        from pydantic import Field
        
        class SimpleLLM(LLM):
            ai_client: Any = Field(description="AI客户端实例")
            
            def __init__(self, ai_client, **kwargs):
                super().__init__(ai_client=ai_client, **kwargs)
                  
            def _call(self, prompt, stop=None, run_manager=None, **kwargs):
                # 使用ai_client生成文本
                system_prompt = kwargs.get("system_prompt", "你是一个专业的API测试专家。")
                return self.ai_client.generate_text(prompt, system_prompt)
                  
            @property
            def _llm_type(self):
                return "simple_llm"
                  
            @property
            def _identifying_params(self) -> Mapping[str, Any]:
                """Get the identifying parameters."""
                return {"type": "simple_llm"}
        
        self.llm = SimpleLLM(self.ai_client)
        
        # 初始化工具
        self.tools = [
            self.parse_openapi_tool,
            self.generate_test_scene_tool,
            self.generate_test_relation_tool,
            self.generate_test_cases_tool,
            self.execute_test_cases_tool,
            self.analyze_results_tool,
            self.generate_report_tool
        ]
        
        # 对于旧版本LangChain，需要确保工具只有一个输入参数
        if not NEW_LANGCHAIN:
            # 旧版本LangChain不支持多输入工具，需要修改工具定义
            self.tools = [
                self._wrap_tool_for_old_langchain(self.parse_openapi_tool),
                self._wrap_tool_for_old_langchain(self.generate_test_scene_tool),
                self._wrap_tool_for_old_langchain(self.generate_test_relation_tool),
                self._wrap_tool_for_old_langchain(self.generate_test_cases_tool),
                self._wrap_tool_for_old_langchain(self.execute_test_cases_tool),
                self._wrap_tool_for_old_langchain(self.analyze_results_tool),
                self._wrap_tool_for_old_langchain(self.generate_report_tool)
            ]
        
        # 创建提示模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的API测试专家，能够根据OpenAPI 3.0.0文档自动生成测试用例、执行测试并分析结果。你有以下工具可以使用："),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 创建代理
        if NEW_LANGCHAIN:
            self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
            self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        else:
            # 使用旧版本的initialize_agent
            self.agent_executor = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent="zero-shot-react-description",
                verbose=True,
                early_stopping_method="generate"
            )
        
        # 初始化组件
        self.openapi_parser = None
        self.test_generator = None
        self.dependency_analyzer = None
        self.assertion_generator = AssertionGenerator()
        
        # 存储测试结果
        self.test_results = []
        self.current_api_doc = None
        
        INFO.logger.info("OpenAPI Agent初始化完成")
    
    def _wrap_tool_for_old_langchain(self, tool):
        """为旧版本LangChain包装工具，确保只有一个输入参数"""
        def wrapped_tool(input_str):
            # 尝试解析输入为JSON
            try:
                import json
                if input_str.startswith('{') and input_str.endswith('}'):
                    # 如果是JSON字符串，解析为字典
                    input_data = json.loads(input_str)
                    # 调用原始工具
                    return tool.func(**input_data)
                else:
                    # 如果不是JSON，直接作为第一个参数传递
                    return tool.func(input_str)
            except Exception as e:
                # 如果解析失败，直接作为第一个参数传递
                return tool.func(input_str)
        
        # 创建新工具，使用包装后的函数
        from langchain.tools import Tool
        return Tool(
            name=tool.name,
            description=tool.description + "\n输入应为JSON字符串，包含所需参数。",
            func=wrapped_tool
        )
    
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
    
    @tool
    def parse_openapi_tool(self, openapi_url_or_path: str) -> str:
        """
        解析OpenAPI 3.0.0文档
        
        Args:
            openapi_url_or_path: OpenAPI文档URL或本地文件路径
            
        Returns:
            解析后的API信息JSON字符串
        """
        try:
            INFO.logger.info(f"开始解析OpenAPI文档: {openapi_url_or_path}")
            
            # 创建OpenAPI解析器
            self.openapi_parser = OpenAPIParser(openapi_url_or_path)
            
            # 加载并解析API文档
            api_data = self.openapi_parser.load_api_doc()
            apis = self.openapi_parser.parse_apis()
            
            # 转换为字典格式以便JSON序列化
            apis_dict = []
            for api in apis:
                api_dict = {
                    "path": api.path,
                    "method": api.method,
                    "summary": api.summary,
                    "description": api.description,
                    "operation_id": api.operation_id,
                    "tags": api.tags,
                    "host": api.host,
                    "base_path": api.base_path,
                    "parameters": api.parameters,
                    "request_body": api.request_body,
                    "response_codes": api.response_codes,
                    "success_response": api.success_response,
                    "security": api.security
                }
                apis_dict.append(api_dict)
            
            # 存储当前API文档信息
            self.current_api_doc = {
                "api_info": self.openapi_parser.api_info,
                "host": self.openapi_parser.host,
                "base_path": self.openapi_parser.base_path,
                "apis": apis_dict
            }
            
            result = {
                "status": "success",
                "message": f"成功解析OpenAPI文档，共发现 {len(apis)} 个API接口",
                "api_info": self.openapi_parser.api_info,
                "total_apis": len(apis)
            }
            
            INFO.logger.info(f"OpenAPI文档解析完成，共发现 {len(apis)} 个API接口")
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"解析OpenAPI文档失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"解析OpenAPI文档失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    @tool
    def generate_test_scene_tool(self, api_doc: str, use_llm: bool = False) -> str:
        """
        根据OpenAPI 3.0.0文档生成测试场景
        
        Args:
            api_doc: OpenAPI 3.0.0文档的JSON字符串或YAML字符串
            use_llm: 是否使用大模型增强测试场景生成，默认为False
            
        Returns:
            生成的测试场景信息JSON字符串
        """
        try:
            INFO.logger.info("开始生成测试场景...")
            
            # 解析API文档
            if isinstance(api_doc, str):
                try:
                    # 尝试解析为JSON
                    doc_data = json.loads(api_doc)
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试解析为YAML
                    try:
                        doc_data = yaml.safe_load(api_doc)
                    except yaml.YAMLError:
                        return json.dumps({
                            "status": "error",
                            "message": "API文档格式不正确，应为有效的JSON或YAML格式"
                        }, ensure_ascii=False)
            
            # 提取API信息
            paths = doc_data.get('paths', {})
            info = doc_data.get('info', {})
            
            # 分析API并生成测试场景
            test_scenes = []
            business_flows = []
            
            # 1. 基础功能场景
            basic_scenes = self._generate_basic_test_scenes(paths, info)
            test_scenes.extend(basic_scenes)
            
            # 2. 业务流程场景
            business_flows = self._generate_business_flow_scenes(paths, info)
            test_scenes.extend(business_flows)
            
            # 3. 边界值场景
            boundary_scenes = self._generate_boundary_test_scenes(paths, info)
            test_scenes.extend(boundary_scenes)
            
            # 4. 安全性场景
            security_scenes = self._generate_security_test_scenes(paths, info)
            test_scenes.extend(security_scenes)
            
            # 5. 性能场景
            performance_scenes = self._generate_performance_test_scenes(paths, info)
            test_scenes.extend(performance_scenes)
            
            # 6. 兼容性场景
            compatibility_scenes = self._generate_compatibility_test_scenes(paths, info)
            test_scenes.extend(compatibility_scenes)
            
            # 如果使用LLM增强测试场景
            if use_llm and self.ai_client.is_available():
                try:
                    llm_enhanced_scenes = self._enhance_test_scenes_with_llm(test_scenes, doc_data)
                    if llm_enhanced_scenes:
                        test_scenes = llm_enhanced_scenes
                except Exception as e:
                    ERROR.logger.warning(f"LLM增强测试场景失败，使用基础场景: {str(e)}")
            
            result = {
                "status": "success",
                "message": f"成功生成 {len(test_scenes)} 个测试场景",
                "test_scenes": test_scenes,
                "business_flows": business_flows
            }
            
            INFO.logger.info(f"测试场景生成完成，共生成 {len(test_scenes)} 个测试场景")
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"生成测试场景失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"生成测试场景失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    def _generate_basic_test_scenes(self, paths: Dict, info: Dict) -> List[Dict]:
        """生成基础功能测试场景"""
        basic_scenes = []
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    scene = {
                        "name": f"基础{method.upper()}测试 - {path}",
                        "description": f"测试{method.upper()} {path}的基础功能",
                        "type": "basic",
                        "path": path,
                        "method": method.upper(),
                        "priority": "high",
                        "tags": operation.get('tags', []),
                        "test_points": [
                            "正常请求响应",
                            "必填参数验证",
                            "可选参数测试"
                        ]
                    }
                    basic_scenes.append(scene)
        
        return basic_scenes
    
    def _generate_business_flow_scenes(self, paths: Dict, info: Dict) -> List[Dict]:
        """生成业务流程测试场景"""
        business_flows = []
        
        # 分析API之间的依赖关系
        dependencies = self._analyze_api_dependencies(paths)
        
        # 根据依赖关系生成业务流程
        for flow_name, flow_apis in dependencies.items():
            flow = {
                "name": flow_name,
                "description": f"测试{flow_name}的完整业务流程",
                "type": "business_flow",
                "apis": flow_apis,
                "priority": "high",
                "test_points": [
                    "流程完整性测试",
                    "状态一致性验证",
                    "数据传递正确性"
                ]
            }
            business_flows.append(flow)
        
        return business_flows
    
    def _generate_boundary_test_scenes(self, paths: Dict, info: Dict) -> List[Dict]:
        """生成边界值测试场景"""
        boundary_scenes = []
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    # 分析参数边界
                    parameters = operation.get('parameters', [])
                    if parameters:
                        scene = {
                            "name": f"边界值测试 - {method.upper()} {path}",
                            "description": f"测试{method.upper()} {path}的参数边界值",
                            "type": "boundary",
                            "path": path,
                            "method": method.upper(),
                            "priority": "medium",
                            "test_points": [
                                "参数最大值测试",
                                "参数最小值测试",
                                "参数为空测试",
                                "参数格式错误测试"
                            ]
                        }
                        boundary_scenes.append(scene)
        
        return boundary_scenes
    
    def _generate_security_test_scenes(self, paths: Dict, info: Dict) -> List[Dict]:
        """生成安全性测试场景"""
        security_scenes = []
        
        # 检查是否有认证要求
        has_security = False
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    if operation.get('security'):
                        has_security = True
                        break
            if has_security:
                break
        
        if has_security:
            scene = {
                "name": "安全性测试 - 认证授权",
                "description": "测试API的认证和授权机制",
                "type": "security",
                "priority": "high",
                "test_points": [
                    "无认证访问测试",
                    "无效token测试",
                    "权限不足测试",
                    "token过期测试"
                ]
            }
            security_scenes.append(scene)
        
        return security_scenes
    
    def _generate_performance_test_scenes(self, paths: Dict, info: Dict) -> List[Dict]:
        """生成性能测试场景"""
        performance_scenes = []
        
        # 选择关键API进行性能测试
        critical_apis = []
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    # 优先选择GET和POST接口进行性能测试
                    if method.upper() in ['GET', 'POST']:
                        critical_apis.append((path, method.upper()))
        
        if critical_apis:
            scene = {
                "name": "性能测试 - 关键API",
                "description": "测试关键API的性能表现",
                "type": "performance",
                "priority": "medium",
                "apis": critical_apis[:5],  # 限制为前5个关键API
                "test_points": [
                    "响应时间测试",
                    "并发访问测试",
                    "压力测试"
                ]
            }
            performance_scenes.append(scene)
        
        return performance_scenes
    
    def _generate_compatibility_test_scenes(self, paths: Dict, info: Dict) -> List[Dict]:
        """生成兼容性测试场景"""
        compatibility_scenes = []
        
        # 检查API版本兼容性
        version = info.get('version', '')
        if version:
            scene = {
                "name": f"兼容性测试 - 版本 {version}",
                "description": f"测试API版本 {version} 的兼容性",
                "type": "compatibility",
                "priority": "low",
                "test_points": [
                    "版本兼容性测试",
                    "向后兼容性测试",
                    "数据格式兼容性测试"
                ]
            }
            compatibility_scenes.append(scene)
        
        return compatibility_scenes
    
    def _analyze_api_dependencies(self, paths: Dict) -> Dict[str, List[Dict]]:
        """分析API之间的依赖关系"""
        dependencies = {}
        
        # 简单的依赖关系分析
        # 实际项目中可能需要更复杂的分析逻辑
        post_apis = []
        get_apis = []
        put_apis = []
        delete_apis = []
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() == 'POST':
                    post_apis.append({"path": path, "method": method.upper()})
                elif method.upper() == 'GET':
                    get_apis.append({"path": path, "method": method.upper()})
                elif method.upper() == 'PUT':
                    put_apis.append({"path": path, "method": method.upper()})
                elif method.upper() == 'DELETE':
                    delete_apis.append({"path": path, "method": method.upper()})
        
        # 生成常见的业务流程
        if post_apis and get_apis:
            dependencies["创建-查询流程"] = post_apis[:1] + get_apis[:1]
        
        if post_apis and put_apis:
            dependencies["创建-更新流程"] = post_apis[:1] + put_apis[:1]
        
        if post_apis and delete_apis:
            dependencies["创建-删除流程"] = post_apis[:1] + delete_apis[:1]
        
        return dependencies
    
    def _enhance_test_scenes_with_llm(self, test_scenes: List[Dict], doc_data: Dict) -> Optional[List[Dict]]:
        """使用LLM增强测试场景"""
        try:
            # 构建提示
            prompt = f"""
            请基于以下OpenAPI 3.0.0文档，增强以下测试场景，添加更多有价值的测试点：
            
            API文档信息：
            {json.dumps(doc_data, ensure_ascii=False)}
            
            当前测试场景：
            {json.dumps(test_scenes, ensure_ascii=False)}
            
            请返回增强后的测试场景，保持JSON格式。
            """
            
            # 调用AI客户端
            response = self.ai_client.chat_completion(prompt)
            
            if response and response.get('success'):
                enhanced_scenes_text = response.get('content', '')
                try:
                    enhanced_scenes = json.loads(enhanced_scenes_text)
                    if isinstance(enhanced_scenes, list):
                        return enhanced_scenes
                except json.JSONDecodeError:
                    ERROR.logger.warning("LLM返回的增强测试场景格式不正确")
            
            return None
            
        except Exception as e:
            ERROR.logger.error(f"LLM增强测试场景失败: {str(e)}")
            return None
    
    @tool
    def generate_test_relation_tool(self, test_scenes: str) -> str:
        """
        生成测试场景之间的关系图
        
        Args:
            test_scenes: 测试场景的JSON字符串
            
        Returns:
            测试场景关系图的JSON字符串
        """
        try:
            INFO.logger.info("开始生成测试场景关系图...")
            
            # 解析测试场景
            scenes_data = json.loads(test_scenes)
            test_scenes_list = scenes_data.get('test_scenes', [])
            
            # 分析场景之间的关系
            relations = []
            scene_map = {scene['name']: scene for scene in test_scenes_list}
            
            # 基于API路径和方法分析关系
            for i, scene1 in enumerate(test_scenes_list):
                for j, scene2 in enumerate(test_scenes_list):
                    if i >= j:  # 避免重复和自关联
                        continue
                    
                    # 同一API的不同测试类型
                    if (scene1.get('path') == scene2.get('path') and 
                        scene1.get('method') == scene2.get('method')):
                        relation = {
                            "source": scene1['name'],
                            "target": scene2['name'],
                            "type": "same_api",
                            "description": f"同一API {scene1.get('method')} {scene1.get('path')} 的不同测试类型"
                        }
                        relations.append(relation)
                    
                    # 业务流程关系
                    elif (scene1.get('type') == 'business_flow' and 
                          scene2.get('type') == 'business_flow'):
                        # 检查是否有共同的API
                        apis1 = set(api.get('path') for api in scene1.get('apis', []))
                        apis2 = set(api.get('path') for api in scene2.get('apis', []))
                        
                        if apis1.intersection(apis2):
                            relation = {
                                "source": scene1['name'],
                                "target": scene2['name'],
                                "type": "shared_api",
                                "description": "业务流程共享API"
                            }
                            relations.append(relation)
            
            # 构建关系图数据
            graph_data = {
                "nodes": [
                    {
                        "id": scene['name'],
                        "name": scene['name'],
                        "type": scene.get('type', 'unknown'),
                        "priority": scene.get('priority', 'medium'),
                        "description": scene.get('description', ''),
                        "path": scene.get('path', ''),
                        "method": scene.get('method', '')
                    }
                    for scene in test_scenes_list
                ],
                "edges": relations
            }
            
            result = {
                "status": "success",
                "message": f"成功生成测试场景关系图，包含 {len(test_scenes_list)} 个节点和 {len(relations)} 条边",
                "graph_data": graph_data
            }
            
            INFO.logger.info(f"测试场景关系图生成完成")
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"生成测试场景关系图失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"生成测试场景关系图失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    @tool
    def generate_test_cases_tool(self, test_scenes: str, api_doc: str) -> str:
        """
        根据测试场景和API文档生成测试用例
        
        Args:
            test_scenes: 测试场景的JSON字符串
            api_doc: API文档的JSON字符串
            
        Returns:
            生成的测试用例的JSON字符串
        """
        try:
            INFO.logger.info("开始生成测试用例...")
            
            # 解析测试场景和API文档
            scenes_data = json.loads(test_scenes)
            doc_data = json.loads(api_doc)
            
            test_scenes_list = scenes_data.get('test_scenes', [])
            paths = doc_data.get('paths', {})
            
            # 初始化测试用例生成器
            if not self.test_generator:
                self.test_generator = TestCaseGenerator()
            
            # 为每个测试场景生成测试用例
            all_test_cases = []
            
            for scene in test_scenes_list:
                scene_type = scene.get('type', 'basic')
                scene_path = scene.get('path', '')
                scene_method = scene.get('method', '')
                
                # 获取对应的API定义
                api_definition = None
                if scene_path and scene_method and scene_path in paths:
                    api_definition = paths[scene_path].get(scene_method.lower(), {})
                
                # 根据场景类型生成测试用例
                if scene_type == 'basic':
                    test_cases = self._generate_basic_test_cases(scene, api_definition)
                elif scene_type == 'business_flow':
                    test_cases = self._generate_business_flow_test_cases(scene, api_definition)
                elif scene_type == 'boundary':
                    test_cases = self._generate_boundary_test_cases(scene, api_definition)
                elif scene_type == 'security':
                    test_cases = self._generate_security_test_cases(scene, api_definition)
                elif scene_type == 'performance':
                    test_cases = self._generate_performance_test_cases(scene, api_definition)
                elif scene_type == 'compatibility':
                    test_cases = self._generate_compatibility_test_cases(scene, api_definition)
                else:
                    test_cases = []
                
                # 添加场景信息到测试用例
                for test_case in test_cases:
                    test_case['scene_name'] = scene['name']
                    test_case['scene_type'] = scene_type
                    test_case['scene_priority'] = scene.get('priority', 'medium')
                
                all_test_cases.extend(test_cases)
            
            # 使用LLM增强测试用例（如果可用）
            if self.ai_client.is_available():
                try:
                    enhanced_test_cases = self._enhance_test_cases_with_llm(all_test_cases, doc_data)
                    if enhanced_test_cases:
                        all_test_cases = enhanced_test_cases
                except Exception as e:
                    ERROR.logger.warning(f"LLM增强测试用例失败，使用基础测试用例: {str(e)}")
            
            result = {
                "status": "success",
                "message": f"成功生成 {len(all_test_cases)} 个测试用例",
                "test_cases": all_test_cases,
                "test_suites": self._group_test_cases_by_suite(all_test_cases)
            }
            
            INFO.logger.info(f"测试用例生成完成，共生成 {len(all_test_cases)} 个测试用例")
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"生成测试用例失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"生成测试用例失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    def _generate_basic_test_cases(self, scene: Dict, api_definition: Dict) -> List[Dict]:
        """生成基础功能测试用例"""
        test_cases = []
        path = scene.get('path', '')
        method = scene.get('method', '')
        
        # 正常请求测试用例
        normal_case = {
            "name": f"正常请求 - {method} {path}",
            "description": f"测试{method} {path}的正常请求功能",
            "type": "normal",
            "priority": "high",
            "path": path,
            "method": method,
            "headers": {},
            "params": {},
            "body": {},
            "expected_status": 200,
            "assertions": [
                {"type": "status_code", "value": 200},
                {"type": "response_time", "value": 5000}  # 5秒内响应
            ]
        }
        
        # 添加API定义中的参数
        if api_definition:
            # 处理查询参数
            for param in api_definition.get('parameters', []):
                if param.get('in') == 'query':
                    param_name = param.get('name')
                    param_schema = param.get('schema', {})
                    param_type = param_schema.get('type', 'string')
                    
                    # 根据参数类型设置默认值
                    if param_type == 'string':
                        default_value = "test"
                    elif param_type == 'integer':
                        default_value = 1
                    elif param_type == 'boolean':
                        default_value = True
                    else:
                        default_value = None
                    
                    if default_value is not None:
                        normal_case["params"][param_name] = default_value
                
                # 处理头部参数
                elif param.get('in') == 'header':
                    param_name = param.get('name')
                    normal_case["headers"][param_name] = "test"
            
            # 处理请求体
            request_body = api_definition.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    # 简单的请求体生成
                    if schema.get('type') == 'object':
                        normal_case["headers"]["Content-Type"] = "application/json"
                        normal_case["body"] = {"test": "value"}
        
        test_cases.append(normal_case)
        
        # 必填参数验证测试用例
        required_params_case = {
            "name": f"必填参数验证 - {method} {path}",
            "description": f"测试{method} {path}的必填参数验证",
            "type": "required_params",
            "priority": "high",
            "path": path,
            "method": method,
            "headers": {},
            "params": {},
            "body": {},
            "expected_status": 400,  # 期望返回400错误
            "assertions": [
                {"type": "status_code", "value": 400}
            ]
        }
        
        test_cases.append(required_params_case)
        
        return test_cases
    
    def _generate_business_flow_test_cases(self, scene: Dict, api_definition: Dict) -> List[Dict]:
        """生成业务流程测试用例"""
        test_cases = []
        apis = scene.get('apis', [])
        
        for i, api in enumerate(apis):
            path = api.get('path', '')
            method = api.get('method', '')
            
            # 业务流程中的每个API测试用例
            flow_case = {
                "name": f"业务流程步骤{i+1} - {method} {path}",
                "description": f"测试业务流程中的第{i+1}步：{method} {path}",
                "type": "business_flow",
                "priority": "high",
                "path": path,
                "method": method,
                "headers": {},
                "params": {},
                "body": {},
                "expected_status": 200,
                "assertions": [
                    {"type": "status_code", "value": 200},
                    {"type": "response_time", "value": 5000}
                ],
                "flow_step": i + 1,
                "total_steps": len(apis)
            }
            
            test_cases.append(flow_case)
        
        return test_cases
    
    def _generate_boundary_test_cases(self, scene: Dict, api_definition: Dict) -> List[Dict]:
        """生成边界值测试用例"""
        test_cases = []
        path = scene.get('path', '')
        method = scene.get('method', '')
        
        # 参数最大值测试
        max_value_case = {
            "name": f"参数最大值测试 - {method} {path}",
            "description": f"测试{method} {path}的参数最大值",
            "type": "boundary_max",
            "priority": "medium",
            "path": path,
            "method": method,
            "headers": {},
            "params": {},
            "body": {},
            "expected_status": 200,
            "assertions": [
                {"type": "status_code", "value": 200}
            ]
        }
        
        # 参数最小值测试
        min_value_case = {
            "name": f"参数最小值测试 - {method} {path}",
            "description": f"测试{method} {path}的参数最小值",
            "type": "boundary_min",
            "priority": "medium",
            "path": path,
            "method": method,
            "headers": {},
            "params": {},
            "body": {},
            "expected_status": 200,
            "assertions": [
                {"type": "status_code", "value": 200}
            ]
        }
        
        # 参数为空测试
        empty_value_case = {
            "name": f"参数为空测试 - {method} {path}",
            "description": f"测试{method} {path}的参数为空",
            "type": "boundary_empty",
            "priority": "medium",
            "path": path,
            "method": method,
            "headers": {},
            "params": {},
            "body": {},
            "expected_status": 400,  # 期望返回400错误
            "assertions": [
                {"type": "status_code", "value": 400}
            ]
        }
        
        # 参数格式错误测试
        invalid_format_case = {
            "name": f"参数格式错误测试 - {method} {path}",
            "description": f"测试{method} {path}的参数格式错误",
            "type": "boundary_invalid",
            "priority": "medium",
            "path": path,
            "method": method,
            "headers": {},
            "params": {},
            "body": {},
            "expected_status": 400,  # 期望返回400错误
            "assertions": [
                {"type": "status_code", "value": 400}
            ]
        }
        
        test_cases.extend([
            max_value_case,
            min_value_case,
            empty_value_case,
            invalid_format_case
        ])
        
        return test_cases
    
    def _generate_security_test_cases(self, scene: Dict, api_definition: Dict) -> List[Dict]:
        """生成安全性测试用例"""
        test_cases = []
        
        # 无认证访问测试
        no_auth_case = {
            "name": "无认证访问测试",
            "description": "测试无认证情况下的API访问",
            "type": "security_no_auth",
            "priority": "high",
            "headers": {},  # 不包含认证信息
            "expected_status": 401,  # 期望返回401未授权
            "assertions": [
                {"type": "status_code", "value": 401}
            ]
        }
        
        # 无效token测试
        invalid_token_case = {
            "name": "无效token测试",
            "description": "测试使用无效token的API访问",
            "type": "security_invalid_token",
            "priority": "high",
            "headers": {
                "Authorization": "Bearer invalid_token"
            },
            "expected_status": 401,  # 期望返回401未授权
            "assertions": [
                {"type": "status_code", "value": 401}
            ]
        }
        
        # 权限不足测试
        insufficient_permission_case = {
            "name": "权限不足测试",
            "description": "测试权限不足情况下的API访问",
            "type": "security_insufficient_permission",
            "priority": "high",
            "headers": {
                "Authorization": "Bearer low_permission_token"
            },
            "expected_status": 403,  # 期望返回403禁止访问
            "assertions": [
                {"type": "status_code", "value": 403}
            ]
        }
        
        # token过期测试
        expired_token_case = {
            "name": "token过期测试",
            "description": "测试token过期情况下的API访问",
            "type": "security_expired_token",
            "priority": "high",
            "headers": {
                "Authorization": "Bearer expired_token"
            },
            "expected_status": 401,  # 期望返回401未授权
            "assertions": [
                {"type": "status_code", "value": 401}
            ]
        }
        
        test_cases.extend([
            no_auth_case,
            invalid_token_case,
            insufficient_permission_case,
            expired_token_case
        ])
        
        return test_cases
    
    def _generate_performance_test_cases(self, scene: Dict, api_definition: Dict) -> List[Dict]:
        """生成性能测试用例"""
        test_cases = []
        apis = scene.get('apis', [])
        
        for api in apis:
            path = api.get('path', '')
            method = api.get('method', '')
            
            # 响应时间测试
            response_time_case = {
                "name": f"响应时间测试 - {method} {path}",
                "description": f"测试{method} {path}的响应时间",
                "type": "performance_response_time",
                "priority": "medium",
                "path": path,
                "method": method,
                "headers": {},
                "params": {},
                "body": {},
                "expected_status": 200,
                "assertions": [
                    {"type": "status_code", "value": 200},
                    {"type": "response_time", "value": 2000}  # 2秒内响应
                ],
                "performance_threshold": {
                    "response_time": 2000,  # 2秒
                    "concurrent_users": 10
                }
            }
            
            # 并发访问测试
            concurrent_case = {
                "name": f"并发访问测试 - {method} {path}",
                "description": f"测试{method} {path}的并发访问能力",
                "type": "performance_concurrent",
                "priority": "medium",
                "path": path,
                "method": method,
                "headers": {},
                "params": {},
                "body": {},
                "expected_status": 200,
                "assertions": [
                    {"type": "status_code", "value": 200}
                ],
                "performance_threshold": {
                    "concurrent_users": 50,
                    "success_rate": 95  # 95%成功率
                }
            }
            
            # 压力测试
            stress_case = {
                "name": f"压力测试 - {method} {path}",
                "description": f"测试{method} {path}在高负载下的表现",
                "type": "performance_stress",
                "priority": "medium",
                "path": path,
                "method": method,
                "headers": {},
                "params": {},
                "body": {},
                "expected_status": 200,
                "assertions": [
                    {"type": "status_code", "value": 200}
                ],
                "performance_threshold": {
                    "concurrent_users": 100,
                    "duration": 60,  # 60秒
                    "success_rate": 90  # 90%成功率
                }
            }
            
            test_cases.extend([
                response_time_case,
                concurrent_case,
                stress_case
            ])
        
        return test_cases
    
    def _generate_compatibility_test_cases(self, scene: Dict, api_definition: Dict) -> List[Dict]:
        """生成兼容性测试用例"""
        test_cases = []
        
        # 版本兼容性测试
        version_compatibility_case = {
            "name": "版本兼容性测试",
            "description": "测试API版本兼容性",
            "type": "compatibility_version",
            "priority": "low",
            "headers": {
                "Accept": "application/json",
                "API-Version": "1.0"
            },
            "expected_status": 200,
            "assertions": [
                {"type": "status_code", "value": 200}
            ]
        }
        
        # 向后兼容性测试
        backward_compatibility_case = {
            "name": "向后兼容性测试",
            "description": "测试API向后兼容性",
            "type": "compatibility_backward",
            "priority": "low",
            "headers": {
                "Accept": "application/json"
            },
            "expected_status": 200,
            "assertions": [
                {"type": "status_code", "value": 200}
            ]
        }
        
        # 数据格式兼容性测试
        data_format_compatibility_case = {
            "name": "数据格式兼容性测试",
            "description": "测试API数据格式兼容性",
            "type": "compatibility_data_format",
            "priority": "low",
            "headers": {
                "Accept": "application/xml"  # 请求XML格式
            },
            "expected_status": 200,
            "assertions": [
                {"type": "status_code", "value": 200}
            ]
        }
        
        test_cases.extend([
            version_compatibility_case,
            backward_compatibility_case,
            data_format_compatibility_case
        ])
        
        return test_cases
    
    def _enhance_test_cases_with_llm(self, test_cases: List[Dict], doc_data: Dict) -> Optional[List[Dict]]:
        """使用LLM增强测试用例"""
        try:
            # 构建提示
            prompt = f"""
            请基于以下OpenAPI 3.0.0文档，增强以下测试用例，添加更多有价值的断言和测试数据：
            
            API文档信息：
            {json.dumps(doc_data, ensure_ascii=False)}
            
            当前测试用例：
            {json.dumps(test_cases, ensure_ascii=False)}
            
            请返回增强后的测试用例，保持JSON格式。
            """
            
            # 调用AI客户端
            response = self.ai_client.chat_completion(prompt)
            
            if response and response.get('success'):
                enhanced_cases_text = response.get('content', '')
                try:
                    enhanced_cases = json.loads(enhanced_cases_text)
                    if isinstance(enhanced_cases, list):
                        return enhanced_cases
                except json.JSONDecodeError:
                    ERROR.logger.warning("LLM返回的增强测试用例格式不正确")
            
            return None
            
        except Exception as e:
            ERROR.logger.error(f"LLM增强测试用例失败: {str(e)}")
            return None
    
    def _group_test_cases_by_suite(self, test_cases: List[Dict]) -> List[Dict]:
        """将测试用例按测试套件分组"""
        suites = {}
        
        for test_case in test_cases:
            scene_name = test_case.get('scene_name', 'Default')
            scene_type = test_case.get('scene_type', 'basic')
            
            # 创建或获取测试套件
            suite_key = f"{scene_type}_{scene_name}"
            if suite_key not in suites:
                suites[suite_key] = {
                    "name": scene_name,
                    "type": scene_type,
                    "priority": test_case.get('scene_priority', 'medium'),
                    "test_cases": []
                }
            
            # 添加测试用例到套件
            suites[suite_key]["test_cases"].append(test_case)
        
        # 转换为列表
        return list(suites.values())
    
    @tool
    def execute_test_cases_tool(self, test_suites: str, environment: Optional[str] = None) -> str:
        """
        执行测试用例
        
        Args:
            test_suites: 测试套件的JSON字符串
            environment: 环境配置的JSON字符串，可选
            
        Returns:
            测试执行结果的JSON字符串
        """
        try:
            INFO.logger.info("开始执行测试用例...")
            
            # 解析测试套件和环境配置
            suites_data = json.loads(test_suites)
            env_config = json.loads(environment) if environment else {}
            
            test_suites_list = suites_data.get('test_suites', [])
            
            # 初始化测试结果
            all_test_results = []
            suite_results = []
            
            # 执行每个测试套件
            for suite in test_suites_list:
                suite_name = suite.get('name', 'Unknown Suite')
                test_cases = suite.get('test_cases', [])
                
                INFO.logger.info(f"执行测试套件: {suite_name}，包含 {len(test_cases)} 个测试用例")
                
                # 执行套件中的每个测试用例
                suite_test_results = []
                passed_count = 0
                failed_count = 0
                error_count = 0
                
                for test_case in test_cases:
                    test_result = self._execute_single_test_case(test_case, env_config)
                    suite_test_results.append(test_result)
                    all_test_results.append(test_result)
                    
                    # 统计结果
                    if test_result.get('status') == 'passed':
                        passed_count += 1
                    elif test_result.get('status') == 'failed':
                        failed_count += 1
                    else:
                        error_count += 1
                
                # 创建套件结果
                suite_result = {
                    "suite_name": suite_name,
                    "suite_type": suite.get('type', 'unknown'),
                    "total_tests": len(test_cases),
                    "passed_tests": passed_count,
                    "failed_tests": failed_count,
                    "error_tests": error_count,
                    "success_rate": passed_count / len(test_cases) * 100 if test_cases else 0,
                    "test_results": suite_test_results
                }
                
                suite_results.append(suite_result)
                INFO.logger.info(f"测试套件 {suite_name} 执行完成，成功率: {suite_result['success_rate']:.2f}%")
            
            # 创建总体结果
            total_tests = sum(suite['total_tests'] for suite in suite_results)
            total_passed = sum(suite['passed_tests'] for suite in suite_results)
            total_failed = sum(suite['failed_tests'] for suite in suite_results)
            total_error = sum(suite['error_tests'] for suite in suite_results)
            
            overall_result = {
                "status": "success",
                "message": f"测试执行完成，总计 {total_tests} 个测试用例",
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_error": total_error,
                "overall_success_rate": total_passed / total_tests * 100 if total_tests > 0 else 0,
                "suite_results": suite_results,
                "all_test_results": all_test_results
            }
            
            INFO.logger.info(f"所有测试执行完成，总体成功率: {overall_result['overall_success_rate']:.2f}%")
            return json.dumps(overall_result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"执行测试用例失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"执行测试用例失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    def _execute_single_test_case(self, test_case: Dict, env_config: Dict) -> Dict:
        """执行单个测试用例"""
        import time
        import requests
        from urllib.parse import urljoin
        
        test_name = test_case.get('name', 'Unknown Test')
        path = test_case.get('path', '')
        method = test_case.get('method', 'GET')
        headers = test_case.get('headers', {})
        params = test_case.get('params', {})
        body = test_case.get('body', {})
        expected_status = test_case.get('expected_status', 200)
        assertions = test_case.get('assertions', [])
        
        # 获取基础URL
        base_url = env_config.get('base_url', 'http://localhost:8000')
        full_url = urljoin(base_url, path)
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            INFO.logger.info(f"执行测试用例: {test_name}")
            
            # 根据方法发送请求
            if method.upper() == 'GET':
                response = requests.get(full_url, headers=headers, params=params, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(full_url, headers=headers, json=body if body else None, params=params, timeout=10)
            elif method.upper() == 'PUT':
                response = requests.put(full_url, headers=headers, json=body if body else None, params=params, timeout=10)
            elif method.upper() == 'DELETE':
                response = requests.delete(full_url, headers=headers, params=params, timeout=10)
            elif method.upper() == 'PATCH':
                response = requests.patch(full_url, headers=headers, json=body if body else None, params=params, timeout=10)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            # 获取响应数据
            status_code = response.status_code
            response_data = {}
            
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"raw_response": response.text}
            
            # 执行断言
            assertion_results = []
            all_assertions_passed = True
            
            for assertion in assertions:
                assertion_type = assertion.get('type')
                expected_value = assertion.get('value')
                
                assertion_result = {
                    "type": assertion_type,
                    "expected": expected_value,
                    "actual": None,
                    "passed": False
                }
                
                if assertion_type == 'status_code':
                    assertion_result["actual"] = status_code
                    assertion_result["passed"] = (status_code == expected_value)
                
                elif assertion_type == 'response_time':
                    assertion_result["actual"] = response_time
                    assertion_result["passed"] = (response_time <= expected_value)
                
                # 可以添加更多断言类型
                
                assertion_results.append(assertion_result)
                
                if not assertion_result["passed"]:
                    all_assertions_passed = False
            
            # 确定测试结果状态
            if all_assertions_passed and status_code == expected_status:
                status = "passed"
            elif status_code != expected_status:
                status = "failed"
            else:
                status = "failed"  # 断言失败
            
            # 创建测试结果
            test_result = {
                "test_name": test_name,
                "status": status,
                "response_time": response_time,
                "status_code": status_code,
                "response_data": response_data,
                "assertion_results": assertion_results,
                "request": {
                    "url": full_url,
                    "method": method,
                    "headers": headers,
                    "params": params,
                    "body": body
                }
            }
            
            INFO.logger.info(f"测试用例 {test_name} 执行完成，状态: {status}")
            return test_result
            
        except Exception as e:
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            ERROR.logger.error(f"测试用例 {test_name} 执行异常: {str(e)}")
            
            # 创建错误结果
            test_result = {
                "test_name": test_name,
                "status": "error",
                "response_time": response_time,
                "status_code": 0,
                "response_data": {},
                "assertion_results": [],
                "error_message": str(e),
                "request": {
                    "url": full_url,
                    "method": method,
                    "headers": headers,
                    "params": params,
                    "body": body
                }
            }
            
            return test_result
    
    @tool
    def analyze_results_tool(self, test_results: str) -> str:
        """
        分析测试结果
        
        Args:
            test_results: 测试结果的JSON字符串
            
        Returns:
            测试结果分析的JSON字符串
        """
        try:
            INFO.logger.info("开始分析测试结果...")
            
            # 解析测试结果
            results_data = json.loads(test_results)
            all_test_results = results_data.get('all_test_results', [])
            suite_results = results_data.get('suite_results', [])
            
            # 基本统计
            total_tests = len(all_test_results)
            passed_tests = sum(1 for result in all_test_results if result.get('status') == 'passed')
            failed_tests = sum(1 for result in all_test_results if result.get('status') == 'failed')
            error_tests = sum(1 for result in all_test_results if result.get('status') == 'error')
            
            success_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0
            
            # 响应时间分析
            response_times = [result.get('response_time', 0) for result in all_test_results if result.get('response_time')]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0
            
            # 按状态码分析
            status_codes = {}
            for result in all_test_results:
                status_code = result.get('status_code', 0)
                status_codes[status_code] = status_codes.get(status_code, 0) + 1
            
            # 按测试套件分析
            suite_analysis = []
            for suite in suite_results:
                suite_name = suite.get('suite_name', 'Unknown')
                suite_type = suite.get('suite_type', 'unknown')
                suite_total = suite.get('total_tests', 0)
                suite_passed = suite.get('passed_tests', 0)
                suite_failed = suite.get('failed_tests', 0)
                suite_error = suite.get('error_tests', 0)
                suite_success_rate = suite.get('success_rate', 0)
                
                # 套件响应时间分析
                suite_response_times = [
                    result.get('response_time', 0) 
                    for result in suite.get('test_results', []) 
                    if result.get('response_time')
                ]
                suite_avg_response_time = sum(suite_response_times) / len(suite_response_times) if suite_response_times else 0
                
                suite_analysis.append({
                    "suite_name": suite_name,
                    "suite_type": suite_type,
                    "total_tests": suite_total,
                    "passed_tests": suite_passed,
                    "failed_tests": suite_failed,
                    "error_tests": suite_error,
                    "success_rate": suite_success_rate,
                    "avg_response_time": suite_avg_response_time
                })
            
            # 失败测试用例分析
            failed_test_cases = [
                {
                    "test_name": result.get('test_name', ''),
                    "status": result.get('status', ''),
                    "error_message": result.get('error_message', ''),
                    "status_code": result.get('status_code', 0),
                    "assertion_results": result.get('assertion_results', [])
                }
                for result in all_test_results 
                if result.get('status') in ['failed', 'error']
            ]
            
            # 使用LLM增强分析（如果可用）
            enhanced_analysis = None
            if self.ai_client.is_available():
                try:
                    enhanced_analysis = self._enhance_result_analysis_with_llm(all_test_results, suite_results)
                except Exception as e:
                    ERROR.logger.warning(f"LLM增强结果分析失败，使用基础分析: {str(e)}")
            
            # 构建分析结果
            analysis_result = {
                "status": "success",
                "message": "测试结果分析完成",
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "error_tests": error_tests,
                    "success_rate": success_rate
                },
                "performance": {
                    "avg_response_time": avg_response_time,
                    "max_response_time": max_response_time,
                    "min_response_time": min_response_time
                },
                "status_codes": status_codes,
                "suite_analysis": suite_analysis,
                "failed_test_cases": failed_test_cases,
                "enhanced_analysis": enhanced_analysis
            }
            
            INFO.logger.info(f"测试结果分析完成，总体成功率: {success_rate:.2f}%")
            return json.dumps(analysis_result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"分析测试结果失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"分析测试结果失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    def _enhance_result_analysis_with_llm(self, test_results: List[Dict], suite_results: List[Dict]) -> Optional[Dict]:
        """使用LLM增强结果分析"""
        try:
            # 构建提示
            prompt = f"""
            请基于以下测试结果，提供深入的分析和改进建议：
            
            测试结果：
            {json.dumps(test_results, ensure_ascii=False)}
            
            测试套件结果：
            {json.dumps(suite_results, ensure_ascii=False)}
            
            请提供以下内容：
            1. 测试质量评估
            2. 性能问题分析
            3. 潜在风险识别
            4. 改进建议
            
            请返回JSON格式的分析结果。
            """
            
            # 调用AI客户端
            response = self.ai_client.chat_completion(prompt)
            
            if response and response.get('success'):
                analysis_text = response.get('content', '')
                try:
                    analysis = json.loads(analysis_text)
                    if isinstance(analysis, dict):
                        return analysis
                except json.JSONDecodeError:
                    ERROR.logger.warning("LLM返回的分析结果格式不正确")
            
            return None
            
        except Exception as e:
            ERROR.logger.error(f"LLM增强结果分析失败: {str(e)}")
            return None
    
    @tool
    def generate_report_tool(self, analysis_results: str) -> str:
        """
        生成测试报告
        
        Args:
            analysis_results: 测试结果分析的JSON字符串
            
        Returns:
            测试报告的JSON字符串
        """
        try:
            INFO.logger.info("开始生成测试报告...")
            
            # 解析分析结果
            analysis_data = json.loads(analysis_results)
            summary = analysis_data.get('summary', {})
            performance = analysis_data.get('performance', {})
            status_codes = analysis_data.get('status_codes', {})
            suite_analysis = analysis_data.get('suite_analysis', [])
            failed_test_cases = analysis_data.get('failed_test_cases', [])
            enhanced_analysis = analysis_data.get('enhanced_analysis', {})
            
            # 生成报告内容
            report_content = {
                "title": "API自动化测试报告",
                "summary": {
                    "total_tests": summary.get('total_tests', 0),
                    "passed_tests": summary.get('passed_tests', 0),
                    "failed_tests": summary.get('failed_tests', 0),
                    "error_tests": summary.get('error_tests', 0),
                    "success_rate": summary.get('success_rate', 0),
                    "test_date": self._get_current_date()
                },
                "performance": {
                    "avg_response_time": performance.get('avg_response_time', 0),
                    "max_response_time": performance.get('max_response_time', 0),
                    "min_response_time": performance.get('min_response_time', 0),
                    "performance_rating": self._evaluate_performance(performance.get('avg_response_time', 0))
                },
                "status_codes": status_codes,
                "suite_analysis": suite_analysis,
                "failed_test_cases": failed_test_cases,
                "recommendations": self._generate_recommendations(analysis_data),
                "enhanced_analysis": enhanced_analysis
            }
            
            result = {
                "status": "success",
                "message": "测试报告生成完成",
                "report": report_content
            }
            
            INFO.logger.info("测试报告生成完成")
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            ERROR.logger.error(f"生成测试报告失败: {str(e)}")
            error_result = {
                "status": "error",
                "message": f"生成测试报告失败: {str(e)}"
            }
            return json.dumps(error_result, ensure_ascii=False)
    
    def _get_current_date(self) -> str:
        """获取当前日期字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _evaluate_performance(self, avg_response_time: float) -> str:
        """评估性能等级"""
        if avg_response_time < 200:
            return "优秀"
        elif avg_response_time < 500:
            return "良好"
        elif avg_response_time < 1000:
            return "一般"
        else:
            return "需要优化"
    
    def _generate_recommendations(self, analysis_data: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于成功率的建议
        success_rate = analysis_data.get('summary', {}).get('success_rate', 0)
        if success_rate < 90:
            recommendations.append("测试成功率较低，建议检查API实现和测试用例设计")
        
        # 基于性能的建议
        avg_response_time = analysis_data.get('performance', {}).get('avg_response_time', 0)
        if avg_response_time > 1000:
            recommendations.append("平均响应时间较长，建议优化API性能")
        
        # 基于失败测试用例的建议
        failed_cases = analysis_data.get('failed_test_cases', [])
        if failed_cases:
            # 分析常见失败原因
            status_codes = {}
            for case in failed_cases:
                status_code = case.get('status_code', 0)
                status_codes[status_code] = status_codes.get(status_code, 0) + 1
            
            if 401 in status_codes or 403 in status_codes:
                recommendations.append("存在认证授权问题，建议检查API安全机制")
            
            if 404 in status_codes:
                recommendations.append("存在API路径问题，建议检查API路由配置")
            
            if 500 in status_codes:
                recommendations.append("存在服务器内部错误，建议检查API实现")
        
        # 基于LLM增强分析的建议
        enhanced_analysis = analysis_data.get('enhanced_analysis', {})
        if enhanced_analysis and 'recommendations' in enhanced_analysis:
            llm_recommendations = enhanced_analysis['recommendations']
            if isinstance(llm_recommendations, list):
                recommendations.extend(llm_recommendations)
        
        return recommendations
    
    # 公共接口方法
    def parse_openapi(self, openapi_url_or_path: str) -> Dict[str, Any]:
        """解析OpenAPI 3.0.0文档"""
        result = self.parse_openapi_tool(openapi_url_or_path)
        return json.loads(result)
    
    def generate_test_scenes(self, api_doc: str, use_llm: bool = False) -> Dict[str, Any]:
        """生成测试场景"""
        result = self.generate_test_scene_tool(api_doc, use_llm)
        return json.loads(result)
    
    def generate_test_relations(self, test_scenes: str) -> Dict[str, Any]:
        """生成测试场景关系图"""
        result = self.generate_test_relation_tool(test_scenes)
        return json.loads(result)
    
    def generate_test_cases(self, test_scenes: str, api_doc: str) -> Dict[str, Any]:
        """生成测试用例"""
        result = self.generate_test_cases_tool(test_scenes, api_doc)
        return json.loads(result)
    
    def execute_test_cases(self, test_suites: str, environment: Optional[str] = None) -> Dict[str, Any]:
        """执行测试用例"""
        result = self.execute_test_cases_tool(test_suites, environment)
        return json.loads(result)
    
    def analyze_test_results(self, test_results: str) -> Dict[str, Any]:
        """分析测试结果"""
        result = self.analyze_results_tool(test_results)
        return json.loads(result)
    
    def generate_test_report(self, analysis_results: str) -> Dict[str, Any]:
        """生成测试报告"""
        result = self.generate_report_tool(analysis_results)
        return json.loads(result)
    
    def full_test_workflow(self, openapi_url_or_path: str, source_type: str = "url", 
                          test_type: str = "all", environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行完整的测试工作流程"""
        try:
            INFO.logger.info("开始执行完整的测试工作流程...")
            
            # 1. 解析OpenAPI文档
            parse_result = self.parse_openapi(openapi_url_or_path)
            if not parse_result.get('success'):
                return parse_result
            
            # 2. 生成测试场景
            api_doc = json.dumps(self.current_api_doc, ensure_ascii=False)
            scenes_result = self.generate_test_scenes(api_doc, use_llm=True)
            if not scenes_result.get('success'):
                return scenes_result
            
            # 3. 生成测试用例
            test_scenes = json.dumps(scenes_result, ensure_ascii=False)
            cases_result = self.generate_test_cases(test_scenes, api_doc)
            if not cases_result.get('success'):
                return cases_result
            
            # 4. 执行测试用例
            test_suites = json.dumps(cases_result, ensure_ascii=False)
            env_config = json.dumps(environment) if environment else None
            execution_result = self.execute_test_cases(test_suites, env_config)
            if not execution_result.get('success'):
                return execution_result
            
            # 5. 分析测试结果
            test_results = json.dumps(execution_result, ensure_ascii=False)
            analysis_result = self.analyze_test_results(test_results)
            if not analysis_result.get('success'):
                return analysis_result
            
            # 6. 生成测试报告
            analysis_results = json.dumps(analysis_result, ensure_ascii=False)
            report_result = self.generate_test_report(analysis_results)
            if not report_result.get('success'):
                return report_result
            
            # 构建完整工作流程结果
            workflow_result = {
                "success": True,
                "message": "完整测试工作流程执行成功",
                "parse_result": parse_result,
                "scenes_result": scenes_result,
                "cases_result": cases_result,
                "execution_result": execution_result,
                "analysis_result": analysis_result,
                "report_result": report_result
            }
            
            INFO.logger.info("完整测试工作流程执行成功")
            return workflow_result
            
        except Exception as e:
            ERROR.logger.error(f"执行完整测试工作流程失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# 为了向后兼容，保留SwaggerAgent的别名
SwaggerAgent = OpenAPIAgent