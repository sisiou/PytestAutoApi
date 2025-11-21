"""
接口场景覆盖度评分模块

该模块负责评估测试用例对接口场景的覆盖程度，并提供评分和改进建议。
支持多种覆盖度指标计算，包括功能覆盖、参数覆盖、异常覆盖等。
"""

import os
import json
import math
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoverageType(Enum):
    """覆盖度类型枚举"""
    FUNCTIONAL = "functional"  # 功能覆盖度
    PARAMETER = "parameter"   # 参数覆盖度
    EXCEPTION = "exception"   # 异常覆盖度
    BUSINESS = "business"     # 业务场景覆盖度
    INTEGRATION = "integration"  # 集成测试覆盖度


class CoverageLevel(Enum):
    """覆盖度级别枚举"""
    POOR = "poor"       # 差 (0-40%)
    FAIR = "fair"       # 一般 (40-60%)
    GOOD = "good"       # 良好 (60-80%)
    EXCELLENT = "excellent"  # 优秀 (80-100%)


@dataclass
class APIScenario:
    """API场景定义"""
    scenario_id: str
    scenario_name: str
    description: str
    api_endpoints: List[str]  # 涉及的API端点
    prerequisites: List[str] = field(default_factory=list)  # 前置条件
    test_steps: List[Dict[str, Any]] = field(default_factory=list)  # 测试步骤
    expected_results: List[Dict[str, Any]] = field(default_factory=list)  # 预期结果
    tags: List[str] = field(default_factory=list)  # 标签
    priority: str = "medium"  # 优先级
    business_value: str = "medium"  # 业务价值


@dataclass
class TestCoverage:
    """测试覆盖度信息"""
    scenario_id: str
    scenario_name: str
    coverage_types: Dict[CoverageType, float] = field(default_factory=dict)
    total_coverage: float = 0.0
    coverage_level: CoverageLevel = CoverageLevel.POOR
    missing_tests: List[str] = field(default_factory=list)
    test_cases: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """覆盖度报告"""
    report_id: str
    report_name: str
    api_scenarios: List[APIScenario] = field(default_factory=list)
    test_coverages: List[TestCoverage] = field(default_factory=list)
    overall_coverage: float = 0.0
    overall_level: CoverageLevel = CoverageLevel.POOR
    coverage_by_type: Dict[CoverageType, float] = field(default_factory=dict)
    coverage_by_tag: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    generated_time: str = field(default_factory=str)


class CoverageCalculator:
    """覆盖度计算器"""
    
    def __init__(self):
        self.weight_config = {
            CoverageType.FUNCTIONAL: 0.3,    # 功能覆盖度权重
            CoverageType.PARAMETER: 0.2,     # 参数覆盖度权重
            CoverageType.EXCEPTION: 0.2,     # 异常覆盖度权重
            CoverageType.BUSINESS: 0.2,      # 业务场景覆盖度权重
            CoverageType.INTEGRATION: 0.1    # 集成测试覆盖度权重
        }
    
    def calculate_functional_coverage(self, scenario: APIScenario, test_cases: List[Dict[str, Any]]) -> float:
        """计算功能覆盖度"""
        if not scenario.test_steps:
            return 0.0
        
        # 获取场景中所有需要测试的功能点
        required_functions = set()
        for step in scenario.test_steps:
            if "function" in step:
                required_functions.add(step["function"])
        
        # 获取测试用例中覆盖的功能点
        covered_functions = set()
        for test_case in test_cases:
            if "functions" in test_case:
                covered_functions.update(test_case["functions"])
        
        # 计算覆盖度
        if not required_functions:
            return 0.0
        
        coverage = len(covered_functions & required_functions) / len(required_functions)
        return coverage * 100
    
    def calculate_parameter_coverage(self, scenario: APIScenario, test_cases: List[Dict[str, Any]]) -> float:
        """计算参数覆盖度"""
        if not scenario.test_steps:
            return 0.0
        
        # 获取场景中所有需要测试的参数
        required_params = set()
        param_types = {}  # 参数类型
        
        for step in scenario.test_steps:
            if "parameters" in step:
                for param in step["parameters"]:
                    param_name = param.get("name")
                    if param_name:
                        required_params.add(param_name)
                        param_types[param_name] = param.get("type", "string")
        
        # 获取测试用例中覆盖的参数
        covered_params = set()
        param_variations = {}  # 参数变体数量
        
        for test_case in test_cases:
            if "parameters" in test_case:
                for param in test_case["parameters"]:
                    param_name = param.get("name")
                    if param_name and param_name in required_params:
                        covered_params.add(param_name)
                        
                        # 记录参数变体
                        if param_name not in param_variations:
                            param_variations[param_name] = set()
                        
                        param_value = param.get("value")
                        if param_value is not None:
                            param_variations[param_name].add(str(param_value))
        
        # 计算覆盖度
        if not required_params:
            return 0.0
        
        # 基础覆盖度：参数是否被测试
        basic_coverage = len(covered_params) / len(required_params)
        
        # 变体覆盖度：参数变体数量是否足够
        variation_coverage = 0.0
        if param_variations:
            total_variations = 0
            expected_variations = 0
            
            for param_name, variations in param_variations.items():
                param_type = param_types.get(param_name, "string")
                
                # 根据参数类型确定期望的变体数量
                if param_type == "boolean":
                    expected = 2  # true/false
                elif param_type == "enum":
                    # 枚举类型需要覆盖所有枚举值
                    expected = max(
                        len(step.get("enum_values", []))
                        for step in scenario.test_steps
                        if "parameters" in step
                        for param in step["parameters"]
                        if param.get("name") == param_name and "enum_values" in param
                    ) if any(
                        "enum_values" in param
                        for step in scenario.test_steps
                        if "parameters" in step
                        for param in step["parameters"]
                        if param.get("name") == param_name
                    ) else 1
                    expected = max(expected) if expected else 1
                else:
                    expected = 3  # 正常值、边界值、异常值
                
                expected_variations += expected
                total_variations += min(len(variations), expected)
            
            if expected_variations > 0:
                variation_coverage = total_variations / expected_variations
        
        # 综合覆盖度：基础覆盖度占70%，变体覆盖度占30%
        coverage = (basic_coverage * 0.7 + variation_coverage * 0.3) * 100
        return coverage
    
    def calculate_exception_coverage(self, scenario: APIScenario, test_cases: List[Dict[str, Any]]) -> float:
        """计算异常覆盖度"""
        if not scenario.test_steps:
            return 0.0
        
        # 获取场景中所有需要测试的异常情况
        required_exceptions = set()
        for step in scenario.test_steps:
            if "exceptions" in step:
                for exception in step["exceptions"]:
                    required_exceptions.add(exception.get("type", "unknown"))
        
        # 获取测试用例中覆盖的异常情况
        covered_exceptions = set()
        for test_case in test_cases:
            if "exceptions" in test_case:
                for exception in test_case["exceptions"]:
                    covered_exceptions.add(exception.get("type", "unknown"))
        
        # 计算覆盖度
        if not required_exceptions:
            return 0.0
        
        coverage = len(covered_exceptions & required_exceptions) / len(required_exceptions)
        return coverage * 100
    
    def calculate_business_coverage(self, scenario: APIScenario, test_cases: List[Dict[str, Any]]) -> float:
        """计算业务场景覆盖度"""
        if not scenario.test_steps:
            return 0.0
        
        # 获取场景中所有需要测试的业务流程
        required_flows = set()
        for step in scenario.test_steps:
            if "business_flow" in step:
                required_flows.add(step["business_flow"])
        
        # 获取测试用例中覆盖的业务流程
        covered_flows = set()
        for test_case in test_cases:
            if "business_flow" in test_case:
                covered_flows.add(test_case["business_flow"])
        
        # 计算覆盖度
        if not required_flows:
            return 0.0
        
        coverage = len(covered_flows & required_flows) / len(required_flows)
        return coverage * 100
    
    def calculate_integration_coverage(self, scenario: APIScenario, test_cases: List[Dict[str, Any]]) -> float:
        """计算集成测试覆盖度"""
        if not scenario.api_endpoints or len(scenario.api_endpoints) <= 1:
            return 100.0  # 单一API不需要集成测试
        
        # 获取场景中所有需要测试的API集成点
        required_integrations = set()
        for i in range(len(scenario.api_endpoints)):
            for j in range(i + 1, len(scenario.api_endpoints)):
                required_integrations.add((scenario.api_endpoints[i], scenario.api_endpoints[j]))
        
        # 获取测试用例中覆盖的API集成点
        covered_integrations = set()
        for test_case in test_cases:
            if "api_sequence" in test_case:
                apis = test_case["api_sequence"]
                for i in range(len(apis)):
                    for j in range(i + 1, len(apis)):
                        if (apis[i], apis[j]) in required_integrations or (apis[j], apis[i]) in required_integrations:
                            covered_integrations.add((apis[i], apis[j]))
        
        # 计算覆盖度
        if not required_integrations:
            return 0.0
        
        coverage = len(covered_integrations) / len(required_integrations)
        return coverage * 100
    
    def calculate_overall_coverage(self, coverages: Dict[CoverageType, float]) -> float:
        """计算总体覆盖度"""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for coverage_type, coverage_value in coverages.items():
            if coverage_type in self.weight_config:
                weight = self.weight_config[coverage_type]
                total_weight += weight
                weighted_sum += coverage_value * weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def get_coverage_level(self, coverage: float) -> CoverageLevel:
        """根据覆盖度获取覆盖度级别"""
        if coverage < 40:
            return CoverageLevel.POOR
        elif coverage < 60:
            return CoverageLevel.FAIR
        elif coverage < 80:
            return CoverageLevel.GOOD
        else:
            return CoverageLevel.EXCELLENT


class CoverageScorer:
    """覆盖度评分器"""
    
    def __init__(self):
        self.calculator = CoverageCalculator()
    
    def score_scenario_coverage(self, scenario: APIScenario, test_cases: List[Dict[str, Any]]) -> TestCoverage:
        """对单个场景进行覆盖度评分"""
        # 计算各类覆盖度
        coverages = {}
        
        coverages[CoverageType.FUNCTIONAL] = self.calculator.calculate_functional_coverage(scenario, test_cases)
        coverages[CoverageType.PARAMETER] = self.calculator.calculate_parameter_coverage(scenario, test_cases)
        coverages[CoverageType.EXCEPTION] = self.calculator.calculate_exception_coverage(scenario, test_cases)
        coverages[CoverageType.BUSINESS] = self.calculator.calculate_business_coverage(scenario, test_cases)
        coverages[CoverageType.INTEGRATION] = self.calculator.calculate_integration_coverage(scenario, test_cases)
        
        # 计算总体覆盖度
        total_coverage = self.calculator.calculate_overall_coverage(coverages)
        coverage_level = self.calculator.get_coverage_level(total_coverage)
        
        # 生成缺失测试建议
        missing_tests = self._identify_missing_tests(scenario, test_cases, coverages)
        
        # 生成改进建议
        recommendations = self._generate_recommendations(scenario, test_cases, coverages)
        
        # 获取测试用例ID
        test_case_ids = [test_case.get("id", "") for test_case in test_cases]
        
        return TestCoverage(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            coverage_types=coverages,
            total_coverage=total_coverage,
            coverage_level=coverage_level,
            missing_tests=missing_tests,
            test_cases=test_case_ids,
            recommendations=recommendations
        )
    
    def _identify_missing_tests(self, scenario: APIScenario, test_cases: List[Dict[str, Any]], 
                               coverages: Dict[CoverageType, float]) -> List[str]:
        """识别缺失的测试"""
        missing_tests = []
        
        # 功能覆盖度不足
        if coverages.get(CoverageType.FUNCTIONAL, 0) < 80:
            missing_tests.append("功能测试覆盖不足，需要增加对核心功能的测试用例")
        
        # 参数覆盖度不足
        if coverages.get(CoverageType.PARAMETER, 0) < 80:
            missing_tests.append("参数测试覆盖不足，需要增加对参数边界值和异常值的测试用例")
        
        # 异常覆盖度不足
        if coverages.get(CoverageType.EXCEPTION, 0) < 80:
            missing_tests.append("异常测试覆盖不足，需要增加对各种异常情况的测试用例")
        
        # 业务场景覆盖度不足
        if coverages.get(CoverageType.BUSINESS, 0) < 80:
            missing_tests.append("业务场景测试覆盖不足，需要增加对完整业务流程的测试用例")
        
        # 集成测试覆盖度不足
        if coverages.get(CoverageType.INTEGRATION, 0) < 80:
            missing_tests.append("集成测试覆盖不足，需要增加对API间交互的测试用例")
        
        return missing_tests
    
    def _generate_recommendations(self, scenario: APIScenario, test_cases: List[Dict[str, Any]], 
                                 coverages: Dict[CoverageType, float]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 根据覆盖度类型生成具体建议
        if coverages.get(CoverageType.FUNCTIONAL, 0) < 60:
            recommendations.append(f"建议为场景'{scenario.scenario_name}'添加更多功能测试用例，确保所有核心功能都被覆盖")
        
        if coverages.get(CoverageType.PARAMETER, 0) < 60:
            recommendations.append(f"建议为场景'{scenario.scenario_name}'添加参数测试用例，包括边界值、空值和异常值")
        
        if coverages.get(CoverageType.EXCEPTION, 0) < 60:
            recommendations.append(f"建议为场景'{scenario.scenario_name}'添加异常处理测试用例，验证系统在异常情况下的行为")
        
        if coverages.get(CoverageType.BUSINESS, 0) < 60:
            recommendations.append(f"建议为场景'{scenario.scenario_name}'添加端到端业务流程测试，验证完整的业务流程")
        
        if coverages.get(CoverageType.INTEGRATION, 0) < 60:
            recommendations.append(f"建议为场景'{scenario.scenario_name}'添加API集成测试，验证不同API之间的交互")
        
        # 根据优先级生成建议
        if scenario.priority == "high" and any(coverage < 80 for coverage in coverages.values()):
            recommendations.append(f"场景'{scenario.scenario_name}'是高优先级场景，建议提高其测试覆盖度至80%以上")
        
        # 根据业务价值生成建议
        if scenario.business_value == "high" and any(coverage < 80 for coverage in coverages.values()):
            recommendations.append(f"场景'{scenario.scenario_name}'具有高业务价值，建议提高其测试覆盖度至80%以上")
        
        return recommendations
    
    def score_all_scenarios(self, scenarios: List[APIScenario], 
                          test_cases_by_scenario: Dict[str, List[Dict[str, Any]]]) -> CoverageReport:
        """对所有场景进行覆盖度评分"""
        test_coverages = []
        
        for scenario in scenarios:
            test_cases = test_cases_by_scenario.get(scenario.scenario_id, [])
            coverage = self.score_scenario_coverage(scenario, test_cases)
            test_coverages.append(coverage)
        
        # 计算总体覆盖度
        overall_coverage = sum(coverage.total_coverage for coverage in test_coverages) / len(test_coverages) if test_coverages else 0
        overall_level = self.calculator.get_coverage_level(overall_coverage)
        
        # 按类型计算覆盖度
        coverage_by_type = {}
        for coverage_type in CoverageType:
            type_coverages = [coverage.coverage_types.get(coverage_type, 0) for coverage in test_coverages]
            coverage_by_type[coverage_type] = sum(type_coverages) / len(type_coverages) if type_coverages else 0
        
        # 按标签计算覆盖度
        coverage_by_tag = {}
        for scenario in scenarios:
            for tag in scenario.tags:
                tag_coverages = []
                for coverage in test_coverages:
                    if coverage.scenario_id == scenario.scenario_id:
                        tag_coverages.append(coverage.total_coverage)
                
                if tag_coverages:
                    if tag not in coverage_by_tag:
                        coverage_by_tag[tag] = []
                    coverage_by_tag[tag].extend(tag_coverages)
        
        # 计算每个标签的平均覆盖度
        for tag in coverage_by_tag:
            coverage_by_tag[tag] = sum(coverage_by_tag[tag]) / len(coverage_by_tag[tag])
        
        # 生成总体建议
        recommendations = self._generate_overall_recommendations(test_coverages, coverage_by_type)
        
        return CoverageReport(
            report_id=f"coverage_report_{int(time.time())}",
            report_name="接口场景覆盖度评分报告",
            api_scenarios=scenarios,
            test_coverages=test_coverages,
            overall_coverage=overall_coverage,
            overall_level=overall_level,
            coverage_by_type=coverage_by_type,
            coverage_by_tag=coverage_by_tag,
            recommendations=recommendations
        )
    
    def _generate_overall_recommendations(self, test_coverages: List[TestCoverage], 
                                        coverage_by_type: Dict[CoverageType, float]) -> List[str]:
        """生成总体改进建议"""
        recommendations = []
        
        # 找出覆盖度最低的类型
        lowest_coverage_type = min(coverage_by_type.items(), key=lambda x: x[1])
        if lowest_coverage_type[1] < 60:
            type_name = {
                CoverageType.FUNCTIONAL: "功能测试",
                CoverageType.PARAMETER: "参数测试",
                CoverageType.EXCEPTION: "异常测试",
                CoverageType.BUSINESS: "业务场景测试",
                CoverageType.INTEGRATION: "集成测试"
            }.get(lowest_coverage_type[0], "未知类型")
            
            recommendations.append(f"整体{type_name}覆盖度较低({lowest_coverage_type[1]:.1f}%)，建议重点加强这方面的测试")
        
        # 找出覆盖度最低的场景
        if test_coverages:
            lowest_coverage_scenario = min(test_coverages, key=lambda x: x.total_coverage)
            if lowest_coverage_scenario.total_coverage < 60:
                recommendations.append(f"场景'{lowest_coverage_scenario.scenario_name}'覆盖度最低({lowest_coverage_scenario.total_coverage:.1f}%)，建议优先改进")
        
        # 根据总体覆盖度给出建议
        overall_coverage = sum(coverage.total_coverage for coverage in test_coverages) / len(test_coverages) if test_coverages else 0
        if overall_coverage < 40:
            recommendations.append("整体测试覆盖度较低，建议全面审查测试策略，增加测试用例")
        elif overall_coverage < 60:
            recommendations.append("整体测试覆盖度一般，建议针对薄弱环节增加测试用例")
        elif overall_coverage < 80:
            recommendations.append("整体测试覆盖度良好，建议继续完善细节测试，提高覆盖度至80%以上")
        else:
            recommendations.append("整体测试覆盖度优秀，建议保持现有测试策略，并关注新增功能的测试覆盖")
        
        return recommendations


class CoverageReporter:
    """覆盖度报告生成器"""
    
    def __init__(self, output_dir: str = "coverage_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.calculator = CoverageCalculator()
    
    def generate_json_report(self, report: CoverageReport) -> str:
        """生成JSON格式报告"""
        report_data = {
            "report_id": report.report_id,
            "report_name": report.report_name,
            "generated_time": report.generated_time,
            "summary": {
                "overall_coverage": report.overall_coverage,
                "overall_level": report.overall_level.value,
                "total_scenarios": len(report.api_scenarios),
                "coverage_by_type": {ctype.value: coverage for ctype, coverage in report.coverage_by_type.items()},
                "coverage_by_tag": report.coverage_by_tag
            },
            "recommendations": report.recommendations,
            "scenarios": []
        }
        
        for scenario, coverage in zip(report.api_scenarios, report.test_coverages):
            scenario_data = {
                "scenario_id": scenario.scenario_id,
                "scenario_name": scenario.scenario_name,
                "description": scenario.description,
                "api_endpoints": scenario.api_endpoints,
                "tags": scenario.tags,
                "priority": scenario.priority,
                "business_value": scenario.business_value,
                "coverage": {
                    "total_coverage": coverage.total_coverage,
                    "coverage_level": coverage.coverage_level.value,
                    "coverage_by_type": {ctype.value: cov for ctype, cov in coverage.coverage_types.items()},
                    "test_cases": coverage.test_cases,
                    "missing_tests": coverage.missing_tests,
                    "recommendations": coverage.recommendations
                }
            }
            report_data["scenarios"].append(scenario_data)
        
        # 保存JSON报告
        report_file = self.output_dir / f"{report.report_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(report_file)
    
    def generate_html_report(self, report: CoverageReport) -> str:
        """生成HTML格式报告"""
        # 生成覆盖度级别颜色
        level_colors = {
            CoverageLevel.POOR: "#e74c3c",
            CoverageLevel.FAIR: "#f39c12",
            CoverageLevel.GOOD: "#f1c40f",
            CoverageLevel.EXCELLENT: "#2ecc71"
        }
        
        # 生成覆盖度类型中文名
        type_names = {
            CoverageType.FUNCTIONAL: "功能覆盖度",
            CoverageType.PARAMETER: "参数覆盖度",
            CoverageType.EXCEPTION: "异常覆盖度",
            CoverageType.BUSINESS: "业务场景覆盖度",
            CoverageType.INTEGRATION: "集成测试覆盖度"
        }
        
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
        .coverage-bar {{
            width: 100%;
            height: 30px;
            background-color: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .coverage-fill {{
            height: 100%;
            background-color: {level_colors[report.overall_level]};
            transition: width 1s ease-in-out;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .level-poor {{ color: {level_colors[CoverageLevel.POOR]}; }}
        .level-fair {{ color: {level_colors[CoverageLevel.FAIR]}; }}
        .level-good {{ color: {level_colors[CoverageLevel.GOOD]}; }}
        .level-excellent {{ color: {level_colors[CoverageLevel.EXCELLENT]}; }}
        .coverage-cell {{
            position: relative;
        }}
        .mini-bar {{
            width: 100%;
            height: 10px;
            background-color: #ecf0f1;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .mini-fill {{
            height: 100%;
            border-radius: 5px;
        }}
        .recommendations {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .recommendations h3 {{
            margin-top: 0;
        }}
        .recommendations ul {{
            margin-bottom: 0;
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
        .scenario-details {{
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
        }}
        .scenario-header {{
            background-color: #f2f2f2;
            padding: 15px;
            font-weight: bold;
        }}
        .scenario-body {{
            padding: 15px;
        }}
        .coverage-types {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .coverage-type {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
        }}
        .coverage-type h4 {{
            margin: 0 0 5px 0;
        }}
        .missing-tests, .scenario-recommendations {{
            margin-top: 15px;
        }}
        .missing-tests h4, .scenario-recommendations h4 {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report.report_name}</h1>
        <p>报告生成时间: {report.generated_time}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>总体覆盖度</h3>
                <div class="value">{report.overall_coverage:.1f}%</div>
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: {report.overall_coverage}%"></div>
                </div>
            </div>
            <div class="summary-card">
                <h3>覆盖度级别</h3>
                <div class="value level-{report.overall_level.value}">{report.overall_level.value.upper()}</div>
            </div>
            <div class="summary-card">
                <h3>总场景数</h3>
                <div class="value">{len(report.api_scenarios)}</div>
            </div>
            <div class="summary-card">
                <h3>平均场景覆盖度</h3>
                <div class="value">{sum(coverage.total_coverage for coverage in report.test_coverages) / len(report.test_coverages) if report.test_coverages else 0:.1f}%</div>
            </div>
        </div>
        
        <div class="recommendations">
            <h3>总体建议</h3>
            <ul>
                {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
            </ul>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('scenarios')">场景详情</div>
            <div class="tab" onclick="showTab('by-type')">按类型分析</div>
            <div class="tab" onclick="showTab('by-tag')">按标签分析</div>
        </div>
        
        <div id="scenarios" class="tab-content active">
            <h2>场景覆盖度详情</h2>
            {self._generate_scenarios_html(report, type_names, level_colors)}
        </div>
        
        <div id="by-type" class="tab-content">
            <h2>按覆盖度类型分析</h2>
            {self._generate_by_type_html(report, type_names, level_colors)}
        </div>
        
        <div id="by-tag" class="tab-content">
            <h2>按标签分析</h2>
            {self._generate_by_tag_html(report, level_colors)}
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
    </script>
</body>
</html>
        """
        
        # 保存HTML报告
        report_file = self.output_dir / f"{report.report_id}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_file)
    
    def _generate_scenarios_html(self, report: CoverageReport, type_names: Dict[CoverageType, str], 
                                level_colors: Dict[CoverageLevel, str]) -> str:
        """生成场景详情HTML内容"""
        html = ""
        
        for scenario, coverage in zip(report.api_scenarios, report.test_coverages):
            # 生成覆盖度类型HTML
            coverage_types_html = ""
            for coverage_type, coverage_value in coverage.coverage_types.items():
                color = level_colors[self.calculator.get_coverage_level(coverage_value)]
                coverage_types_html += f"""
                <div class="coverage-type">
                    <h4>{type_names.get(coverage_type, coverage_type.value)}</h4>
                    <div class="coverage-cell">
                        <div>{coverage_value:.1f}%</div>
                        <div class="mini-bar">
                            <div class="mini-fill" style="width: {coverage_value}%; background-color: {color}"></div>
                        </div>
                    </div>
                </div>
                """
            
            # 生成缺失测试HTML
            missing_tests_html = ""
            if coverage.missing_tests:
                missing_tests_html = """
                <div class="missing-tests">
                    <h4>缺失测试</h4>
                    <ul>
                """
                for missing_test in coverage.missing_tests:
                    missing_tests_html += f"<li>{missing_test}</li>"
                missing_tests_html += "</ul></div>"
            
            # 生成建议HTML
            recommendations_html = ""
            if coverage.recommendations:
                recommendations_html = """
                <div class="scenario-recommendations">
                    <h4>改进建议</h4>
                    <ul>
                """
                for rec in coverage.recommendations:
                    recommendations_html += f"<li>{rec}</li>"
                recommendations_html += "</ul></div>"
            
            html += f"""
            <div class="scenario-details">
                <div class="scenario-header">
                    {scenario.scenario_name} - 总体覆盖度: {coverage.total_coverage:.1f}% ({coverage.coverage_level.value.upper()})
                </div>
                <div class="scenario-body">
                    <p><strong>描述:</strong> {scenario.description}</p>
                    <p><strong>API端点:</strong> {', '.join(scenario.api_endpoints)}</p>
                    <p><strong>标签:</strong> {', '.join(scenario.tags) if scenario.tags else '无'}</p>
                    <p><strong>优先级:</strong> {scenario.priority} | <strong>业务价值:</strong> {scenario.business_value}</p>
                    
                    <h4>覆盖度详情</h4>
                    <div class="coverage-types">
                        {coverage_types_html}
                    </div>
                    
                    {missing_tests_html}
                    {recommendations_html}
                </div>
            </div>
            """
        
        return html
    
    def _generate_by_type_html(self, report: CoverageReport, type_names: Dict[CoverageType, str], 
                              level_colors: Dict[CoverageLevel, str]) -> str:
        """生成按类型分析HTML内容"""
        html = """
        <table>
            <thead>
                <tr>
                    <th>覆盖度类型</th>
                    <th>覆盖度</th>
                    <th>级别</th>
                    <th>进度条</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for coverage_type, coverage_value in report.coverage_by_type.items():
            level = self.calculator.get_coverage_level(coverage_value)
            type_name = type_names.get(coverage_type, coverage_type.value)
            color = level_colors[level]
            
            html += f"""
            <tr>
                <td>{type_name}</td>
                <td>{coverage_value:.1f}%</td>
                <td class="level-{level.value}">{level.value.upper()}</td>
                <td>
                    <div class="mini-bar">
                        <div class="mini-fill" style="width: {coverage_value}%; background-color: {color}"></div>
                    </div>
                </td>
            </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html
    
    def _generate_by_tag_html(self, report: CoverageReport, level_colors: Dict[CoverageLevel, str]) -> str:
        """生成按标签分析HTML内容"""
        html = """
        <table>
            <thead>
                <tr>
                    <th>标签</th>
                    <th>平均覆盖度</th>
                    <th>级别</th>
                    <th>进度条</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for tag, coverage_value in report.coverage_by_tag.items():
            level = self.calculator.get_coverage_level(coverage_value)
            color = level_colors[level]
            
            html += f"""
            <tr>
                <td>{tag}</td>
                <td>{coverage_value:.1f}%</td>
                <td class="level-{level.value}">{level.value.upper()}</td>
                <td>
                    <div class="mini-bar">
                        <div class="mini-fill" style="width: {coverage_value}%; background-color: {color}"></div>
                    </div>
                </td>
            </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html


# 示例使用
if __name__ == "__main__":
    import time
    
    # 创建示例场景
    scenarios = [
        APIScenario(
            scenario_id="scenario_001",
            scenario_name="用户注册登录场景",
            description="用户注册、登录、获取个人信息的完整流程",
            api_endpoints=["/api/register", "/api/login", "/api/user/profile"],
            tags=["authentication", "user"],
            priority="high",
            business_value="high"
        ),
        APIScenario(
            scenario_id="scenario_002",
            scenario_name="商品浏览购买场景",
            description="用户浏览商品、添加购物车、下单支付的完整流程",
            api_endpoints=["/api/products", "/api/cart", "/api/orders", "/api/payments"],
            tags=["e-commerce", "shopping"],
            priority="high",
            business_value="high"
        ),
        APIScenario(
            scenario_id="scenario_003",
            scenario_name="订单管理场景",
            description="用户查看订单、取消订单、申请售后的流程",
            api_endpoints=["/api/orders", "/api/orders/cancel", "/api/refunds"],
            tags=["e-commerce", "order"],
            priority="medium",
            business_value="medium"
        )
    ]
    
    # 创建示例测试用例
    test_cases_by_scenario = {
        "scenario_001": [
            {
                "id": "test_001",
                "functions": ["register", "login", "get_profile"],
                "parameters": [
                    {"name": "username", "value": "testuser"},
                    {"name": "password", "value": "testpass"}
                ],
                "exceptions": [{"type": "invalid_username"}, {"type": "invalid_password"}],
                "business_flow": "complete_registration_login"
            },
            {
                "id": "test_002",
                "functions": ["register", "login"],
                "parameters": [
                    {"name": "username", "value": ""},
                    {"name": "password", "value": ""}
                ],
                "exceptions": [{"type": "invalid_username"}, {"type": "invalid_password"}],
                "business_flow": "failed_registration"
            }
        ],
        "scenario_002": [
            {
                "id": "test_003",
                "functions": ["browse_products", "add_to_cart", "checkout", "payment"],
                "api_sequence": ["/api/products", "/api/cart", "/api/orders", "/api/payments"],
                "business_flow": "complete_purchase"
            }
        ],
        "scenario_003": [
            {
                "id": "test_004",
                "functions": ["view_orders", "cancel_order"],
                "api_sequence": ["/api/orders", "/api/orders/cancel"],
                "business_flow": "cancel_order"
            }
        ]
    }
    
    # 创建覆盖度评分器
    scorer = CoverageScorer()
    
    # 评分
    report = scorer.score_all_scenarios(scenarios, test_cases_by_scenario)
    report.generated_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 生成报告
    reporter = CoverageReporter()
    json_file = reporter.generate_json_report(report)
    html_file = reporter.generate_html_report(report)
    
    print(f"JSON报告已生成: {json_file}")
    print(f"HTML报告已生成: {html_file}")