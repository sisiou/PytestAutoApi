"""
整合所有功能的APIAgent主模块
基于LangChain实现，整合OpenAPI3.0.0文档解析、测试用例生成、执行和分析功能
支持从飞书API URL到测试报告生成的完整工作流程
"""

import json
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from langchain_core.messages import SystemMessage
from langchain_core.prompts import MessagesPlaceholder
from .openapi_parser_tool import create_openapi_tools
from .test_case_generator_tool import create_test_generator_tools
from .test_executor_tool import create_test_executor_tools
from .feishu_to_openapi import create_feishu_to_openapi_tool


@dataclass
class AgentConfig:
    """Agent配置"""
    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"
    temperature: float = 0.1
    verbose: bool = True
    base_url: Optional[str] = None  # 添加base_url参数，支持自定义API端点


class OpenAPI3Agent:
    """OpenAPI3.0.0 API测试代理"""
    
    def __init__(self, config: AgentConfig):
        """初始化OpenAPI3.0.0 Agent"""
        self.config = config
        
        # 构建ChatOpenAI参数
        llm_kwargs = {
            "openai_api_key": config.openai_api_key,
            "model_name": config.openai_model,
            "temperature": config.temperature
        }
        
        # 如果提供了base_url，添加到参数中
        if config.base_url:
            llm_kwargs["openai_api_base"] = config.base_url
            
        self.llm = ChatOpenAI(**llm_kwargs)
        
        # 创建工具集
        self.tools = self._create_tools()
        
        # 创建代理执行器
        self.agent_executor = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=config.verbose,
            max_iterations=10,
            early_stopping_method="generate"
        )
    
    def _create_tools(self) -> List[BaseTool]:
        """创建工具集"""
        tools = []
        
        # 添加OpenAPI3.0.0解析工具
        tools.extend(create_openapi_tools())
        
        # 添加测试用例生成工具
        tools.extend(create_test_generator_tools())
        
        # 添加测试执行工具
        tools.extend(create_test_executor_tools())
        
        return tools
    
    def _create_agent(self):
        """创建代理"""
        # 创建系统提示
        system_prompt = """
        你是一个专业的API测试助手，专门帮助用户完成OpenAPI3.0.0文档解析、测试用例生成、执行和分析的全流程工作。
        
        你的主要功能包括：
        1. 解析OpenAPI3.0.0文档，提取API接口信息
        2. 根据API文档自动生成测试用例，包括基础测试、边界测试和错误测试
        3. 执行测试用例并收集结果
        4. 分析测试结果，提供性能和安全方面的分析
        5. 根据分析结果提供改进建议
        
        工作流程：
        1. 首先使用openapi_parse_tool解析OpenAPI3.0.0文档
        2. 使用openapi_analyzer_tool分析API依赖关系和测试场景
        3. 使用test_case_generator_tool生成测试用例
        4. 使用test_executor_tool执行测试用例
        5. 使用test_analyzer_tool分析测试结果
        
        注意事项：
        - 确保按照正确的顺序使用工具
        - 在生成测试用例时，考虑不同的测试场景
        - 在分析测试结果时，关注性能和安全方面的问题
        - 提供具体、可执行的改进建议
        """
        
        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 创建代理
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        
        return agent
    
    def run(self, query: str, api_doc_source: str, source_type: str = "url", 
            test_type: str = "all", environment: Optional[Dict] = None) -> Dict[str, Any]:
        """运行代理执行任务"""
        try:
            # 构建完整的查询
            full_query = f"""
            {query}
            
            请按照以下步骤执行：
            1. 解析提供的OpenAPI3.0.0文档
            2. 分析API结构和依赖关系
            3. 生成测试用例（类型：{test_type}）
            4. 执行测试用例
            5. 分析测试结果
            
            OpenAPI3.0.0文档来源：{api_doc_source}
            来源类型：{source_type}
            """
            
            # 如果提供了环境配置，添加到查询中
            if environment:
                full_query += f"\n\n环境配置：{json.dumps(environment, ensure_ascii=False)}"
            
            # 执行代理
            result = self.agent_executor.invoke({"input": full_query})
            
            return {
                "success": True,
                "result": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def parse_openapi(self, api_doc_source: str, source_type: str = "url") -> Dict[str, Any]:
        """解析OpenAPI3.0.0文档"""
        try:
            # 获取OpenAPI解析工具
            openapi_parse_tool = next(tool for tool in self.tools if tool.name == "openapi_parse_tool")
            
            # 执行解析
            result = openapi_parse_tool._run(openapi_source=api_doc_source, source_type=source_type)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_test_cases(self, openapi_source: str, source_type: str = "url", 
                           test_type: str = "all", num_cases: int = 3) -> Dict[str, Any]:
        """生成测试用例"""
        try:
            # 获取测试用例生成工具
            test_generator_tool = next(tool for tool in self.tools if tool.name == "test_case_generator_tool")
            
            # 执行生成
            result = test_generator_tool._run(
                openapi_source=openapi_source, 
                source_type=source_type,
                test_type=test_type,
                num_cases=num_cases
            )
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_tests(self, test_suite: Dict, environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行测试用例"""
        try:
            # 获取测试执行工具
            test_executor_tool = next(tool for tool in self.tools if tool.name == "test_executor_tool")
            
            # 确保测试套件格式正确
            if "test_suites" not in test_suite:
                # 如果是单个测试套件，包装成列表
                test_suite = {"test_suites": [test_suite]}
            
            # 执行测试
            result = test_executor_tool._run(test_suite=test_suite, environment=environment)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_test_results(self, test_results: List[Dict], analysis_type: str = "all") -> Dict[str, Any]:
        """分析测试结果"""
        try:
            # 获取测试分析工具
            test_analyzer_tool = next(tool for tool in self.tools if tool.name == "test_analyzer_tool")
            
            # 执行分析
            result = test_analyzer_tool._run(test_results=test_results, analysis_type=analysis_type)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def full_test_workflow(self, openapi_source: str, source_type: str = "url", 
                          test_type: str = "all", environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行完整的测试工作流"""
        try:
            # 1. 解析OpenAPI文档
            parse_result = self.parse_openapi(openapi_source, source_type)
            if not parse_result["success"]:
                return parse_result
            
            # 2. 生成测试用例
            generate_result = self.generate_test_cases(openapi_source, source_type, test_type)
            if not generate_result["success"]:
                return generate_result
            
            # 3. 执行测试用例
            test_suites = generate_result["data"].get("test_suites", [])
            all_test_results = []
            all_execution_results = []
            
            for test_suite in test_suites:
                execute_result = self.execute_tests(test_suite, environment)
                if execute_result["success"]:
                    all_execution_results.append(execute_result["data"])
                    # 收集测试结果用于分析
                    test_results = execute_result["data"].get("test_results", [])
                    all_test_results.extend(test_results)
            
            # 4. 分析测试结果
            analysis_result = self.analyze_test_results(all_test_results)
            if not analysis_result["success"]:
                return analysis_result
            
            # 5. 构建完整结果
            return {
                "success": True,
                "openapi_parse": parse_result["data"],
                "test_generation": generate_result["data"],
                "test_execution": all_execution_results,
                "test_analysis": analysis_result["data"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def feishu_to_openapi_workflow(self, feishu_api_url: str, save_path: Optional[str] = None,
                                  test_type: str = "all", environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行从飞书API URL开始的完整工作流程"""
        try:
            # 1. 将飞书API URL转换为OpenAPI 3.0.0文档
            feishu_converter = create_feishu_to_openapi_tool()
            openapi_doc = feishu_converter.convert_to_openapi(feishu_api_url, save_path)
            
            # 2. 保存OpenAPI文档到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(openapi_doc, f, ensure_ascii=False, indent=2)
                temp_file_path = f.name
            
            # 3. 执行完整的测试工作流
            workflow_result = self.full_test_workflow(
                openapi_source=temp_file_path, 
                source_type="file",
                test_type=test_type,
                environment=environment
            )
            
            # 4. 添加飞书API信息到结果中
            if workflow_result["success"]:
                workflow_result["feishu_api_url"] = feishu_api_url
                workflow_result["openapi_doc"] = openapi_doc
                if save_path:
                    workflow_result["openapi_doc_path"] = save_path
            
            # 5. 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
            
            return workflow_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def create_openapi_agent(openai_api_key: str, openai_model: str = "gpt-3.5-turbo", 
                        temperature: float = 0.1, verbose: bool = True, 
                        base_url: Optional[str] = None) -> OpenAPI3Agent:
    """创建OpenAPI3.0.0 Agent实例"""
    config = AgentConfig(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        temperature=temperature,
        verbose=verbose,
        base_url=base_url
    )
    
    return OpenAPI3Agent(config)


# 便捷函数
def test_api_from_openapi(openapi_source: str, openai_api_key: str, source_type: str = "url",
                         test_type: str = "all", environment: Optional[Dict] = None,
                         openai_model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """便捷函数：从OpenAPI文档测试API"""
    try:
        # 创建代理
        agent = create_openapi_agent(openai_api_key, openai_model)
        
        # 执行完整工作流
        return agent.full_test_workflow(openapi_source, source_type, test_type, environment)
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def test_feishu_api(feishu_api_url: str, openai_api_key: str, save_path: Optional[str] = None,
                   test_type: str = "all", environment: Optional[Dict] = None,
                   openai_model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """便捷函数：从飞书API URL测试API"""
    try:
        # 创建代理
        agent = create_openapi_agent(openai_api_key, openai_model)
        
        # 执行从飞书API URL开始的完整工作流
        return agent.feishu_to_openapi_workflow(feishu_api_url, save_path, test_type, environment)
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }