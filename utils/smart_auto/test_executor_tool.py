"""
测试用例执行和结果分析功能模块
基于LangChain工具实现，用于执行API测试用例并分析结果
"""

import json
import time
import requests
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import re
from datetime import datetime

from .test_case_generator_tool import GeneratedTestCase, GeneratedTestSuite


@dataclass
class TestExecutionResult:
    """测试执行结果"""
    test_name: str
    test_description: str
    method: str
    url: str
    status: str  # passed, failed, error
    execution_time: float
    request: Dict[str, Any]
    response: Dict[str, Any]
    assertions: List[Dict[str, Any]]
    assertion_results: List[Dict[str, Any]]
    error_message: Optional[str] = None


@dataclass
class TestSuiteExecutionResult:
    """测试套件执行结果"""
    suite_name: str
    suite_description: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    execution_time: float
    test_results: List[TestExecutionResult]
    summary: Dict[str, Any]


@dataclass
class TestAnalysisResult:
    """测试分析结果"""
    total_suites: int
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    success_rate: float
    average_response_time: float
    performance_issues: List[Dict[str, Any]]
    security_issues: List[Dict[str, Any]]
    recommendations: List[str]


class TestExecutorInput(BaseModel):
    """测试执行工具输入模型"""
    test_suite: Dict = Field(description="测试套件JSON数据")
    environment: Optional[Dict] = Field(description="测试环境配置，如base_url、headers等")


class TestExecutorTool(BaseTool):
    """测试执行工具"""
    name = "test_executor_tool"
    description = "执行API测试用例并收集结果"
    args_schema: type[BaseModel] = TestExecutorInput
    
    def _run(self, test_suite: Dict, environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行测试套件"""
        try:
            # 检查是否包含多个测试套件
            if "test_suites" in test_suite:
                # 执行多个测试套件
                return self._execute_multiple_suites(test_suite, environment)
            else:
                # 执行单个测试套件
                return self._execute_single_suite(test_suite, environment)
                
        except Exception as e:
            return {"error": f"执行测试套件失败: {str(e)}"}
    
    def _execute_multiple_suites(self, test_suites_data: Dict, environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行多个测试套件"""
        test_suites = test_suites_data.get("test_suites", [])
        all_results = []
        total_passed = 0
        total_failed = 0
        total_error = 0
        total_tests = 0
        total_execution_time = 0
        
        for suite_data in test_suites:
            suite_result = self._execute_single_suite(suite_data, environment)
            all_results.append(suite_result)
            
            total_passed += suite_result.get("passed_tests", 0)
            total_failed += suite_result.get("failed_tests", 0)
            total_error += suite_result.get("error_tests", 0)
            total_tests += suite_result.get("total_tests", 0)
            total_execution_time += suite_result.get("execution_time", 0)
        
        return {
            "test_suites": all_results,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": total_passed,
                "failed_tests": total_failed,
                "error_tests": total_error,
                "success_rate": total_passed / total_tests if total_tests > 0 else 0,
                "total_execution_time": total_execution_time
            }
        }
    
    def _execute_single_suite(self, test_suite: Dict, environment: Optional[Dict] = None) -> Dict[str, Any]:
        """执行单个测试套件"""
        # 解析测试套件
        suite_name = test_suite.get("name", "unknown_suite")
        suite_description = test_suite.get("description", "")
        test_cases = test_suite.get("test_cases", [])
        
        # 初始化环境配置
        env_config = environment or {}
        base_url = env_config.get("base_url", "")
        global_headers = env_config.get("headers", {})
        
        # 执行测试用例
        test_results = []
        total_start_time = time.time()
        
        for test_case in test_cases:
            result = self._execute_test_case(test_case, base_url, global_headers)
            test_results.append(result)
        
        total_execution_time = time.time() - total_start_time
        
        # 统计测试结果
        passed_tests = sum(1 for r in test_results if r.status == "passed")
        failed_tests = sum(1 for r in test_results if r.status == "failed")
        error_tests = sum(1 for r in test_results if r.status == "error")
        
        # 生成测试套件执行结果
        suite_result = TestSuiteExecutionResult(
            suite_name=suite_name,
            suite_description=suite_description,
            total_tests=len(test_cases),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            execution_time=total_execution_time,
            test_results=test_results,
            summary={
                "success_rate": passed_tests / len(test_cases) if test_cases else 0,
                "average_response_time": sum(r.execution_time for r in test_results) / len(test_results) if test_results else 0
            }
        )
        
        # 转换为字典返回
        return {
            "suite_name": suite_result.suite_name,
            "suite_description": suite_result.suite_description,
            "total_tests": suite_result.total_tests,
            "passed_tests": suite_result.passed_tests,
            "failed_tests": suite_result.failed_tests,
            "error_tests": suite_result.error_tests,
            "execution_time": suite_result.execution_time,
            "test_results": [
                {
                    "test_name": r.test_name,
                    "test_description": r.test_description,
                    "method": r.method,
                    "url": r.url,
                    "status": r.status,
                    "execution_time": r.execution_time,
                    "request": r.request,
                    "response": r.response,
                    "assertions": r.assertions,
                    "assertion_results": r.assertion_results,
                    "error_message": r.error_message
                } for r in suite_result.test_results
            ],
            "summary": suite_result.summary
        }
    
    def _execute_test_case(self, test_case: Dict, base_url: str, global_headers: Dict) -> TestExecutionResult:
        """执行单个测试用例"""
        test_name = test_case.get("name", "unknown_test")
        test_description = test_case.get("description", "")
        method = test_case.get("method", "GET")
        url = test_case.get("url", "")
        
        # 如果提供了base_url且url是相对路径，则组合
        if base_url and not url.startswith("http"):
            url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
        
        headers = {**global_headers, **test_case.get("headers", {})}
        params = test_case.get("params", {})
        body = test_case.get("body")
        expected_status = test_case.get("expected_status", 200)
        expected_response = test_case.get("expected_response")
        assertions = test_case.get("assertions", [])
        
        # 记录请求信息
        request_info = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "body": body
        }
        
        # 执行请求
        start_time = time.time()
        status = "error"
        response_info = {}
        assertion_results = []
        error_message = None
        
        try:
            # 发送请求
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, params=params, json=body, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, params=params, json=body, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, json=body, timeout=10)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, params=params, json=body, timeout=10)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            execution_time = time.time() - start_time
            
            # 记录响应信息
            response_info = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "json": None
            }
            
            # 尝试解析JSON响应
            try:
                response_info["json"] = response.json()
            except:
                pass  # 响应不是JSON格式
            
            # 执行断言
            all_passed = True
            for assertion in assertions:
                assertion_result = self._execute_assertion(assertion, response, execution_time, expected_response)
                assertion_results.append(assertion_result)
                if not assertion_result["passed"]:
                    all_passed = False
            
            # 确定测试状态
            if response.status_code == expected_status and all_passed:
                status = "passed"
            else:
                status = "failed"
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            response_info = {
                "error": error_message
            }
        
        return TestExecutionResult(
            test_name=test_name,
            test_description=test_description,
            method=method,
            url=url,
            status=status,
            execution_time=execution_time,
            request=request_info,
            response=response_info,
            assertions=assertions,
            assertion_results=assertion_results,
            error_message=error_message
        )
    
    def _execute_assertion(self, assertion: Dict, response: requests.Response, execution_time: float, expected_response: Optional[Dict]) -> Dict[str, Any]:
        """执行单个断言"""
        assertion_type = assertion.get("type", "")
        expected = assertion.get("expected")
        description = assertion.get("description", "")
        passed = False
        actual = None
        error_message = None
        
        try:
            if assertion_type == "status":
                actual = response.status_code
                passed = actual == expected
                
            elif assertion_type == "response_time":
                actual = execution_time * 1000  # 转换为毫秒
                if isinstance(expected, str) and expected.startswith("<"):
                    threshold = float(expected[1:].strip())
                    passed = actual < threshold
                elif isinstance(expected, str) and expected.startswith(">"):
                    threshold = float(expected[1:].strip())
                    passed = actual > threshold
                else:
                    threshold = float(expected)
                    passed = actual < threshold
                    
            elif assertion_type == "json_structure":
                try:
                    response_json = response.json()
                    if isinstance(expected, list):
                        # 检查响应是否包含所有预期的键
                        if isinstance(response_json, dict):
                            actual = list(response_json.keys())
                            passed = all(key in response_json for key in expected)
                        else:
                            actual = "Response is not a JSON object"
                            passed = False
                    else:
                        actual = "Expected value is not a list"
                        passed = False
                except:
                    actual = "Response is not valid JSON"
                    passed = False
                    
            elif assertion_type == "contains":
                try:
                    response_text = response.text
                    passed = expected in response_text
                    actual = response_text
                except:
                    actual = "Could not get response text"
                    passed = False
                    
            elif assertion_type == "json_value":
                try:
                    response_json = response.json()
                    if isinstance(expected, dict) and "path" in expected and "value" in expected:
                        path = expected["path"]
                        value = expected["value"]
                        actual = self._get_json_value_by_path(response_json, path)
                        passed = actual == value
                    else:
                        actual = "Invalid json_value assertion format"
                        passed = False
                except:
                    actual = "Response is not valid JSON"
                    passed = False
                    
            else:
                error_message = f"不支持的断言类型: {assertion_type}"
                
        except Exception as e:
            error_message = f"执行断言失败: {str(e)}"
        
        return {
            "type": assertion_type,
            "description": description,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "error_message": error_message
        }
    
    def _get_json_value_by_path(self, json_obj: Dict, path: str) -> Any:
        """根据路径获取JSON值"""
        keys = path.split(".")
        current = json_obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
                current = current[int(key)]
            else:
                return None
        
        return current


class TestAnalyzerInput(BaseModel):
    """测试分析工具输入模型"""
    test_results: List[Dict] = Field(description="测试结果列表")
    analysis_type: str = Field(description="分析类型：basic(基础分析)、performance(性能分析)、security(安全分析)或all(全部)")


class TestAnalyzerTool(BaseTool):
    """测试分析工具"""
    name = "test_analyzer_tool"
    description = "分析测试结果，提供性能、安全等方面的分析"
    args_schema: type[BaseModel] = TestAnalyzerInput
    
    def _run(self, test_results: List[Dict], analysis_type: str = "all") -> Dict[str, Any]:
        """执行测试结果分析"""
        try:
            # 初始化分析结果
            analysis = {
                "basic": {},
                "performance": {},
                "security": {},
                "recommendations": []
            }
            
            # 基础分析
            if analysis_type in ["basic", "all"]:
                analysis["basic"] = self._basic_analysis(test_results)
            
            # 性能分析
            if analysis_type in ["performance", "all"]:
                analysis["performance"] = self._performance_analysis(test_results)
            
            # 安全分析
            if analysis_type in ["security", "all"]:
                analysis["security"] = self._security_analysis(test_results)
            
            # 生成建议
            analysis["recommendations"] = self._generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            return {"error": f"分析测试结果失败: {str(e)}"}
    
    def _basic_analysis(self, test_results: List[Dict]) -> Dict[str, Any]:
        """基础分析"""
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get("status") == "passed")
        failed_tests = sum(1 for r in test_results if r.get("status") == "failed")
        error_tests = sum(1 for r in test_results if r.get("status") == "error")
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        # 按HTTP方法统计
        method_stats = {}
        for result in test_results:
            method = result.get("method", "UNKNOWN")
            if method not in method_stats:
                method_stats[method] = {"total": 0, "passed": 0}
            method_stats[method]["total"] += 1
            if result.get("status") == "passed":
                method_stats[method]["passed"] += 1
        
        # 按状态码统计
        status_code_stats = {}
        for result in test_results:
            response = result.get("response", {})
            status_code = response.get("status_code", "UNKNOWN")
            if status_code not in status_code_stats:
                status_code_stats[status_code] = 0
            status_code_stats[status_code] += 1
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": success_rate,
            "method_stats": method_stats,
            "status_code_stats": status_code_stats
        }
    
    def _performance_analysis(self, test_results: List[Dict]) -> Dict[str, Any]:
        """性能分析"""
        execution_times = []
        response_sizes = []
        
        for result in test_results:
            execution_time = result.get("execution_time", 0)
            execution_times.append(execution_time)
            
            response = result.get("response", {})
            content = response.get("content", "")
            response_sizes.append(len(content))
        
        # 计算统计数据
        avg_response_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_response_time = max(execution_times) if execution_times else 0
        min_response_time = min(execution_times) if execution_times else 0
        
        avg_response_size = sum(response_sizes) / len(response_sizes) if response_sizes else 0
        max_response_size = max(response_sizes) if response_sizes else 0
        min_response_size = min(response_sizes) if response_sizes else 0
        
        # 识别性能问题
        performance_issues = []
        
        # 响应时间超过5秒的请求
        slow_requests = [
            {"test_name": r.get("test_name"), "response_time": r.get("execution_time")}
            for r in test_results if r.get("execution_time", 0) > 5
        ]
        
        if slow_requests:
            performance_issues.append({
                "type": "slow_requests",
                "description": f"发现{len(slow_requests)}个响应时间超过5秒的请求",
                "details": slow_requests
            })
        
        # 响应大小超过1MB的请求
        large_responses = [
            {"test_name": r.get("test_name"), "response_size": len(r.get("response", {}).get("content", ""))}
            for r in test_results if len(r.get("response", {}).get("content", "")) > 1024 * 1024
        ]
        
        if large_responses:
            performance_issues.append({
                "type": "large_responses",
                "description": f"发现{len(large_responses)}个响应大小超过1MB的请求",
                "details": large_responses
            })
        
        return {
            "avg_response_time": avg_response_time,
            "max_response_time": max_response_time,
            "min_response_time": min_response_time,
            "avg_response_size": avg_response_size,
            "max_response_size": max_response_size,
            "min_response_size": min_response_size,
            "performance_issues": performance_issues
        }
    
    def _security_analysis(self, test_results: List[Dict]) -> Dict[str, Any]:
        """安全分析"""
        security_issues = []
        
        for result in test_results:
            test_name = result.get("test_name", "")
            response = result.get("response", {})
            headers = response.get("headers", {})
            
            # 检查是否缺少安全头
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy"
            ]
            
            missing_headers = [h for h in security_headers if h not in headers]
            if missing_headers:
                security_issues.append({
                    "type": "missing_security_headers",
                    "test_name": test_name,
                    "description": f"缺少安全头: {', '.join(missing_headers)}",
                    "severity": "medium"
                })
            
            # 检查是否在响应中泄露敏感信息
            content = response.get("content", "")
            sensitive_patterns = [
                (r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+', "密码信息"),
                (r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+', "API密钥"),
                (r'token["\']?\s*[:=]\s*["\']?[^"\'\s]+', "令牌信息"),
                (r'secret["\']?\s*[:=]\s*["\']?[^"\'\s]+', "密钥信息")
            ]
            
            for pattern, description in sensitive_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    security_issues.append({
                        "type": "sensitive_data_leak",
                        "test_name": test_name,
                        "description": f"响应中可能包含{description}",
                        "severity": "high"
                    })
            
            # 检查是否使用HTTPS
            request = result.get("request", {})
            url = request.get("url", "")
            if url.startswith("http://") and not url.startswith("http://localhost"):
                security_issues.append({
                    "type": "insecure_protocol",
                    "test_name": test_name,
                    "description": "使用不安全的HTTP协议",
                    "severity": "high"
                })
            
            # 检查错误信息是否暴露过多细节
            status_code = response.get("status_code", 0)
            if status_code >= 500:
                # 检查错误响应是否包含堆栈跟踪或详细错误信息
                if "stack trace" in content.lower() or "exception" in content.lower():
                    security_issues.append({
                        "type": "detailed_error_info",
                        "test_name": test_name,
                        "description": "错误响应可能包含过多细节",
                        "severity": "medium"
                    })
        
        return {
            "security_issues": security_issues,
            "security_score": self._calculate_security_score(security_issues, len(test_results))
        }
    
    def _calculate_security_score(self, security_issues: List[Dict], total_tests: int) -> float:
        """计算安全分数"""
        if total_tests == 0:
            return 0
        
        # 根据问题严重程度计算扣分
        high_severity_count = sum(1 for issue in security_issues if issue.get("severity") == "high")
        medium_severity_count = sum(1 for issue in security_issues if issue.get("severity") == "medium")
        low_severity_count = sum(1 for issue in security_issues if issue.get("severity") == "low")
        
        # 初始分数为100
        score = 100
        
        # 高严重性问题每个扣10分
        score -= high_severity_count * 10
        
        # 中等严重性问题每个扣5分
        score -= medium_severity_count * 5
        
        # 低严重性问题每个扣2分
        score -= low_severity_count * 2
        
        # 确保分数不低于0
        return max(0, score)
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于基础分析的建议
        basic = analysis.get("basic", {})
        success_rate = basic.get("success_rate", 0)
        
        if success_rate < 0.9:
            recommendations.append(f"测试通过率较低({success_rate:.2%})，建议检查API实现和测试用例设计")
        
        # 基于性能分析的建议
        performance = analysis.get("performance", {})
        avg_response_time = performance.get("avg_response_time", 0)
        performance_issues = performance.get("performance_issues", [])
        
        if avg_response_time > 2:
            recommendations.append(f"平均响应时间较长({avg_response_time:.2f}秒)，建议优化API性能")
        
        slow_requests = next((issue for issue in performance_issues if issue.get("type") == "slow_requests"), None)
        if slow_requests:
            recommendations.append("发现响应时间过长的请求，建议优化相关API或增加缓存")
        
        large_responses = next((issue for issue in performance_issues if issue.get("type") == "large_responses"), None)
        if large_responses:
            recommendations.append("发现响应过大的请求，建议优化数据结构或实现分页")
        
        # 基于安全分析的建议
        security = analysis.get("security", {})
        security_issues = security.get("security_issues", [])
        security_score = security.get("security_score", 100)
        
        if security_score < 80:
            recommendations.append(f"安全分数较低({security_score}/100)，建议加强安全措施")
        
        missing_headers_issues = [issue for issue in security_issues if issue.get("type") == "missing_security_headers"]
        if missing_headers_issues:
            recommendations.append("建议添加必要的安全响应头，如X-Content-Type-Options、X-Frame-Options等")
        
        insecure_protocol_issues = [issue for issue in security_issues if issue.get("type") == "insecure_protocol"]
        if insecure_protocol_issues:
            recommendations.append("建议使用HTTPS协议代替HTTP，以增强数据传输安全性")
        
        sensitive_data_issues = [issue for issue in security_issues if issue.get("type") == "sensitive_data_leak"]
        if sensitive_data_issues:
            recommendations.append("建议检查响应内容，避免在响应中泄露敏感信息")
        
        return recommendations


def create_test_executor_tools():
    """创建测试执行相关的工具集"""
    return [
        TestExecutorTool(),
        TestAnalyzerTool()
    ]