#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
执行 feishu_unified_generator.py 并按依赖关系顺序执行测试用例

功能：
1. 执行 feishu_unified_generator.py 生成测试用例
2. 根据依赖关系确定测试用例执行顺序
3. 按顺序执行测试用例
4. 生成 Allure 报告

使用方法：
    python run_feishu_generator_and_tests.py --folder interfacetest/interfaceUnion/imageSend
    或
    python run_feishu_generator_and_tests.py --folder interfacetest/interfaceUnion/imageSend --app-id YOUR_APP_ID --app-secret YOUR_APP_SECRET
"""

import os
import sys
import argparse
import traceback
import json
import io
from contextlib import redirect_stdout, redirect_stderr
import glob
import time
import importlib.util
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
import yaml

# 添加项目根目录到路径，并优先加载 .env（与其它工具保持一致）
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv  # type: ignore

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except Exception:
    # 未安装 python-dotenv 不影响运行
    ...

try:
    import pytest
except ImportError:
    print("✗ 错误: 需要安装 pytest 库")
    print("   请运行: pip install pytest")
    sys.exit(1)

from utils.other_tools.allure_config_helper import ensure_allure_properties_file
from utils.other_tools.feishu_unified_generator import FeishuUnifiedGenerator
from utils.read_files_tools.yaml_control import GetYamlData


class TestCaseDependencyResolver:
    """测试用例依赖关系解析器"""
    
    def __init__(self, data_output_dir: str = "open-apis2", generated_yaml_files: List[Path] = None):
        self.data_output_dir = Path(data_output_dir)
        self.test_cases: Dict[str, Dict] = {}  # {case_id: test_case_data}
        self.dependency_graph: Dict[str, List[str]] = {}  # {case_id: [dependent_case_ids]}
        self.generated_yaml_files = generated_yaml_files or []  # 本次生成的 YAML 文件列表
        
    def load_test_cases(self) -> None:
        """加载测试用例（如果指定了 generated_yaml_files，则只加载这些文件）"""
        if not self.data_output_dir.exists():
            print(f"[WARN] 数据目录不存在: {self.data_output_dir}")
            return
        
        # 如果指定了生成的 YAML 文件列表，只加载这些文件
        if self.generated_yaml_files:
            yaml_files = [Path(f) for f in self.generated_yaml_files if Path(f).exists()]
            print(f"[INFO] 只加载本次生成的 {len(yaml_files)} 个 YAML 文件")
        else:
            # 否则加载所有 YAML 文件
            yaml_files = list(self.data_output_dir.rglob("*.yaml"))
            print(f"[INFO] 加载所有 YAML 文件（共 {len(yaml_files)} 个）")
        
        if not yaml_files:
            print(f"[WARN] 在 {self.data_output_dir} 中未找到 YAML 文件")
            return
        
        for yaml_file in yaml_files:
            # 跳过代理拦截文件
            if 'proxy_data.yaml' in str(yaml_file):
                continue
            
            try:
                yaml_data = GetYamlData(str(yaml_file)).get_yaml_data()
                if yaml_data is None:
                    continue
                
                # 提取所有 case_id
                for case_id, case_data in yaml_data.items():
                    if case_id == "case_common":
                        continue
                    
                    if isinstance(case_data, dict):
                        self.test_cases[case_id] = {
                            "case_id": case_id,
                            "yaml_file": str(yaml_file),
                            "dependence_case": case_data.get("dependence_case", False),
                            "dependence_case_data": case_data.get("dependence_case_data", None),
                            "detail": case_data.get("detail", ""),
                        }
            except Exception as e:
                print(f"[WARN] 加载 YAML 文件失败 {yaml_file}: {e}")
                continue
        
        print(f"[OK] 加载了 {len(self.test_cases)} 个测试用例")
    
    def build_dependency_graph(self) -> None:
        """构建依赖关系图"""
        # 初始化图
        for case_id in self.test_cases.keys():
            self.dependency_graph[case_id] = []
        
        # 构建依赖关系
        for case_id, case_info in self.test_cases.items():
            if not case_info.get("dependence_case", False):
                continue
            
            dependence_case_data = case_info.get("dependence_case_data")
            if not dependence_case_data:
                continue
            
            # 处理依赖数据（可能是列表或单个字典）
            if isinstance(dependence_case_data, list):
                for dep_data in dependence_case_data:
                    if isinstance(dep_data, dict):
                        dep_case_id = dep_data.get("case_id")
                        if dep_case_id and dep_case_id in self.test_cases:
                            if dep_case_id not in self.dependency_graph[case_id]:
                                self.dependency_graph[case_id].append(dep_case_id)
            elif isinstance(dependence_case_data, dict):
                dep_case_id = dependence_case_data.get("case_id")
                if dep_case_id and dep_case_id in self.test_cases:
                    if dep_case_id not in self.dependency_graph[case_id]:
                        self.dependency_graph[case_id].append(dep_case_id)
        
        print(f"[OK] 构建依赖关系图完成，共 {len(self.dependency_graph)} 个节点")
    
    def topological_sort(self) -> List[str]:
        """拓扑排序：根据依赖关系确定执行顺序"""
        # 计算每个节点的入度
        in_degree = {case_id: 0 for case_id in self.test_cases.keys()}
        for case_id, deps in self.dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[case_id] += 1
        
        # 找到所有入度为 0 的节点（没有依赖的用例）
        queue = [case_id for case_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 按 case_id 排序，确保稳定性
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            
            # 更新依赖当前节点的其他节点的入度
            for case_id, deps in self.dependency_graph.items():
                if current in deps:
                    in_degree[case_id] -= 1
                    if in_degree[case_id] == 0:
                        queue.append(case_id)
        
        # 处理有循环依赖或不在图中的节点（按原始顺序添加）
        for case_id in self.test_cases.keys():
            if case_id not in result:
                result.append(case_id)
        
        return result
    
    def get_test_files_in_order(self, sorted_case_ids: List[str]) -> List[Path]:
        """根据排序后的 case_id 列表获取测试文件路径（去重）"""
        test_files = []
        seen_files = set()
        
        for case_id in sorted_case_ids:
            if case_id not in self.test_cases:
                continue
            
            yaml_file = Path(self.test_cases[case_id]["yaml_file"])
            
            # 计算对应的测试文件路径
            # yaml_file: open-apis2/open-apis/im/v1/images.yaml
            # test_file: open-apis2/open-apis/im/v1/test_images.py
            # 测试文件与 YAML 文件在同一目录，文件名格式为 test_{yaml_stem}.py
            test_file_path = yaml_file.parent / f"test_{yaml_file.stem}.py"
            
            # 首先尝试在 YAML 文件同目录下查找
            if test_file_path.exists() and str(test_file_path) not in seen_files:
                test_files.append(test_file_path)
                seen_files.add(str(test_file_path))
            else:
                # 如果找不到，尝试在 test_case 目录下查找
                # 计算相对路径：从 data_output_dir 到 yaml_file 的父目录
                try:
                    relative_path = yaml_file.parent.relative_to(self.data_output_dir)
                    test_case_path = Path("test_case") / relative_path / f"test_{yaml_file.stem}.py"
                    if test_case_path.exists() and str(test_case_path) not in seen_files:
                        test_files.append(test_case_path)
                        seen_files.add(str(test_case_path))
                except ValueError:
                    # 如果无法计算相对路径，跳过
                    pass
        
        return test_files

    def map_case_to_test_file(self, case_id: str) -> Optional[Path]:
        """
        根据 case_id 反推出测试文件路径。
        逻辑与 get_test_files_in_order 一致：优先 YAML 同目录的 test_{stem}.py，其次 test_case 目录。
        """
        case_info = self.test_cases.get(case_id)
        if not case_info:
            return None
        yaml_file = Path(case_info["yaml_file"])
        # 优先 YAML 同目录
        test_file_path = yaml_file.parent / f"test_{yaml_file.stem}.py"
        if test_file_path.exists():
            return test_file_path
        # 其次 test_case 目录
        try:
            relative_path = yaml_file.parent.relative_to(self.data_output_dir)
            test_case_path = Path("test_case") / relative_path / f"test_{yaml_file.stem}.py"
            if test_case_path.exists():
                return test_case_path
        except ValueError:
            return None
        return None


class FeishuGeneratorAndTestRunner:
    """飞书测试用例生成和执行器"""
    
    def __init__(self, folder_path: str, app_id: str = None, app_secret: str = None):
        self.folder_path = Path(folder_path)
        self.app_id = app_id
        self.app_secret = app_secret
        self.generator = None
        self.dependency_resolver = None
        
    def step1_run_generator(self) -> bool:
        """步骤1: 执行 feishu_unified_generator.py"""
        print("\n" + "=" * 60)
        print("步骤 1/4: 执行测试用例生成器")
        print("=" * 60)
        
        if not self.folder_path.exists():
            print(f"✗ 错误: 文件夹不存在: {self.folder_path}")
            return False
        
        try:
            # 创建生成器实例
            self.generator = FeishuUnifiedGenerator(
                folder_path=self.folder_path,
                app_id=self.app_id,
                app_secret=self.app_secret
            )
            
            # 执行生成流程
            self.generator.run_all()
            
            print("\n" + "=" * 60)
            print("✓ 测试用例生成完成")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n✗ 生成器执行失败: {e}")
            traceback.print_exc()
            return False
    
    def step2_resolve_dependencies(self) -> List[Path]:
        """步骤2: 解析依赖关系并确定执行顺序"""
        print("\n" + "=" * 60)
        print("步骤 2/4: 解析测试用例依赖关系")
        print("=" * 60)
        
        try:
            # 创建依赖解析器
            data_output_dir = getattr(self.generator, 'data_output_dir', 'open-apis2')
            # 获取本次生成的 YAML 文件列表
            generated_yaml_files = getattr(self.generator, 'generated_yaml_files', [])
            self.dependency_resolver = TestCaseDependencyResolver(
                data_output_dir=data_output_dir,
                generated_yaml_files=generated_yaml_files
            )
            
            # 加载测试用例（只加载本次生成的）
            self.dependency_resolver.load_test_cases()
            
            if not self.dependency_resolver.test_cases:
                print("⚠ 警告: 未找到任何测试用例")
                return []
            
            # 构建依赖图
            self.dependency_resolver.build_dependency_graph()
            
            # 拓扑排序
            sorted_case_ids = self.dependency_resolver.topological_sort()
            
            print(f"\n[OK] 依赖关系排序完成，共 {len(sorted_case_ids)} 个测试用例")
            print("\n执行顺序：")
            for i, case_id in enumerate(sorted_case_ids, 1):
                case_info = self.dependency_resolver.test_cases.get(case_id, {})
                detail = case_info.get("detail", case_id)
                deps = self.dependency_resolver.dependency_graph.get(case_id, [])
                dep_str = f" (依赖: {', '.join(deps)})" if deps else ""
                print(f"  {i}. {case_id}: {detail}{dep_str}")
            
            # 获取测试文件路径
            test_files = self.dependency_resolver.get_test_files_in_order(sorted_case_ids)
            
            if not test_files:
                print("\n⚠ 警告: 未找到任何测试文件")
                return []
            
            print(f"\n[OK] 找到 {len(test_files)} 个测试文件")
            print("\n测试文件执行顺序：")
            for i, test_file in enumerate(test_files, 1):
                print(f"  {i}. {test_file}")
            
            return test_files
            
        except Exception as e:
            print(f"\n✗ 解析依赖关系失败: {e}")
            traceback.print_exc()
            return []
    
    def step3_load_cache(self) -> bool:
        """步骤3.1: 加载测试用例到缓存"""
        print("\n" + "=" * 60)
        print("步骤 3.1/5: 加载测试用例到缓存")
        print("=" * 60)
        
        try:
            # 获取数据输出目录
            data_output_dir = getattr(self.generator, 'data_output_dir', 'open-apis2')
            
            # 方法1: 尝试导入包，触发 __init__.py 执行
            try:
                import importlib
                # 将 data_output_dir 的父目录添加到 Python 路径
                data_dir_path = Path(data_output_dir).absolute()
                parent_path = str(data_dir_path.parent)
                if parent_path not in sys.path:
                    sys.path.insert(0, parent_path)
                
                # 尝试导入包（包名是 data_output_dir 的目录名）
                package_name = data_dir_path.name
                try:
                    # 使用 importlib 动态导入
                    module = importlib.import_module(package_name)
                    print(f"✓ 成功导入 {package_name} 包，缓存已加载")
                except (ImportError, AttributeError) as e:
                    # 如果导入失败，手动加载缓存
                    print(f"⚠ 无法导入包 {package_name}: {e}，尝试手动加载缓存...")
                    self._manual_load_cache(data_output_dir)
            except Exception as e:
                print(f"⚠ 导入包时出错: {e}，尝试手动加载缓存...")
                self._manual_load_cache(data_output_dir)
            
            return True
            
        except Exception as e:
            print(f"\n✗ 加载缓存失败: {e}")
            traceback.print_exc()
            return False
    
    def _manual_load_cache(self, data_output_dir: str) -> None:
        """手动加载缓存"""
        from common.setting import ensure_path_sep
        from utils.read_files_tools.get_yaml_data_analysis import CaseData
        from utils.read_files_tools.get_all_files_path import get_all_files
        from utils.cache_process.cache_control import CacheHandler, _cache_config
        
        print(f"正在从 {data_output_dir} 目录加载 YAML 文件到缓存...")
        
        # 循环拿到所有存放用例的文件路径
        yaml_files = get_all_files(file_path=ensure_path_sep(f"\\{data_output_dir}"), yaml_data_switch=True)
        loaded_count = 0
        
        for yaml_file in yaml_files:
            try:
                # 循环读取文件中的数据
                case_process = CaseData(yaml_file).case_process(case_id_switch=True)
                if case_process is not None:
                    # 转换数据类型
                    for case in case_process:
                        for k, v in case.items():
                            # 判断 case_id 是否已存在
                            case_id_exit = k in _cache_config.keys()
                            # 如果case_id 不存在，则将用例写入缓存池中
                            if case_id_exit is False:
                                CacheHandler.update_cache(cache_name=k, value=v)
                                loaded_count += 1
                            # 当 case_id 为 True 存在时，则抛出异常
                            elif case_id_exit is True:
                                print(f"⚠ 警告: case_id {k} 已存在，跳过")
            except Exception as e:
                print(f"⚠ 警告: 加载 {yaml_file} 时出错: {e}")
                continue
        
        print(f"✓ 成功加载 {loaded_count} 个测试用例到缓存")
    
    def step3_ensure_conftest(self) -> bool:
        """步骤3.2: 确保 conftest.py 存在"""
        try:
            # 获取数据输出目录
            data_output_dir = getattr(self.generator, 'data_output_dir', 'open-apis2')
            conftest_path = Path(data_output_dir) / "conftest.py"
            
            # 如果 conftest.py 不存在，创建它
            if not conftest_path.exists():
                print(f"\n创建 conftest.py 文件: {conftest_path}")
                conftest_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : Auto-generated for open-apis2 test cases
# 此文件用于定义 open-apis2 目录下测试用例需要的 fixture
# 注意：不导入 test_case.conftest，避免触发 test_case/__init__.py 的执行导致 case_id 冲突

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import ast
import allure
from utils.requests_tool.request_control import cache_regular
from utils.other_tools.models import TestCase
from utils.other_tools.allure_data.allure_tools import allure_step, allure_step_no


@pytest.fixture(scope="function", autouse=True)
def case_skip(in_data):
    """处理跳过用例"""
    in_data = TestCase(**in_data)
    if ast.literal_eval(cache_regular(str(in_data.is_run))) is False:
        allure.dynamic.title(in_data.detail)
        allure_step_no(f"请求URL: {in_data.is_run}")
        allure_step_no(f"请求方式: {in_data.method}")
        allure_step("请求头: ", in_data.headers)
        allure_step("请求数据: ", in_data.data)
        allure_step("依赖数据: ", in_data.dependence_case_data)
        allure_step("预期数据: ", in_data.assert_data)
        pytest.skip()


def pytest_configure(config):
    """pytest 配置"""
    config.addinivalue_line("markers", '回归测试')


def pytest_collection_modifyitems(items):
    """
    测试用例收集完成时，将收集到的 item 的 name 和 node_id 的中文显示在控制台上
    """
    for item in items:
        item.name = item.name.encode("utf-8").decode("unicode_escape")
        item._nodeid = item.nodeid.encode("utf-8").decode("unicode_escape")
'''
                conftest_path.parent.mkdir(parents=True, exist_ok=True)
                with conftest_path.open("w", encoding="utf-8") as f:
                    f.write(conftest_content)
                print(f"✓ 已创建 conftest.py")
            else:
                print(f"✓ conftest.py 已存在")
            
            return True
        except Exception as e:
            print(f"⚠ 警告: 创建 conftest.py 时出错: {e}")
            return False
    
    def step3_run_tests(self, test_files: List[Path]) -> Optional[tuple]:
        """步骤3.3: 按顺序执行测试用例，返回 exit_code 和 pytest 输出"""
        print("\n" + "=" * 60)
        print("步骤 3.3/5: 执行测试用例")
        print("=" * 60)
        
        if not test_files:
            print("✗ 错误: 没有可执行的测试用例")
            return None
        
        # 确保 Allure 配置文件存在
        try:
            ensure_allure_properties_file("./report/tmp")
            print("✓ Allure 配置文件已就绪")
        except Exception as e:
            print(f"⚠ 警告: 创建 Allure 配置文件时出错: {e}")
        
        print(f"\n开始执行 {len(test_files)} 个测试文件...")
        print("-" * 60)
        
        # 构建 pytest 参数
        pytest_args = [
            "-s",  # 显示 print 输出
            "-W", "ignore:Module already imported:pytest.PytestWarning",  # 忽略警告
            "--alluredir", "./report/tmp",  # Allure 报告目录
            "--clean-alluredir",  # 清理旧的报告
        ]
        
        # 添加所有测试文件路径（按依赖顺序）
        pytest_args.extend([str(f) for f in test_files])
        
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                exit_code = pytest.main(pytest_args)
            pytest_output = buf.getvalue()
            return exit_code, pytest_output
        except Exception as e:
            print(f"\n✗ 执行测试时出错: {e}")
            traceback.print_exc()
            return None

    def load_latest_results(self) -> Optional[Any]:
        """
        尝试读取 uploads/results 下最新的 results_*.json，返回解析后的数据。
        这是现有框架的落盘结果（通常包含请求/响应等执行详情）。
        """
        try:
            results_dir = Path("uploads") / "results"
            if not results_dir.exists():
                return None
            files = list(results_dir.glob("results_*.json"))
            if not files:
                return None
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            with latest_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def _parse_log_blocks_to_cases(log_text: str, cases_data: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        从 stdout 的日志块中解析用例的请求/响应详情，格式形如：
        用例标题: ...
        请求路径: ...
        请求方式: ...
        请求头:   {...}
        请求内容: {...}
        接口响应内容: {...}
        接口响应时长: xxx ms
        Http状态码: 200
        """
        import re
        import ast
        import json as _json

        if not log_text:
            return None

        # 用例标题 -> case_id 映射
        case_map: Dict[str, Any] = {}
        if isinstance(cases_data, list):
            for c in cases_data:
                detail = c.get("detail")
                if detail:
                    case_map[detail] = c.get("case_id")

        pattern = re.compile(
            r"用例标题:\s*(?P<title>.+?)\n"
            r"请求路径:\s*(?P<url>.+?)\n"
            r"请求方式:\s*(?P<method>\S+)\n"
            r"请求头:\s*(?P<headers>\{.*?\})\n"
            r"请求内容:\s*(?P<body>\{.*?\})\n"
            r"接口响应内容:\s*(?P<resp_body>\{.*?\})\n"
            r"接口响应时长:\s*(?P<elapsed>[\d\.]+)\s*ms\n"
            r"Http状态码:\s*(?P<status>\d+)",
            re.S
        )

        def _parse_obj(text):
            for parser in (
                lambda t: _json.loads(t),
                lambda t: ast.literal_eval(t),
            ):
                try:
                    return parser(text)
                except Exception:
                    continue
            return text

        results: List[Dict[str, Any]] = []
        for m in pattern.finditer(log_text):
            detail = m.group("title").strip()
            results.append({
                "case_id": case_map.get(detail),
                "detail": detail,
                "request": {
                    "method": m.group("method").strip(),
                    "url": m.group("url").strip(),
                    "body": _parse_obj(m.group("body")),
                    "headers": _parse_obj(m.group("headers")),
                },
                "response": {
                    "status_code": int(m.group("status")),
                    "body": _parse_obj(m.group("resp_body")),
                    "headers": None,  # 日志中无响应头，无法获取
                    "elapsed_ms": float(m.group("elapsed")),
                }
            })
        return results or None
    
    def step4_generate_report(self) -> None:
        """步骤4: 跳过 Allure 报告生成（按需可自行生成）"""
        print("\n" + "=" * 60)
        print("步骤 4/5: 跳过 Allure HTML 报告生成")
        print("=" * 60)
        print("已禁用自动生成 Allure 报告，如需报告请手动执行：")
        print("  allure generate ./report/tmp -o ./report/html --clean")
    
    def _check_allure_available(self) -> bool:
        """检查 Allure 命令是否可用"""
        import subprocess
        try:
            # 尝试运行 allure --version 来检查是否可用
            result = subprocess.run(
                ["allure", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
    
    def step5_start_allure_server(self) -> None:
        """步骤5: 跳过 Allure 预览服务器（API 调用场景不启动）"""
        print("\n" + "=" * 60)
        print("步骤 5/5: 跳过 Allure 报告服务器启动")
        print("=" * 60)
        print("已禁用自动启动 Allure 预览，如需预览请手动执行：")
        print("  allure serve ./report/tmp -h 127.0.0.1 -p 9999")
    
    def run_all(self) -> int:
        """执行完整流程"""
        try:
            # 步骤1: 执行生成器
            if not self.step1_run_generator():
                print("\n✗ 生成器执行失败，退出")
                return 1
            
            # 步骤2: 解析依赖关系
            test_files = self.step2_resolve_dependencies()
            if not test_files:
                print("\n⚠ 警告: 未找到测试文件，但生成器已执行完成")
                return 0
            
            # 步骤3.1: 加载缓存
            if not self.step3_load_cache():
                print("\n⚠ 警告: 缓存加载失败，但继续执行测试")
            
            # 步骤3.2: 确保 conftest.py 存在
            self.step3_ensure_conftest()
            
            # 步骤3.3: 执行测试
            run_ret = self.step3_run_tests(test_files)
            if run_ret is None:
                exit_code, pytest_output = 1, ""
            else:
                exit_code, pytest_output = run_ret
            # 跳过 Allure 报告生成和预览
            # self.step4_generate_report()
            # self.step5_start_allure_server()
            
            # 输出总结
            print("\n" + "=" * 60)
            print("执行完成总结")
            print("=" * 60)
            if exit_code == 0:
                print("✓ 所有测试用例执行成功")
            else:
                print(f"⚠ 部分测试用例失败，退出码: {exit_code}")
            print("=" * 60)
            # 从 pytest 输出中解析简单指标（总数、通过数、失败数、耗时）
            def _parse_pytest_metrics(text: str) -> Dict[str, Any]:
                import re
                metrics: Dict[str, Any] = {
                    "total": None,
                    "passed": None,
                    "failed": None,
                    "skipped": None,
                    "duration_seconds": None,
                    "success_rate": None,
                }
                lines = text.splitlines()
                summary_line = ""
                for line in reversed(lines):
                    line = line.strip()
                    if " passed" in line and " in " in line:
                        summary_line = line
                        break
                if not summary_line:
                    return metrics

                # 例如： "2 passed in 1.82s" 或 "1 passed, 1 failed in 3.01s"
                m = re.search(r"(?P<passed>\d+)\s+passed", summary_line)
                if m:
                    metrics["passed"] = int(m.group("passed"))
                m = re.search(r"(?P<failed>\d+)\s+failed", summary_line)
                if m:
                    metrics["failed"] = int(m.group("failed"))
                m = re.search(r"(?P<skipped>\d+)\s+skipped", summary_line)
                if m:
                    metrics["skipped"] = int(m.group("skipped"))
                m = re.search(r"in\s+(?P<duration>[\d\.]+)s", summary_line)
                if m:
                    try:
                        metrics["duration_seconds"] = float(m.group("duration"))
                    except ValueError:
                        pass

                # 计算总数和成功率
                total = 0
                for key in ("passed", "failed", "skipped"):
                    if isinstance(metrics.get(key), int):
                        total += metrics[key]  # type: ignore[operator]
                metrics["total"] = total or None
                if total and isinstance(metrics.get("passed"), int):
                    metrics["success_rate"] = round(metrics["passed"] * 100.0 / total, 2)  # type: ignore[operator]
                return metrics

            metrics = _parse_pytest_metrics(pytest_output)

            # 以机器可读的 JSON 形式输出结果，便于 api_server.py 获取
            # 附加每个用例的明细（case_id、detail、yaml_file、test_file）
            cases = []
            if self.dependency_resolver and self.dependency_resolver.test_cases:
                for cid, info in self.dependency_resolver.test_cases.items():
                    cases.append({
                        "case_id": cid,
                        "detail": info.get("detail"),
                        "yaml_file": info.get("yaml_file"),
                        "test_file": str(self.dependency_resolver.map_case_to_test_file(cid) or "")
                    })

            # 加载最新的测试执行结果（包含 stdout 日志）并尝试结构化请求/响应
            latest_responses = self.load_latest_results()
            structured_responses = None
            if isinstance(latest_responses, dict):
                stdout_text = latest_responses.get("stdout") if isinstance(latest_responses.get("stdout"), str) else ""
                stderr_text = latest_responses.get("stderr") if isinstance(latest_responses.get("stderr"), str) else ""
                combined_text = f"{stdout_text}\n{stderr_text}"
                if combined_text.strip():
                    structured_responses = self._parse_log_blocks_to_cases(combined_text, cases)
                # 如果已有结构化列表，则直接透传
                if structured_responses is None and isinstance(latest_responses.get("responses"), list):
                    structured_responses = latest_responses.get("responses")

            result = {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "test_files": [str(f) for f in test_files],
                "cases": cases,
                "metrics": metrics,
                "pytest_output": pytest_output,
                "pytest_output_length": len(pytest_output) if pytest_output else 0,
                # 返回结构化的请求/响应
                "responses": structured_responses,
                "app_id": self.app_id,
                "folder": str(self.folder_path),
            }
            print(json.dumps(result, ensure_ascii=False))
            return exit_code
            
        except KeyboardInterrupt:
            print("\n\n用户中断，正在退出...")
            sys.exit(130)
        except Exception as e:
            print(f"\n✗ 执行过程中出错: {e}")
            traceback.print_exc()
            return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="执行 feishu_unified_generator.py 并按依赖关系顺序执行测试用例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置
  python run_feishu_generator_and_tests.py --folder interfacetest/interfaceUnion/imageSend
  
  # 指定 App ID 和 Secret
  python run_feishu_generator_and_tests.py \\
      --folder interfacetest/interfaceUnion/imageSend \\
      --app-id YOUR_APP_ID \\
      --app-secret YOUR_APP_SECRET
        """
    )
    
    parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="包含 OpenAPI YAML 文件的文件夹路径"
    )
    
    parser.add_argument(
        "--app-id",
        type=str,
        default=None,
        help="飞书应用 App ID (默认读取环境变量 FEISHU_APP_ID 或配置)"
    )
    
    parser.add_argument(
        "--app-secret",
        type=str,
        default=None,
        help="飞书应用 App Secret (默认读取环境变量 FEISHU_APP_SECRET 或配置)"
    )
    
    args = parser.parse_args()
    
    # 优先使用命令行参数，其次环境变量
    app_id = args.app_id or os.getenv("FEISHU_APP_ID")
    app_secret = args.app_secret or os.getenv("FEISHU_APP_SECRET")
    
    try:
        runner = FeishuGeneratorAndTestRunner(
            folder_path=args.folder,
            app_id=app_id,
            app_secret=app_secret
        )
        exit_code = runner.run_all()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断，退出")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] 执行出错: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

