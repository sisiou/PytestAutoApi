"""
智能测试建议生成模块

该模块基于测试覆盖度分析、测试用例质量评估和API依赖关系，
生成全面的测试改进建议，帮助提高测试质量和效率。
"""

import json
import time
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .coverage_scorer import (
    APIScenario, TestCoverage, CoverageReport, CoverageType, CoverageLevel
)
from .api_parser import APIEndpoint
from .dependency_analyzer import DependencyAnalyzer


class SuggestionType(Enum):
    """建议类型"""
    COVERAGE = "coverage"  # 覆盖度相关建议
    TEST_CASE = "test_case"  # 测试用例相关建议
    ASSERTION = "assertion"  # 断言相关建议
    DATA = "data"  # 测试数据相关建议
    DEPENDENCY = "dependency"  # 依赖关系相关建议
    PERFORMANCE = "performance"  # 性能测试相关建议
    SECURITY = "security"  # 安全测试相关建议
    MAINTENANCE = "maintenance"  # 维护性相关建议


class SuggestionPriority(Enum):
    """建议优先级"""
    CRITICAL = "critical"  # 关键建议
    HIGH = "high"  # 高优先级建议
    MEDIUM = "medium"  # 中等优先级建议
    LOW = "low"  # 低优先级建议


@dataclass
class Suggestion:
    """测试建议"""
    suggestion_id: str
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    scenario_id: Optional[str] = None  # 关联的场景ID，None表示全局建议
    api_endpoint: Optional[str] = None  # 关联的API端点，None表示场景级别建议
    implementation_hint: Optional[str] = None  # 实现提示
    expected_benefit: Optional[str] = None  # 预期收益
    effort_estimate: Optional[str] = None  # 实现工作量估计


@dataclass
class SuggestionReport:
    """建议报告"""
    report_id: str
    report_name: str
    generated_time: str
    api_scenarios: List[APIScenario]
    suggestions: List[Suggestion]
    summary: Dict[str, Any] = field(default_factory=dict)
    priority_distribution: Dict[SuggestionPriority, int] = field(default_factory=dict)
    type_distribution: Dict[SuggestionType, int] = field(default_factory=dict)


class TestSuggestionGenerator:
    """测试建议生成器"""
    
    def __init__(self, api_endpoints: List[APIEndpoint] = None):
        # 如果没有提供api_endpoints，则初始化一个空列表
        apis = [self._convert_endpoint_to_dict(ep) for ep in api_endpoints] if api_endpoints else []
        self.dependency_analyzer = DependencyAnalyzer(apis)
    
    def _convert_endpoint_to_dict(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """将APIEndpoint对象转换为字典格式，供DependencyAnalyzer使用"""
        return {
            "method": endpoint.method,
            "path": endpoint.path,
            "operationId": endpoint.operation_id,
            "parameters": endpoint.parameters,
            "request_body": endpoint.request_body,
            "success_response": endpoint.success_response if endpoint.success_response else {},
            "tags": endpoint.tags,
            "summary": endpoint.summary
        }
    
    def generate_suggestions(self, api_scenarios: List[APIScenario], 
                           coverage_report: CoverageReport,
                           api_endpoints: List[APIEndpoint],
                           test_cases: List[Dict[str, Any]]) -> SuggestionReport:
        """生成全面的测试建议"""
        suggestions = []
        
        # 1. 基于覆盖度的建议
        coverage_suggestions = self._generate_coverage_suggestions(
            api_scenarios, coverage_report
        )
        suggestions.extend(coverage_suggestions)
        
        # 2. 基于测试用例质量的建议
        test_case_suggestions = self._generate_test_case_suggestions(
            api_scenarios, test_cases
        )
        suggestions.extend(test_case_suggestions)
        
        # 3. 基于断言质量的建议
        assertion_suggestions = self._generate_assertion_suggestions(
            api_scenarios, test_cases
        )
        suggestions.extend(assertion_suggestions)
        
        # 4. 基于测试数据的建议
        data_suggestions = self._generate_data_suggestions(
            api_scenarios, test_cases, api_endpoints
        )
        suggestions.extend(data_suggestions)
        
        # 5. 基于依赖关系的建议
        dependency_suggestions = self._generate_dependency_suggestions(
            api_scenarios, api_endpoints
        )
        suggestions.extend(dependency_suggestions)
        
        # 6. 性能测试建议
        performance_suggestions = self._generate_performance_suggestions(
            api_scenarios, api_endpoints
        )
        suggestions.extend(performance_suggestions)
        
        # 7. 安全测试建议
        security_suggestions = self._generate_security_suggestions(
            api_scenarios, api_endpoints
        )
        suggestions.extend(security_suggestions)
        
        # 8. 维护性建议
        maintenance_suggestions = self._generate_maintenance_suggestions(
            api_scenarios, test_cases
        )
        suggestions.extend(maintenance_suggestions)
        
        # 按优先级排序
        suggestions.sort(key=lambda s: self._priority_order(s.priority))
        
        # 生成统计信息
        priority_distribution = {}
        for priority in SuggestionPriority:
            priority_distribution[priority] = sum(
                1 for s in suggestions if s.priority == priority
            )
        
        type_distribution = {}
        for suggestion_type in SuggestionType:
            type_distribution[suggestion_type] = sum(
                1 for s in suggestions if s.suggestion_type == suggestion_type
            )
        
        summary = {
            "total_suggestions": len(suggestions),
            "critical_suggestions": priority_distribution[SuggestionPriority.CRITICAL],
            "high_priority_suggestions": priority_distribution[SuggestionPriority.HIGH],
            "scenarios_with_suggestions": len(set(s.scenario_id for s in suggestions if s.scenario_id)),
            "most_common_suggestion_type": max(type_distribution.items(), key=lambda x: x[1])[0].value if type_distribution else None,
            "estimated_implementation_time": self._estimate_total_implementation_time(suggestions)
        }
        
        return SuggestionReport(
            report_id=f"suggestion_report_{int(time.time())}",
            report_name="智能测试建议报告",
            generated_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            api_scenarios=api_scenarios,
            suggestions=suggestions,
            summary=summary,
            priority_distribution=priority_distribution,
            type_distribution=type_distribution
        )
    
    def _priority_order(self, priority: SuggestionPriority) -> int:
        """获取优先级排序值"""
        order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3
        }
        return order.get(priority, 3)
    
    def _estimate_total_implementation_time(self, suggestions: List[Suggestion]) -> str:
        """估算总实现时间"""
        time_map = {
            SuggestionPriority.CRITICAL: "4-8小时",
            SuggestionPriority.HIGH: "2-4小时",
            SuggestionPriority.MEDIUM: "1-2小时",
            SuggestionPriority.LOW: "0.5-1小时"
        }
        
        total_hours_min = 0
        total_hours_max = 0
        
        for suggestion in suggestions:
            if suggestion.priority == SuggestionPriority.CRITICAL:
                total_hours_min += 4
                total_hours_max += 8
            elif suggestion.priority == SuggestionPriority.HIGH:
                total_hours_min += 2
                total_hours_max += 4
            elif suggestion.priority == SuggestionPriority.MEDIUM:
                total_hours_min += 1
                total_hours_max += 2
            elif suggestion.priority == SuggestionPriority.LOW:
                total_hours_min += 0.5
                total_hours_max += 1
        
        return f"{total_hours_min}-{total_hours_max}小时"
    
    def _generate_coverage_suggestions(self, api_scenarios: List[APIScenario], 
                                      coverage_report: CoverageReport) -> List[Suggestion]:
        """基于覆盖度生成建议"""
        suggestions = []
        
        for coverage in coverage_report.test_coverages:
            scenario = next((s for s in api_scenarios if s.scenario_id == coverage.scenario_id), None)
            if not scenario:
                continue
            
            # 功能覆盖度不足
            func_coverage = coverage.coverage_types.get(CoverageType.FUNCTIONAL, 0)
            if func_coverage < 60:
                suggestions.append(Suggestion(
                    suggestion_id=f"coverage_func_{coverage.scenario_id}",
                    suggestion_type=SuggestionType.COVERAGE,
                    priority=SuggestionPriority.HIGH,
                    title=f"提高场景'{scenario.scenario_name}'的功能覆盖度",
                    description=f"当前功能覆盖度为{func_coverage:.1f}%，建议增加对核心功能的测试用例，确保所有主要功能点都被覆盖。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="分析场景中的API端点，为每个端点创建至少一个正常流程的测试用例。",
                    expected_benefit="提高功能测试覆盖度，减少未测试功能导致的生产问题。",
                    effort_estimate="2-3小时"
                ))
            elif func_coverage < 80:
                suggestions.append(Suggestion(
                    suggestion_id=f"coverage_func_{coverage.scenario_id}",
                    suggestion_type=SuggestionType.COVERAGE,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"完善场景'{scenario.scenario_name}'的功能覆盖度",
                    description=f"当前功能覆盖度为{func_coverage:.1f}%，建议补充对次要功能的测试用例，进一步提高覆盖度。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="检查场景中的API端点，确保所有功能点都有对应的测试用例。",
                    expected_benefit="进一步提高功能测试覆盖度，增强测试全面性。",
                    effort_estimate="1-2小时"
                ))
            
            # 参数覆盖度不足
            param_coverage = coverage.coverage_types.get(CoverageType.PARAMETER, 0)
            if param_coverage < 60:
                suggestions.append(Suggestion(
                    suggestion_id=f"coverage_param_{coverage.scenario_id}",
                    suggestion_type=SuggestionType.COVERAGE,
                    priority=SuggestionPriority.HIGH,
                    title=f"提高场景'{scenario.scenario_name}'的参数覆盖度",
                    description=f"当前参数覆盖度为{param_coverage:.1f}%，建议增加对参数边界值、空值和异常值的测试用例。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="为每个API参数创建正常值、边界值、空值和异常值的测试用例。",
                    expected_benefit="提高参数测试覆盖度，增强对异常输入的处理能力。",
                    effort_estimate="2-3小时"
                ))
            
            # 异常覆盖度不足
            exception_coverage = coverage.coverage_types.get(CoverageType.EXCEPTION, 0)
            if exception_coverage < 60:
                suggestions.append(Suggestion(
                    suggestion_id=f"coverage_exception_{coverage.scenario_id}",
                    suggestion_type=SuggestionType.COVERAGE,
                    priority=SuggestionPriority.HIGH,
                    title=f"提高场景'{scenario.scenario_name}'的异常覆盖度",
                    description=f"当前异常覆盖度为{exception_coverage:.1f}%，建议增加对各种异常情况的测试用例。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="分析API文档中的错误响应，为每种错误码创建对应的测试用例。",
                    expected_benefit="提高异常处理测试覆盖度，确保系统在异常情况下的稳定性。",
                    effort_estimate="2-4小时"
                ))
            
            # 业务场景覆盖度不足
            business_coverage = coverage.coverage_types.get(CoverageType.BUSINESS, 0)
            if business_coverage < 60:
                suggestions.append(Suggestion(
                    suggestion_id=f"coverage_business_{coverage.scenario_id}",
                    suggestion_type=SuggestionType.COVERAGE,
                    priority=SuggestionPriority.HIGH,
                    title=f"提高场景'{scenario.scenario_name}'的业务场景覆盖度",
                    description=f"当前业务场景覆盖度为{business_coverage:.1f}%，建议增加对完整业务流程的测试用例。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="设计端到端的业务流程测试，验证完整的业务流程。",
                    expected_benefit="提高业务场景测试覆盖度，确保业务流程的正确性。",
                    effort_estimate="3-5小时"
                ))
            
            # 集成测试覆盖度不足
            integration_coverage = coverage.coverage_types.get(CoverageType.INTEGRATION, 0)
            if integration_coverage < 60:
                suggestions.append(Suggestion(
                    suggestion_id=f"coverage_integration_{coverage.scenario_id}",
                    suggestion_type=SuggestionType.COVERAGE,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"提高场景'{scenario.scenario_name}'的集成测试覆盖度",
                    description=f"当前集成测试覆盖度为{integration_coverage:.1f}%，建议增加对API间交互的测试用例。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="设计API集成测试，验证不同API之间的交互。",
                    expected_benefit="提高集成测试覆盖度，确保API间的正确交互。",
                    effort_estimate="2-4小时"
                ))
        
        return suggestions
    
    def _generate_test_case_suggestions(self, api_scenarios: List[APIScenario], 
                                     test_cases: List[Dict[str, Any]]) -> List[Suggestion]:
        """基于测试用例质量生成建议"""
        suggestions = []
        
        # 按场景分组测试用例
        test_cases_by_scenario = {}
        for test_case in test_cases:
            scenario_id = test_case.get("scenario_id", "")
            if scenario_id not in test_cases_by_scenario:
                test_cases_by_scenario[scenario_id] = []
            test_cases_by_scenario[scenario_id].append(test_case)
        
        for scenario in api_scenarios:
            scenario_test_cases = test_cases_by_scenario.get(scenario.scenario_id, [])
            
            # 测试用例数量不足
            if len(scenario_test_cases) < 3:
                suggestions.append(Suggestion(
                    suggestion_id=f"testcase_count_{scenario.scenario_id}",
                    suggestion_type=SuggestionType.TEST_CASE,
                    priority=SuggestionPriority.HIGH,
                    title=f"增加场景'{scenario.scenario_name}'的测试用例数量",
                    description=f"当前场景只有{len(scenario_test_cases)}个测试用例，建议增加更多测试用例以提高测试覆盖率。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="为每个API端点创建至少3个测试用例：正常流程、异常流程和边界情况。",
                    expected_benefit="提高测试用例覆盖率，增强测试全面性。",
                    effort_estimate="2-3小时"
                ))
            
            # 测试用例描述不完整
            incomplete_descriptions = sum(
                1 for tc in scenario_test_cases 
                if not tc.get("description") or len(tc.get("description", "")) < 10
            )
            if incomplete_descriptions > 0:
                suggestions.append(Suggestion(
                    suggestion_id=f"testcase_description_{scenario.scenario_id}",
                    suggestion_type=SuggestionType.TEST_CASE,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"完善场景'{scenario.scenario_name}'的测试用例描述",
                    description=f"发现{incomplete_descriptions}个测试用例描述不完整或过于简单，建议补充详细描述。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="为每个测试用例添加详细的描述，说明测试目的、预期结果和测试步骤。",
                    expected_benefit="提高测试用例可读性和可维护性。",
                    effort_estimate="1-2小时"
                ))
            
            # 测试用例缺少标签
            cases_without_tags = sum(
                1 for tc in scenario_test_cases 
                if not tc.get("tags")
            )
            if cases_without_tags > 0:
                suggestions.append(Suggestion(
                    suggestion_id=f"testcase_tags_{scenario.scenario_id}",
                    suggestion_type=SuggestionType.TEST_CASE,
                    priority=SuggestionPriority.LOW,
                    title=f"为场景'{scenario.scenario_name}'的测试用例添加标签",
                    description=f"发现{cases_without_tags}个测试用例缺少标签，建议添加适当的标签以便分类和筛选。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="为测试用例添加功能标签、类型标签和优先级标签。",
                    expected_benefit="提高测试用例的可管理性和可筛选性。",
                    effort_estimate="1小时"
                ))
        
        return suggestions
    
    def _generate_assertion_suggestions(self, api_scenarios: List[APIScenario], 
                                       test_cases: List[Dict[str, Any]]) -> List[Suggestion]:
        """基于断言质量生成建议"""
        suggestions = []
        
        # 按场景分组测试用例
        test_cases_by_scenario = {}
        for test_case in test_cases:
            scenario_id = test_case.get("scenario_id", "")
            if scenario_id not in test_cases_by_scenario:
                test_cases_by_scenario[scenario_id] = []
            test_cases_by_scenario[scenario_id].append(test_case)
        
        for scenario in api_scenarios:
            scenario_test_cases = test_cases_by_scenario.get(scenario.scenario_id, [])
            
            # 测试用例缺少断言
            cases_without_assertions = sum(
                1 for tc in scenario_test_cases 
                if not tc.get("assertions") or len(tc.get("assertions", [])) == 0
            )
            if cases_without_assertions > 0:
                suggestions.append(Suggestion(
                    suggestion_id=f"assertion_missing_{scenario.scenario_id}",
                    suggestion_type=SuggestionType.ASSERTION,
                    priority=SuggestionPriority.CRITICAL,
                    title=f"为场景'{scenario.scenario_name}'的测试用例添加断言",
                    description=f"发现{cases_without_assertions}个测试用例缺少断言，没有断言的测试用例无法验证结果正确性。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="为每个测试用例添加状态码断言、响应数据断言和业务逻辑断言。",
                    expected_benefit="确保测试用例能够正确验证API响应，提高测试有效性。",
                    effort_estimate="2-3小时"
                ))
            
            # 断言类型单一
            single_type_assertions = 0
            for tc in scenario_test_cases:
                assertions = tc.get("assertions", [])
                if assertions:
                    assertion_types = set(a.get("type", "") for a in assertions)
                    if len(assertion_types) <= 1:
                        single_type_assertions += 1
            
            if single_type_assertions > 0:
                suggestions.append(Suggestion(
                    suggestion_id=f"assertion_types_{scenario.scenario_id}",
                    suggestion_type=SuggestionType.ASSERTION,
                    priority=SuggestionPriority.MEDIUM,
                    title=f"丰富场景'{scenario.scenario_name}'的断言类型",
                    description=f"发现{single_type_assertions}个测试用例只使用单一类型的断言，建议增加多种类型的断言。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="为测试用例添加状态码断言、响应头断言、响应体断言和性能断言。",
                    expected_benefit="提高测试用例的验证能力，增强测试全面性。",
                    effort_estimate="1-2小时"
                ))
        
        return suggestions
    
    def _generate_data_suggestions(self, api_scenarios: List[APIScenario], 
                                  test_cases: List[Dict[str, Any]],
                                  api_endpoints: List[APIEndpoint]) -> List[Suggestion]:
        """基于测试数据生成建议"""
        suggestions = []
        
        # 按场景分组测试用例
        test_cases_by_scenario = {}
        for test_case in test_cases:
            scenario_id = test_case.get("scenario_id", "")
            if scenario_id not in test_cases_by_scenario:
                test_cases_by_scenario[scenario_id] = []
            test_cases_by_scenario[scenario_id].append(test_case)
        
        for scenario in api_scenarios:
            scenario_test_cases = test_cases_by_scenario.get(scenario.scenario_id, [])
            
            # 测试数据多样性不足
            for endpoint in scenario.api_endpoints:
                endpoint_test_cases = [
                    tc for tc in scenario_test_cases 
                    if endpoint in tc.get("api_endpoints", [])
                ]
                
                if endpoint_test_cases:
                    # 检查参数值多样性
                    param_values = {}
                    for tc in endpoint_test_cases:
                        params = tc.get("parameters", [])
                        for param in params:
                            param_name = param.get("name", "")
                            param_value = param.get("value", "")
                            if param_name not in param_values:
                                param_values[param_name] = set()
                            param_values[param_name].add(str(param_value))
                    
                    # 找出值多样性不足的参数
                    for param_name, values in param_values.items():
                        if len(values) < 3:  # 少于3个不同值认为多样性不足
                            suggestions.append(Suggestion(
                                suggestion_id=f"data_diversity_{scenario.scenario_id}_{endpoint}_{param_name}",
                                suggestion_type=SuggestionType.DATA,
                                priority=SuggestionPriority.MEDIUM,
                                title=f"增加API'{endpoint}'参数'{param_name}'的测试数据多样性",
                                description=f"参数'{param_name}'只有{len(values)}个不同的测试值，建议增加更多样化的测试数据。",
                                scenario_id=scenario.scenario_id,
                                api_endpoint=endpoint,
                                implementation_hint=f"为参数'{param_name}'添加正常值、边界值、空值和异常值的测试数据。",
                                expected_benefit="提高测试数据覆盖率，增强测试全面性。",
                                effort_estimate="1小时"
                            ))
        
        # 全局测试数据建议
        # 检查是否有测试数据管理策略
        suggestions.append(Suggestion(
            suggestion_id="data_management",
            suggestion_type=SuggestionType.DATA,
            priority=SuggestionPriority.MEDIUM,
            title="建立测试数据管理策略",
            description="建议建立统一的测试数据管理策略，包括测试数据的生成、存储、清理和版本控制。",
            implementation_hint="创建测试数据管理模块，支持测试数据的自动生成、依赖管理和清理机制。",
            expected_benefit="提高测试数据管理效率，减少测试数据维护成本。",
            effort_estimate="4-6小时"
        ))
        
        return suggestions
    
    def _generate_dependency_suggestions(self, api_scenarios: List[APIScenario], 
                                       api_endpoints: List[APIEndpoint]) -> List[Suggestion]:
        """基于依赖关系生成建议"""
        suggestions = []
        
        # 分析API依赖关系
        self.dependency_analyzer.analyze_dependencies()
        dependencies = self.dependency_analyzer.data_dependencies
        
        # 检查是否有未测试的依赖关系
        for scenario in api_scenarios:
            scenario_endpoints = [
                ep for ep in api_endpoints 
                if ep.path in scenario.api_endpoints
            ]
            
            # 获取场景内API的依赖关系
            scenario_dependencies = []
            for ep in scenario_endpoints:
                for dep in dependencies:
                    if dep.source_api == ep.path and dep.target_api in scenario.api_endpoints:
                        scenario_dependencies.append(dep)
            
            # 检查依赖关系是否被测试
            if scenario_dependencies:
                suggestions.append(Suggestion(
                    suggestion_id=f"dependency_test_{scenario.scenario_id}",
                    suggestion_type=SuggestionType.DEPENDENCY,
                    priority=SuggestionPriority.HIGH,
                    title=f"测试场景'{scenario.scenario_name}'中的API依赖关系",
                    description=f"发现场景中有{len(scenario_dependencies)}个API依赖关系，建议创建测试用例验证这些依赖关系。",
                    scenario_id=scenario.scenario_id,
                    implementation_hint="设计测试用例，按照依赖关系顺序调用API，验证数据传递和状态变化。",
                    expected_benefit="确保API依赖关系的正确性，提高集成测试质量。",
                    effort_estimate="2-4小时"
                ))
        
        # 检查循环依赖
        circular_deps = [
            dep for dep in dependencies 
            if hasattr(dep, 'dependency_type') and dep.dependency_type == "circular"
        ]
        if circular_deps:
            suggestions.append(Suggestion(
                suggestion_id="circular_dependency",
                suggestion_type=SuggestionType.DEPENDENCY,
                priority=SuggestionPriority.CRITICAL,
                title="解决API循环依赖问题",
                description=f"发现{len(circular_deps)}个循环依赖关系，循环依赖可能导致测试困难和系统不稳定。",
                implementation_hint="重构API设计，消除循环依赖；或设计特殊的测试策略处理循环依赖。",
                expected_benefit="提高系统稳定性，简化测试设计。",
                effort_estimate="4-8小时"
            ))
        
        return suggestions
    
    def _generate_performance_suggestions(self, api_scenarios: List[APIScenario], 
                                        api_endpoints: List[APIEndpoint]) -> List[Suggestion]:
        """生成性能测试建议"""
        suggestions = []
        
        # 全局性能测试建议
        suggestions.append(Suggestion(
            suggestion_id="performance_testing",
            suggestion_type=SuggestionType.PERFORMANCE,
            priority=SuggestionPriority.MEDIUM,
            title="添加API性能测试",
            description="建议为关键API添加性能测试，验证API在不同负载下的响应时间和资源使用情况。",
            implementation_hint="使用性能测试工具（如JMeter、Locust）创建负载测试，监控API响应时间和资源使用。",
            expected_benefit="确保API性能满足要求，提前发现性能瓶颈。",
            effort_estimate="4-6小时"
        ))
        
        # 针对高优先级场景的性能测试建议
        high_priority_scenarios = [
            s for s in api_scenarios 
            if s.priority == "high" or s.business_value == "high"
        ]
        
        for scenario in high_priority_scenarios:
            suggestions.append(Suggestion(
                suggestion_id=f"performance_scenario_{scenario.scenario_id}",
                suggestion_type=SuggestionType.PERFORMANCE,
                priority=SuggestionPriority.HIGH,
                title=f"为高价值场景'{scenario.scenario_name}'添加性能测试",
                description=f"场景'{scenario.scenario_name}'是高优先级/高业务价值场景，建议添加专门的性能测试。",
                scenario_id=scenario.scenario_id,
                implementation_hint="设计场景级别的性能测试，模拟真实用户负载，验证端到端性能。",
                expected_benefit="确保关键业务场景的性能满足要求，提升用户体验。",
                effort_estimate="3-5小时"
            ))
        
        return suggestions
    
    def _generate_security_suggestions(self, api_scenarios: List[APIScenario], 
                                     api_endpoints: List[APIEndpoint]) -> List[Suggestion]:
        """生成安全测试建议"""
        suggestions = []
        
        # 全局安全测试建议
        suggestions.append(Suggestion(
            suggestion_id="security_testing",
            suggestion_type=SuggestionType.SECURITY,
            priority=SuggestionPriority.HIGH,
            title="添加API安全测试",
            description="建议为API添加安全测试，验证API的安全性和抗攻击能力。",
            implementation_hint="使用安全测试工具（如OWASP ZAP）进行安全扫描，创建针对常见安全漏洞的测试用例。",
            expected_benefit="提高API安全性，防范安全攻击。",
            effort_estimate="4-6小时"
        ))
        
        # 针对认证相关API的安全测试建议
        auth_endpoints = [
            ep for ep in api_endpoints 
            if "auth" in ep.path.lower() or "login" in ep.path.lower() or "register" in ep.path.lower()
        ]
        
        if auth_endpoints:
            suggestions.append(Suggestion(
                suggestion_id="auth_security",
                suggestion_type=SuggestionType.SECURITY,
                priority=SuggestionPriority.CRITICAL,
                title="加强认证相关API的安全测试",
                description="发现认证相关API，建议加强这些API的安全测试，防止认证绕过和会话劫持。",
                implementation_hint="添加认证绕过测试、会话管理测试和密码策略测试。",
                expected_benefit="提高认证系统安全性，保护用户数据。",
                effort_estimate="3-5小时"
            ))
        
        # 针对数据敏感API的安全测试建议
        data_sensitive_endpoints = [
            ep for ep in api_endpoints 
            if any(keyword in ep.path.lower() for keyword in ["user", "profile", "payment", "order"])
        ]
        
        if data_sensitive_endpoints:
            suggestions.append(Suggestion(
                suggestion_id="data_security",
                suggestion_type=SuggestionType.SECURITY,
                priority=SuggestionPriority.HIGH,
                title="加强数据敏感API的安全测试",
                description="发现处理敏感数据的API，建议加强这些API的安全测试，防止数据泄露。",
                implementation_hint="添加数据加密测试、访问控制测试和数据泄露测试。",
                expected_benefit="保护敏感数据，防止数据泄露。",
                effort_estimate="3-5小时"
            ))
        
        return suggestions
    
    def _generate_maintenance_suggestions(self, api_scenarios: List[APIScenario], 
                                       test_cases: List[Dict[str, Any]]) -> List[Suggestion]:
        """生成维护性建议"""
        suggestions = []
        
        # 测试用例重复检查
        test_case_signatures = set()
        duplicate_count = 0
        
        for test_case in test_cases:
            # 创建测试用例签名（基于API端点和参数）
            endpoints = tuple(sorted(test_case.get("api_endpoints", [])))
            # 将参数字典转换为可哈希的字符串表示
            params = tuple(sorted(str(p) for p in test_case.get("parameters", [])))
            signature = (endpoints, params)
            
            if signature in test_case_signatures:
                duplicate_count += 1
            else:
                test_case_signatures.add(signature)
        
        if duplicate_count > 0:
            suggestions.append(Suggestion(
                suggestion_id="duplicate_test_cases",
                suggestion_type=SuggestionType.MAINTENANCE,
                priority=SuggestionPriority.MEDIUM,
                title="消除重复的测试用例",
                description=f"发现{duplicate_count}个可能重复的测试用例，建议合并或重构重复的测试用例。",
                implementation_hint="分析测试用例的目的和预期结果，合并功能相似的测试用例。",
                expected_benefit="减少测试套件维护成本，提高测试执行效率。",
                effort_estimate="2-3小时"
            ))
        
        # 测试用例命名规范
        poorly_named_cases = sum(
            1 for tc in test_cases 
            if not tc.get("name") or len(tc.get("name", "")) < 5 or "_" not in tc.get("name", "")
        )
        
        if poorly_named_cases > 0:
            suggestions.append(Suggestion(
                suggestion_id="test_case_naming",
                suggestion_type=SuggestionType.MAINTENANCE,
                priority=SuggestionPriority.LOW,
                title="改进测试用例命名规范",
                description=f"发现{poorly_named_cases}个测试用例命名不规范，建议采用统一的命名规范。",
                implementation_hint="采用'测试场景_测试功能_预期结果'的命名规范，确保测试用例名称清晰描述测试内容。",
                expected_benefit="提高测试用例可读性和可维护性。",
                effort_estimate="1-2小时"
            ))
        
        # 测试文档建议
        suggestions.append(Suggestion(
            suggestion_id="test_documentation",
            suggestion_type=SuggestionType.MAINTENANCE,
            priority=SuggestionPriority.MEDIUM,
            title="完善测试文档",
            description="建议完善测试文档，包括测试策略、测试用例设计说明和测试环境配置。",
            implementation_hint="创建测试文档模板，记录测试设计决策、测试环境配置和测试执行指南。",
            expected_benefit="提高测试团队协作效率，降低新成员学习成本。",
            effort_estimate="3-4小时"
        ))
        
        # 测试自动化建议
        suggestions.append(Suggestion(
            suggestion_id="test_automation",
            suggestion_type=SuggestionType.MAINTENANCE,
            priority=SuggestionPriority.HIGH,
            title="提高测试自动化程度",
            description="建议提高测试自动化程度，减少手工测试工作量，提高测试效率和可靠性。",
            implementation_hint="分析测试用例，识别可自动化的测试场景，使用CI/CD工具集成自动化测试。",
            expected_benefit="减少测试执行时间，提高测试频率和反馈速度。",
            effort_estimate="6-10小时"
        ))
        
        return suggestions


class SuggestionReporter:
    """建议报告生成器"""
    
    def __init__(self, output_dir: str = "suggestion_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_json_report(self, report: SuggestionReport) -> str:
        """生成JSON格式报告"""
        report_data = {
            "report_id": report.report_id,
            "report_name": report.report_name,
            "generated_time": report.generated_time,
            "summary": report.summary,
            "priority_distribution": {p.value: count for p, count in report.priority_distribution.items()},
            "type_distribution": {t.value: count for t, count in report.type_distribution.items()},
            "suggestions": []
        }
        
        for suggestion in report.suggestions:
            suggestion_data = {
                "suggestion_id": suggestion.suggestion_id,
                "suggestion_type": suggestion.suggestion_type.value,
                "priority": suggestion.priority.value,
                "title": suggestion.title,
                "description": suggestion.description,
                "scenario_id": suggestion.scenario_id,
                "api_endpoint": suggestion.api_endpoint,
                "implementation_hint": suggestion.implementation_hint,
                "expected_benefit": suggestion.expected_benefit,
                "effort_estimate": suggestion.effort_estimate
            }
            report_data["suggestions"].append(suggestion_data)
        
        # 保存JSON报告
        report_file = self.output_dir / f"{report.report_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(report_file)
    
    def generate_html_report(self, report: SuggestionReport) -> str:
        """生成HTML格式报告"""
        # 生成优先级颜色
        priority_colors = {
            SuggestionPriority.CRITICAL: "#e74c3c",
            SuggestionPriority.HIGH: "#e67e22",
            SuggestionPriority.MEDIUM: "#f39c12",
            SuggestionPriority.LOW: "#95a5a6"
        }
        
        # 生成建议类型中文名
        type_names = {
            SuggestionType.COVERAGE: "覆盖度建议",
            SuggestionType.TEST_CASE: "测试用例建议",
            SuggestionType.ASSERTION: "断言建议",
            SuggestionType.DATA: "测试数据建议",
            SuggestionType.DEPENDENCY: "依赖关系建议",
            SuggestionType.PERFORMANCE: "性能测试建议",
            SuggestionType.SECURITY: "安全测试建议",
            SuggestionType.MAINTENANCE: "维护性建议"
        }
        
        # 生成优先级中文名
        priority_names = {
            SuggestionPriority.CRITICAL: "关键",
            SuggestionPriority.HIGH: "高",
            SuggestionPriority.MEDIUM: "中",
            SuggestionPriority.LOW: "低"
        }
        
        # 生成建议列表HTML
        suggestions_html = ""
        for suggestion in report.suggestions:
            scenario_name = ""
            if suggestion.scenario_id:
                scenario = next((s for s in report.api_scenarios if s.scenario_id == suggestion.scenario_id), None)
                if scenario:
                    scenario_name = scenario.scenario_name
            
            suggestions_html += f"""
            <div class="suggestion-item priority-{suggestion.priority.value}">
                <div class="suggestion-header">
                    <h3>{suggestion.title}</h3>
                    <div class="suggestion-meta">
                        <span class="priority-badge priority-{suggestion.priority.value}">{priority_names[suggestion.priority]}</span>
                        <span class="type-badge">{type_names[suggestion.suggestion_type]}</span>
                        {f'<span class="scenario-badge">{scenario_name}</span>' if scenario_name else ''}
                        {f'<span class="endpoint-badge">{suggestion.api_endpoint}</span>' if suggestion.api_endpoint else ''}
                    </div>
                </div>
                <div class="suggestion-body">
                    <p class="description">{suggestion.description}</p>
                    {f'<div class="implementation-hint"><strong>实现提示:</strong> {suggestion.implementation_hint}</div>' if suggestion.implementation_hint else ''}
                    {f'<div class="expected-benefit"><strong>预期收益:</strong> {suggestion.expected_benefit}</div>' if suggestion.expected_benefit else ''}
                    {f'<div class="effort-estimate"><strong>工作量估计:</strong> {suggestion.effort_estimate}</div>' if suggestion.effort_estimate else ''}
                </div>
            </div>
            """
        
        # 生成优先级分布图表HTML
        priority_chart_html = ""
        for priority, count in report.priority_distribution.items():
            if count > 0:
                color = priority_colors[priority]
                percentage = (count / report.summary["total_suggestions"]) * 100
                priority_chart_html += f"""
                <div class="chart-item">
                    <div class="chart-label">{priority_names[priority]}优先级</div>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: {percentage}%; background-color: {color}"></div>
                    </div>
                    <div class="chart-value">{count} ({percentage:.1f}%)</div>
                </div>
                """
        
        # 生成类型分布图表HTML
        type_chart_html = ""
        for suggestion_type, count in report.type_distribution.items():
            if count > 0:
                percentage = (count / report.summary["total_suggestions"]) * 100
                type_chart_html += f"""
                <div class="chart-item">
                    <div class="chart-label">{type_names[suggestion_type]}</div>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: {percentage}%; background-color: #3498db"></div>
                    </div>
                    <div class="chart-value">{count} ({percentage:.1f}%)</div>
                </div>
                """
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.report_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 16px;
        }}
        .summary-card .value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .chart-container {{
            margin-bottom: 30px;
        }}
        .chart-container h2 {{
            margin-bottom: 20px;
        }}
        .chart {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .chart-item {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .chart-label {{
            width: 150px;
            font-weight: bold;
        }}
        .chart-bar {{
            flex-grow: 1;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 0 15px;
        }}
        .chart-fill {{
            height: 100%;
            transition: width 1s ease-in-out;
        }}
        .chart-value {{
            width: 80px;
            text-align: right;
        }}
        .suggestion-item {{
            border: 1px solid #ddd;
            border-radius: 6px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .suggestion-header {{
            background-color: #f2f2f2;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .suggestion-header h3 {{
            margin: 0;
        }}
        .suggestion-meta {{
            display: flex;
            gap: 10px;
        }}
        .priority-badge, .type-badge, .scenario-badge, .endpoint-badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }}
        .priority-critical {{ background-color: {priority_colors[SuggestionPriority.CRITICAL]}; }}
        .priority-high {{ background-color: {priority_colors[SuggestionPriority.HIGH]}; }}
        .priority-medium {{ background-color: {priority_colors[SuggestionPriority.MEDIUM]}; }}
        .priority-low {{ background-color: {priority_colors[SuggestionPriority.LOW]}; }}
        .type-badge {{ background-color: #3498db; }}
        .scenario-badge {{ background-color: #9b59b6; }}
        .endpoint-badge {{ background-color: #1abc9c; }}
        .suggestion-body {{
            padding: 15px;
        }}
        .description {{
            margin-bottom: 10px;
        }}
        .implementation-hint, .expected-benefit, .effort-estimate {{
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
        }}
        .implementation-hint {{
            background-color: #e8f4fd;
        }}
        .expected-benefit {{
            background-color: #e8f8f5;
        }}
        .effort-estimate {{
            background-color: #fef9e7;
        }}
        .tabs {{
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }}
        .tab {{
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
        }}
        .tab.active {{
            border-bottom-color: #3498db;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .filter-container {{
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .filter-group label {{
            font-weight: bold;
        }}
        .filter-group select {{
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .filter-group button {{
            padding: 5px 15px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .filter-group button:hover {{
            background-color: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report.report_name}</h1>
        <p>报告生成时间: {report.generated_time}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>总建议数</h3>
                <div class="value">{report.summary["total_suggestions"]}</div>
            </div>
            <div class="summary-card">
                <h3>关键建议</h3>
                <div class="value">{report.summary["critical_suggestions"]}</div>
            </div>
            <div class="summary-card">
                <h3>高优先级建议</h3>
                <div class="value">{report.summary["high_priority_suggestions"]}</div>
            </div>
            <div class="summary-card">
                <h3>涉及场景数</h3>
                <div class="value">{report.summary["scenarios_with_suggestions"]}</div>
            </div>
            <div class="summary-card">
                <h3>预计实现时间</h3>
                <div class="value">{report.summary["estimated_implementation_time"]}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>建议分布</h2>
            <div class="tabs">
                <div class="tab active" onclick="showTab('priority')">按优先级分布</div>
                <div class="tab" onclick="showTab('type')">按类型分布</div>
            </div>
            
            <div id="priority" class="tab-content active">
                <div class="chart">
                    {priority_chart_html}
                </div>
            </div>
            
            <div id="type" class="tab-content">
                <div class="chart">
                    {type_chart_html}
                </div>
            </div>
        </div>
        
        <div class="filter-container">
            <div class="filter-group">
                <label>优先级:</label>
                <select id="priority-filter">
                    <option value="">全部</option>
                    <option value="critical">关键</option>
                    <option value="high">高</option>
                    <option value="medium">中</option>
                    <option value="low">低</option>
                </select>
            </div>
            <div class="filter-group">
                <label>类型:</label>
                <select id="type-filter">
                    <option value="">全部</option>
                    <option value="coverage">覆盖度建议</option>
                    <option value="test_case">测试用例建议</option>
                    <option value="assertion">断言建议</option>
                    <option value="data">测试数据建议</option>
                    <option value="dependency">依赖关系建议</option>
                    <option value="performance">性能测试建议</option>
                    <option value="security">安全测试建议</option>
                    <option value="maintenance">维护性建议</option>
                </select>
            </div>
            <div class="filter-group">
                <button onclick="applyFilters()">应用筛选</button>
                <button onclick="resetFilters()">重置</button>
            </div>
        </div>
        
        <h2>详细建议</h2>
        <div id="suggestions-container">
            {suggestions_html}
        </div>
    </div>
    
    <script>
        function showTab(tabId) {{
            // 隐藏所有标签内容
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => {{
                content.classList.remove('active');
            }});
            
            // 移除所有标签的active类
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // 显示选中的标签内容
            document.getElementById(tabId).classList.add('active');
            
            // 添加active类到选中的标签
            event.target.classList.add('active');
        }}
        
        function applyFilters() {{
            const priorityFilterValue = document.getElementById('priority-filter').value;
            const typeFilterValue = document.getElementById('type-filter').value;
            
            const suggestions = document.querySelectorAll('.suggestion-item');
            suggestions.forEach(suggestion => {{
                let show = true;
                
                if (priorityFilterValue && !suggestion.classList.contains('priority-' + priorityFilterValue)) {{
                    show = false;
                }}
                
                // 这里需要更复杂的逻辑来按类型筛选，因为类型不在class中
                // 可以使用data属性或其他方法
                
                suggestion.style.display = show ? 'block' : 'none';
            }});
        }}
        
        function resetFilters() {{
            document.getElementById('priority-filter').value = '';
            document.getElementById('type-filter').value = '';
            
            const suggestions = document.querySelectorAll('.suggestion-item');
            suggestions.forEach(suggestion => {{
                suggestion.style.display = 'block';
            }});
        }}
    </script>
</body>
</html>
        """
        
        # 保存HTML报告
        report_file = self.output_dir / f"{report.report_id}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_file)


# 示例使用
if __name__ == "__main__":
    # 这里可以添加示例代码
    pass