"""
运行报告和指标分析模块

该模块负责收集测试执行数据、生成测试报告并提供指标分析功能。
支持生成HTML报告、分析测试覆盖度、识别测试瓶颈等功能。
"""

import os
import json
import time
import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """测试状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestPriority(Enum):
    """测试优先级枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestResult:
    """单个测试结果"""
    test_id: str
    test_name: str
    test_case_id: str
    test_suite: str
    status: TestStatus
    duration: float  # 执行时间，单位秒
    start_time: datetime.datetime
    end_time: datetime.datetime
    error_message: Optional[str] = None
    assertion_results: List[Dict[str, Any]] = field(default_factory=list)
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    priority: TestPriority = TestPriority.MEDIUM
    tags: List[str] = field(default_factory=list)


@dataclass
class TestSuiteResult:
    """测试套件结果"""
    suite_name: str
    test_results: List[TestResult] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    total_duration: float = 0.0
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    
    def __post_init__(self):
        """初始化后计算统计数据"""
        self.calculate_statistics()
    
    def calculate_statistics(self):
        """计算测试套件统计信息"""
        self.total_tests = len(self.test_results)
        self.passed_tests = sum(1 for test in self.test_results if test.status == TestStatus.PASSED)
        self.failed_tests = sum(1 for test in self.test_results if test.status == TestStatus.FAILED)
        self.skipped_tests = sum(1 for test in self.test_results if test.status == TestStatus.SKIPPED)
        self.error_tests = sum(1 for test in self.test_results if test.status == TestStatus.ERROR)
        
        if self.test_results:
            self.total_duration = sum(test.duration for test in self.test_results)
            start_times = [test.start_time for test in self.test_results if test.start_time]
            end_times = [test.end_time for test in self.test_results if test.end_time]
            
            if start_times:
                self.start_time = min(start_times)
            if end_times:
                self.end_time = max(end_times)
    
    def get_pass_rate(self) -> float:
        """获取通过率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    def get_average_duration(self) -> float:
        """获取平均执行时间"""
        if self.total_tests == 0:
            return 0.0
        return self.total_duration / self.total_tests


@dataclass
class TestReport:
    """测试报告"""
    report_id: str
    report_name: str
    test_suites: List[TestSuiteResult] = field(default_factory=list)
    generated_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    environment_info: Dict[str, Any] = field(default_factory=dict)
    
    def get_total_tests(self) -> int:
        """获取总测试数"""
        return sum(suite.total_tests for suite in self.test_suites)
    
    def get_total_passed(self) -> int:
        """获取总通过数"""
        return sum(suite.passed_tests for suite in self.test_suites)
    
    def get_total_failed(self) -> int:
        """获取总失败数"""
        return sum(suite.failed_tests for suite in self.test_suites)
    
    def get_total_skipped(self) -> int:
        """获取总跳过数"""
        return sum(suite.skipped_tests for suite in self.test_suites)
    
    def get_total_errors(self) -> int:
        """获取总错误数"""
        return sum(suite.error_tests for suite in self.test_suites)
    
    def get_overall_pass_rate(self) -> float:
        """获取总体通过率"""
        total = self.get_total_tests()
        if total == 0:
            return 0.0
        return (self.get_total_passed() / total) * 100
    
    def get_total_duration(self) -> float:
        """获取总执行时间"""
        return sum(suite.total_duration for suite in self.test_suites)


class ReportAnalyzer:
    """报告分析器"""
    
    def __init__(self, report: TestReport):
        self.report = report
    
    def analyze_test_performance(self) -> Dict[str, Any]:
        """分析测试性能"""
        all_tests = []
        for suite in self.report.test_suites:
            all_tests.extend(suite.test_results)
        
        if not all_tests:
            return {"error": "没有测试数据可供分析"}
        
        durations = [test.duration for test in all_tests]
        
        return {
            "total_tests": len(all_tests),
            "average_duration": statistics.mean(durations),
            "median_duration": statistics.median(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "slowest_tests": sorted(all_tests, key=lambda x: x.duration, reverse=True)[:5],
            "fastest_tests": sorted(all_tests, key=lambda x: x.duration)[:5]
        }
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """分析失败模式"""
        failed_tests = []
        for suite in self.report.test_suites:
            failed_tests.extend([test for test in suite.test_results 
                               if test.status in [TestStatus.FAILED, TestStatus.ERROR]])
        
        if not failed_tests:
            return {"message": "没有失败的测试"}
        
        # 按错误消息分组
        error_groups = {}
        for test in failed_tests:
            error_msg = test.error_message or "未知错误"
            if error_msg not in error_groups:
                error_groups[error_msg] = []
            error_groups[error_msg].append(test)
        
        # 找出最常见的错误
        common_errors = sorted(error_groups.items(), 
                              key=lambda x: len(x[1]), reverse=True)
        
        return {
            "total_failures": len(failed_tests),
            "failure_rate": (len(failed_tests) / self.report.get_total_tests()) * 100,
            "common_errors": [{"error": error, "count": len(tests), "tests": tests} 
                             for error, tests in common_errors[:5]],
            "failed_test_suites": list(set(test.test_suite for test in failed_tests))
        }
    
    def analyze_test_coverage(self) -> Dict[str, Any]:
        """分析测试覆盖度"""
        # 这里可以扩展为更详细的覆盖度分析
        # 目前只提供基本的覆盖度统计
        
        all_tags = set()
        for suite in self.report.test_suites:
            for test in suite.test_results:
                all_tags.update(test.tags)
        
        tag_coverage = {}
        for tag in all_tags:
            tag_tests = []
            for suite in self.report.test_suites:
                for test in suite.test_results:
                    if tag in test.tags:
                        tag_tests.append(test)
            
            if tag_tests:
                passed = sum(1 for test in tag_tests if test.status == TestStatus.PASSED)
                tag_coverage[tag] = {
                    "total": len(tag_tests),
                    "passed": passed,
                    "failed": len(tag_tests) - passed,
                    "pass_rate": (passed / len(tag_tests)) * 100
                }
        
        return {
            "total_tags": len(all_tags),
            "tag_coverage": tag_coverage
        }
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成测试摘要"""
        return {
            "report_id": self.report.report_id,
            "report_name": self.report.report_name,
            "generated_time": self.report.generated_time.isoformat(),
            "environment": self.report.environment_info,
            "total_suites": len(self.report.test_suites),
            "total_tests": self.report.get_total_tests(),
            "passed_tests": self.report.get_total_passed(),
            "failed_tests": self.report.get_total_failed(),
            "skipped_tests": self.report.get_total_skipped(),
            "error_tests": self.report.get_total_errors(),
            "pass_rate": self.report.get_overall_pass_rate(),
            "total_duration": self.report.get_total_duration()
        }


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_json_report(self, report: TestReport) -> str:
        """生成JSON格式报告"""
        report_data = {
            "report_id": report.report_id,
            "report_name": report.report_name,
            "generated_time": report.generated_time.isoformat(),
            "environment_info": report.environment_info,
            "summary": {
                "total_suites": len(report.test_suites),
                "total_tests": report.get_total_tests(),
                "passed_tests": report.get_total_passed(),
                "failed_tests": report.get_total_failed(),
                "skipped_tests": report.get_total_skipped(),
                "error_tests": report.get_total_errors(),
                "pass_rate": report.get_overall_pass_rate(),
                "total_duration": report.get_total_duration()
            },
            "test_suites": []
        }
        
        for suite in report.test_suites:
            suite_data = {
                "suite_name": suite.suite_name,
                "total_tests": suite.total_tests,
                "passed_tests": suite.passed_tests,
                "failed_tests": suite.failed_tests,
                "skipped_tests": suite.skipped_tests,
                "error_tests": suite.error_tests,
                "pass_rate": suite.get_pass_rate(),
                "total_duration": suite.total_duration,
                "start_time": suite.start_time.isoformat() if suite.start_time else None,
                "end_time": suite.end_time.isoformat() if suite.end_time else None,
                "test_results": []
            }
            
            for test in suite.test_results:
                test_data = {
                    "test_id": test.test_id,
                    "test_name": test.test_name,
                    "test_case_id": test.test_case_id,
                    "status": test.status.value,
                    "duration": test.duration,
                    "start_time": test.start_time.isoformat(),
                    "end_time": test.end_time.isoformat(),
                    "error_message": test.error_message,
                    "priority": test.priority.value,
                    "tags": test.tags,
                    "request_data": test.request_data,
                    "response_data": test.response_data,
                    "assertion_results": test.assertion_results
                }
                suite_data["test_results"].append(test_data)
            
            report_data["test_suites"].append(suite_data)
        
        # 保存JSON报告
        report_file = self.output_dir / f"{report.report_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(report_file)
    
    def generate_html_report(self, report: TestReport) -> str:
        """生成HTML格式报告"""
        analyzer = ReportAnalyzer(report)
        summary = analyzer.generate_summary()
        performance = analyzer.analyze_test_performance()
        failures = analyzer.analyze_failure_patterns()
        coverage = analyzer.analyze_test_coverage()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.report_name} - 测试报告</title>
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
        .summary-card.pass {{
            border-left-color: #2ecc71;
        }}
        .summary-card.fail {{
            border-left-color: #e74c3c;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 16px;
        }}
        .summary-card .value {{
            font-size: 24px;
            font-weight: bold;
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
        .status-pass {{
            color: #2ecc71;
        }}
        .status-fail {{
            color: #e74c3c;
        }}
        .status-skip {{
            color: #f39c12;
        }}
        .status-error {{
            color: #9b59b6;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-pass {{
            height: 100%;
            background-color: #2ecc71;
            float: left;
        }}
        .progress-fail {{
            height: 100%;
            background-color: #e74c3c;
            float: left;
        }}
        .progress-skip {{
            height: 100%;
            background-color: #f39c12;
            float: left;
        }}
        .progress-error {{
            height: 100%;
            background-color: #9b59b6;
            float: left;
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
        .error-message {{
            background-color: #ffeaea;
            padding: 10px;
            border-radius: 4px;
            margin-top: 5px;
            font-family: monospace;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report.report_name}</h1>
        <p>报告生成时间: {report.generated_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>总测试数</h3>
                <div class="value">{summary['total_tests']}</div>
            </div>
            <div class="summary-card pass">
                <h3>通过</h3>
                <div class="value">{summary['passed_tests']}</div>
            </div>
            <div class="summary-card fail">
                <h3>失败</h3>
                <div class="value">{summary['failed_tests']}</div>
            </div>
            <div class="summary-card">
                <h3>跳过</h3>
                <div class="value">{summary['skipped_tests']}</div>
            </div>
            <div class="summary-card">
                <h3>错误</h3>
                <div class="value">{summary['error_tests']}</div>
            </div>
            <div class="summary-card pass">
                <h3>通过率</h3>
                <div class="value">{summary['pass_rate']:.2f}%</div>
            </div>
            <div class="summary-card">
                <h3>总耗时</h3>
                <div class="value">{summary['total_duration']:.2f}s</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-pass" style="width: {summary['pass_rate']:.2f}%"></div>
            <div class="progress-fail" style="width: {(summary['failed_tests']/summary['total_tests']*100) if summary['total_tests'] > 0 else 0}%"></div>
            <div class="progress-skip" style="width: {(summary['skipped_tests']/summary['total_tests']*100) if summary['total_tests'] > 0 else 0}%"></div>
            <div class="progress-error" style="width: {(summary['error_tests']/summary['total_tests']*100) if summary['total_tests'] > 0 else 0}%"></div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('test-suites')">测试套件</div>
            <div class="tab" onclick="showTab('performance')">性能分析</div>
            <div class="tab" onclick="showTab('failures')">失败分析</div>
            <div class="tab" onclick="showTab('coverage')">覆盖度分析</div>
        </div>
        
        <div id="test-suites" class="tab-content active">
            <h2>测试套件详情</h2>
            {self._generate_test_suites_html(report)}
        </div>
        
        <div id="performance" class="tab-content">
            <h2>性能分析</h2>
            {self._generate_performance_html(performance)}
        </div>
        
        <div id="failures" class="tab-content">
            <h2>失败分析</h2>
            {self._generate_failures_html(failures)}
        </div>
        
        <div id="coverage" class="tab-content">
            <h2>覆盖度分析</h2>
            {self._generate_coverage_html(coverage)}
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
    
    def _generate_test_suites_html(self, report: TestReport) -> str:
        """生成测试套件HTML内容"""
        html = ""
        
        for suite in report.test_suites:
            html += f"""
            <h3>{suite.suite_name}</h3>
            <table>
                <thead>
                    <tr>
                        <th>测试用例</th>
                        <th>状态</th>
                        <th>耗时(秒)</th>
                        <th>错误信息</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for test in suite.test_results:
                status_class = f"status-{test.status.value}"
                error_msg = test.error_message or ""
                
                html += f"""
                <tr>
                    <td>{test.test_name}</td>
                    <td class="{status_class}">{test.status.value.upper()}</td>
                    <td>{test.duration:.3f}</td>
                    <td>{error_msg}</td>
                </tr>
                """
            
            html += """
                </tbody>
            </table>
            """
        
        return html
    
    def _generate_performance_html(self, performance: Dict[str, Any]) -> str:
        """生成性能分析HTML内容"""
        if "error" in performance:
            return f"<p>{performance['error']}</p>"
        
        html = f"""
        <div class="summary">
            <div class="summary-card">
                <h3>平均执行时间</h3>
                <div class="value">{performance['average_duration']:.3f}s</div>
            </div>
            <div class="summary-card">
                <h3>中位数执行时间</h3>
                <div class="value">{performance['median_duration']:.3f}s</div>
            </div>
            <div class="summary-card">
                <h3>最短执行时间</h3>
                <div class="value">{performance['min_duration']:.3f}s</div>
            </div>
            <div class="summary-card">
                <h3>最长执行时间</h3>
                <div class="value">{performance['max_duration']:.3f}s</div>
            </div>
        </div>
        
        <h3>最慢的5个测试</h3>
        <table>
            <thead>
                <tr>
                    <th>测试用例</th>
                    <th>执行时间(秒)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for test in performance.get("slowest_tests", []):
            html += f"""
            <tr>
                <td>{test.test_name}</td>
                <td>{test.duration:.3f}</td>
            </tr>
            """
        
        html += """
            </tbody>
        </table>
        
        <h3>最快的5个测试</h3>
        <table>
            <thead>
                <tr>
                    <th>测试用例</th>
                    <th>执行时间(秒)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for test in performance.get("fastest_tests", []):
            html += f"""
            <tr>
                <td>{test.test_name}</td>
                <td>{test.duration:.3f}</td>
            </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html
    
    def _generate_failures_html(self, failures: Dict[str, Any]) -> str:
        """生成失败分析HTML内容"""
        if "message" in failures:
            return f"<p>{failures['message']}</p>"
        
        html = f"""
        <div class="summary">
            <div class="summary-card fail">
                <h3>失败总数</h3>
                <div class="value">{failures['total_failures']}</div>
            </div>
            <div class="summary-card fail">
                <h3>失败率</h3>
                <div class="value">{failures['failure_rate']:.2f}%</div>
            </div>
        </div>
        
        <h3>常见错误</h3>
        """
        
        for error_info in failures.get("common_errors", []):
            error = error_info["error"]
            count = error_info["count"]
            tests = error_info["tests"]
            
            html += f"""
            <div style="margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 5px;">
                <h4>错误 (出现 {count} 次)</h4>
                <div class="error-message">{error}</div>
                
                <h5>受影响的测试用例:</h5>
                <ul>
            """
            
            for test in tests:
                html += f"<li>{test.test_name} ({test.test_suite})</li>"
            
            html += """
                </ul>
            </div>
            """
        
        return html
    
    def _generate_coverage_html(self, coverage: Dict[str, Any]) -> str:
        """生成覆盖度分析HTML内容"""
        html = f"""
        <div class="summary">
            <div class="summary-card">
                <h3>总标签数</h3>
                <div class="value">{coverage['total_tags']}</div>
            </div>
        </div>
        
        <h3>标签覆盖度</h3>
        <table>
            <thead>
                <tr>
                    <th>标签</th>
                    <th>测试数</th>
                    <th>通过数</th>
                    <th>失败数</th>
                    <th>通过率</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for tag, data in coverage.get("tag_coverage", {}).items():
            html += f"""
            <tr>
                <td>{tag}</td>
                <td>{data['total']}</td>
                <td>{data['passed']}</td>
                <td>{data['failed']}</td>
                <td>{data['pass_rate']:.2f}%</td>
            </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html


class TestExecutor:
    """测试执行器"""
    
    def __init__(self):
        self.current_report = None
        self.current_suite = None
    
    def start_report(self, report_name: str, environment_info: Dict[str, Any] = None) -> str:
        """开始一个新的测试报告"""
        report_id = f"report_{int(time.time())}"
        self.current_report = TestReport(
            report_id=report_id,
            report_name=report_name,
            environment_info=environment_info or {}
        )
        return report_id
    
    def start_suite(self, suite_name: str) -> str:
        """开始一个新的测试套件"""
        if not self.current_report:
            raise ValueError("必须先开始一个测试报告")
        
        self.current_suite = TestSuiteResult(suite_name=suite_name)
        return suite_name
    
    def add_test_result(self, 
                        test_id: str,
                        test_name: str,
                        test_case_id: str,
                        status: TestStatus,
                        duration: float,
                        start_time: datetime.datetime,
                        end_time: datetime.datetime,
                        error_message: Optional[str] = None,
                        assertion_results: List[Dict[str, Any]] = None,
                        request_data: Dict[str, Any] = None,
                        response_data: Dict[str, Any] = None,
                        priority: TestPriority = TestPriority.MEDIUM,
                        tags: List[str] = None) -> None:
        """添加测试结果"""
        if not self.current_suite:
            raise ValueError("必须先开始一个测试套件")
        
        test_result = TestResult(
            test_id=test_id,
            test_name=test_name,
            test_case_id=test_case_id,
            test_suite=self.current_suite.suite_name,
            status=status,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            error_message=error_message,
            assertion_results=assertion_results or [],
            request_data=request_data or {},
            response_data=response_data or {},
            priority=priority,
            tags=tags or []
        )
        
        self.current_suite.test_results.append(test_result)
    
    def end_suite(self) -> None:
        """结束当前测试套件"""
        if not self.current_suite:
            return
        
        self.current_suite.calculate_statistics()
        self.current_report.test_suites.append(self.current_suite)
        self.current_suite = None
    
    def end_report(self) -> TestReport:
        """结束当前测试报告并返回"""
        if not self.current_report:
            raise ValueError("没有活动的测试报告")
        
        # 确保所有套件都已结束
        if self.current_suite:
            self.end_suite()
        
        report = self.current_report
        self.current_report = None
        return report


# 示例使用
if __name__ == "__main__":
    # 创建测试执行器
    executor = TestExecutor()
    
    # 开始报告
    report_id = executor.start_report(
        "示例测试报告",
        environment_info={
            "python_version": "3.8.10",
            "pytest_version": "6.2.5",
            "platform": "Linux"
        }
    )
    
    # 开始第一个测试套件
    executor.start_suite("用户管理API测试")
    
    # 添加测试结果
    start_time = datetime.datetime.now()
    time.sleep(0.1)  # 模拟测试执行时间
    end_time = datetime.datetime.now()
    
    executor.add_test_result(
        test_id="test_001",
        test_name="测试用户登录",
        test_case_id="TC001",
        status=TestStatus.PASSED,
        duration=0.1,
        start_time=start_time,
        end_time=end_time,
        tags=["authentication", "smoke"]
    )
    
    # 添加失败的测试
    start_time = datetime.datetime.now()
    time.sleep(0.2)  # 模拟测试执行时间
    end_time = datetime.datetime.now()
    
    executor.add_test_result(
        test_id="test_002",
        test_name="测试用户注册",
        test_case_id="TC002",
        status=TestStatus.FAILED,
        duration=0.2,
        start_time=start_time,
        end_time=end_time,
        error_message="AssertionError: Expected status code 201 but got 400",
        tags=["authentication", "registration"]
    )
    
    # 结束第一个测试套件
    executor.end_suite()
    
    # 开始第二个测试套件
    executor.start_suite("产品管理API测试")
    
    # 添加测试结果
    start_time = datetime.datetime.now()
    time.sleep(0.15)  # 模拟测试执行时间
    end_time = datetime.datetime.now()
    
    executor.add_test_result(
        test_id="test_003",
        test_name="测试获取产品列表",
        test_case_id="TC003",
        status=TestStatus.PASSED,
        duration=0.15,
        start_time=start_time,
        end_time=end_time,
        tags=["products", "list"]
    )
    
    # 结束第二个测试套件
    executor.end_suite()
    
    # 结束报告
    report = executor.end_report()
    
    # 生成报告
    generator = ReportGenerator()
    json_file = generator.generate_json_report(report)
    html_file = generator.generate_html_report(report)
    
    print(f"JSON报告已生成: {json_file}")
    print(f"HTML报告已生成: {html_file}")