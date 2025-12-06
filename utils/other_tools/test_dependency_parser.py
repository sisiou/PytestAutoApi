#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
依赖关系解析测试程序

功能：
1. 加载并解析依赖关系 JSON 文件
2. 输出所有 API 的依赖关系信息
3. 构建依赖关系图
4. 输出拓扑排序结果

使用方法：
    python utils/other_tools/test_dependency_parser.py --json interfacetest/interfaceUnion/api_relation_bailian_da093a41.json
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.other_tools.feishu_unified_generator import FeishuUnifiedGenerator


class DependencyParser:
    """依赖关系解析器"""
    
    def __init__(self, relation_json_path: Path):
        self.relation_json_path = relation_json_path
        self.api_relations = []
        # 使用 FeishuUnifiedGenerator 来解析依赖关系（包含反向推导逻辑）
        self.generator = FeishuUnifiedGenerator(
            folder_path=relation_json_path.parent,
            relation_json_path=relation_json_path
        )
        self.api_relations = self.generator.api_relations
        print(f"[OK] 已加载 {len(self.api_relations)} 个接口的依赖关系")
    
    def print_all_dependencies(self):
        """输出所有 API 的依赖关系"""
        print("\n" + "=" * 80)
        print("所有 API 的依赖关系")
        print("=" * 80)
        
        for i, relation in enumerate(self.api_relations, 1):
            api_path = relation.get("api_path", "未知")
            api_name = relation.get("api_name", "未知")
            
            print(f"\n[{i}] {api_name}")
            print(f"    API 路径: {api_path}")
            
            # 全局依赖
            global_deps = relation.get("global_dependent_apis", [])
            if global_deps:
                print(f"    全局依赖 ({len(global_deps)} 个):")
                for dep in global_deps:
                    print(f"      - {dep}")
            else:
                print(f"    全局依赖: 无")
            
            # 条件依赖（使用 generator 的方法，包含反向推导）
            dependent_apis = self.generator._get_dependent_apis(api_path)
            # 过滤出条件依赖（排除全局依赖）
            global_deps = relation.get("global_dependent_apis", [])
            global_dep_paths = set(global_deps)
            conditional_deps_from_generator = [
                dep for dep in dependent_apis 
                if dep.get("api_path") not in global_dep_paths
            ]
            
            if conditional_deps_from_generator:
                print(f"    条件依赖 ({len(conditional_deps_from_generator)} 个):")
                for dep in conditional_deps_from_generator:
                    dep_path = dep.get("api_path", "未知")
                    optional = dep.get("optional", False)
                    trigger_conditions = dep.get("trigger_conditions", [])
                    
                    # 判断是否是反向推导的依赖
                    is_reverse = dep_path not in [
                        d.get("dependent_api_path", "") 
                        for d in relation.get("conditional_dependent_apis", [])
                    ]
                    reverse_mark = " (反向推导)" if is_reverse else ""
                    
                    print(f"      - {dep_path} {'(可选)' if optional else '(必需)'}{reverse_mark}")
                    if trigger_conditions:
                        for condition in trigger_conditions:
                            param_name = condition.get("param_name", "")
                            param_location = condition.get("param_location", "")
                            match_rule = condition.get("match_rule", "")
                            print(f"        触发条件: {param_location}.{param_name} {match_rule}")
                    
                    # 参数映射
                    param_mapping = dep.get("param_mapping", [])
                    if param_mapping:
                        print(f"        参数映射:")
                        for mapping in param_mapping:
                            source = mapping.get("source_param", "")
                            target = mapping.get("target_param", "")
                            target_location = mapping.get("target_param_location", "body")
                            mapping_rule = mapping.get("mapping_rule", "")
                            print(f"          {source} -> {target_location}.{target}")
                            if mapping_rule:
                                print(f"            规则: {mapping_rule}")
            else:
                print(f"    条件依赖: 无")
            
            # 输出参数
            data_flow = relation.get("data_flow", {})
            output_dest = data_flow.get("output_data_dest", [])
            if output_dest:
                print(f"    输出参数:")
                for dest in output_dest:
                    api_path = dest.get("api_path", "")
                    params = dest.get("params", [])
                    print(f"      -> {api_path}: {', '.join(params)}")
            else:
                print(f"    输出参数: 无")
    
    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """构建依赖关系图（使用 FeishuUnifiedGenerator 的方法，包含反向推导）"""
        graph = defaultdict(list)
        
        # 收集所有 API 路径
        all_api_paths = set()
        for relation in self.api_relations:
            api_path = relation.get("api_path", "")
            if api_path:
                all_api_paths.add(api_path)
        
        # 使用 FeishuUnifiedGenerator 的方法获取每个 API 的依赖
        for relation in self.api_relations:
            api_path = relation.get("api_path", "")
            if not api_path:
                continue
            
            # 使用 generator 的方法获取依赖（包含反向推导）
            dependent_apis = self.generator._get_dependent_apis(api_path)
            
            for dep in dependent_apis:
                dep_path = dep.get("api_path", "")
                if dep_path and dep_path in all_api_paths:
                    if dep_path not in graph[api_path]:
                        graph[api_path].append(dep_path)
        
        return dict(graph)
    
    def print_dependency_graph(self):
        """输出依赖关系图"""
        print("\n" + "=" * 80)
        print("依赖关系图")
        print("=" * 80)
        
        graph = self.build_dependency_graph()
        
        if not graph:
            print("  无依赖关系")
            return
        
        for api_path, deps in sorted(graph.items()):
            if deps:
                print(f"\n  {api_path}")
                print(f"    依赖: {', '.join(deps)}")
            else:
                print(f"\n  {api_path}")
                print(f"    依赖: 无")
    
    def topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序（修正版：确保依赖的接口先执行）"""
        # 计算入度（有多少个接口依赖当前接口）
        in_degree = defaultdict(int)
        all_apis = set(graph.keys())
        
        # 收集所有 API（包括被依赖的 API）
        for deps in graph.values():
            for dep in deps:
                all_apis.add(dep)
        
        # 初始化所有节点的入度
        for api in all_apis:
            in_degree[api] = 0
        
        # 计算每个节点的入度（有多少个依赖）
        for api, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[api] += 1  # api 依赖 dep，所以 api 的入度+1
        
        # 找到所有入度为 0 的节点（没有依赖的接口）
        queue = [api for api, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            
            # 更新依赖当前节点的其他节点的入度
            # 如果 current 是某个接口的依赖，那么该接口的入度减1
            for api, deps in graph.items():
                if current in deps:
                    in_degree[api] -= 1
                    if in_degree[api] == 0:
                        queue.append(api)
        
        # 处理有循环依赖或不在图中的节点
        remaining = [api for api in all_apis if api not in result]
        if remaining:
            result.extend(remaining)
        
        return result
    
    def print_execution_order(self):
        """输出执行顺序"""
        print("\n" + "=" * 80)
        print("建议的执行顺序（拓扑排序）")
        print("=" * 80)
        
        graph = self.build_dependency_graph()
        sorted_apis = self.topological_sort(graph)
        
        if not sorted_apis:
            print("  无 API 需要排序")
            return
        
        print(f"\n  共 {len(sorted_apis)} 个 API，执行顺序如下：\n")
        for i, api_path in enumerate(sorted_apis, 1):
            deps = graph.get(api_path, [])
            if deps:
                print(f"  {i:2d}. {api_path}")
                print(f"      依赖: {', '.join(deps)}")
            else:
                print(f"  {i:2d}. {api_path} (无依赖)")
    
    def print_param_mapping_summary(self):
        """输出参数映射摘要（使用 generator 的方法，包含反向推导）"""
        print("\n" + "=" * 80)
        print("参数映射摘要")
        print("=" * 80)
        
        mapping_count = 0
        for relation in self.api_relations:
            api_path = relation.get("api_path", "")
            # 使用 generator 的方法获取依赖（包含反向推导）
            dependent_apis = self.generator._get_dependent_apis(api_path)
            
            for dep in dependent_apis:
                param_mapping = dep.get("param_mapping", [])
                if param_mapping:
                    dep_path = dep.get("api_path", "")
                    # 判断是否是反向推导的依赖
                    is_reverse = dep_path not in [
                        d.get("dependent_api_path", "") 
                        for d in relation.get("conditional_dependent_apis", [])
                    ] and dep_path not in relation.get("global_dependent_apis", [])
                    reverse_mark = " (反向推导)" if is_reverse else ""
                    
                    print(f"\n  {api_path} <- {dep_path}{reverse_mark}")
                    for mapping in param_mapping:
                        mapping_count += 1
                        source = mapping.get("source_param", "")
                        target = mapping.get("target_param", "")
                        target_location = mapping.get("target_param_location", "body")
                        mapping_rule = mapping.get("mapping_rule", "")
                        print(f"    {source} -> {target_location}.{target}")
                        if mapping_rule:
                            print(f"      规则: {mapping_rule}")
        
        if mapping_count == 0:
            print("  无参数映射")
        else:
            print(f"\n  共 {mapping_count} 个参数映射")
    
    def print_output_params_summary(self):
        """输出输出参数摘要"""
        print("\n" + "=" * 80)
        print("输出参数摘要（用于缓存）")
        print("=" * 80)
        
        output_count = 0
        for relation in self.api_relations:
            api_path = relation.get("api_path", "")
            data_flow = relation.get("data_flow", {})
            output_dest = data_flow.get("output_data_dest", [])
            
            if output_dest:
                print(f"\n  {api_path}")
                for dest in output_dest:
                    dest_api = dest.get("api_path", "")
                    params = dest.get("params", [])
                    if params:
                        output_count += len(params)
                        print(f"    -> {dest_api}: {', '.join(params)}")
                        for param in params:
                            print(f"       缓存键: redis:{param}")
        
        if output_count == 0:
            print("  无输出参数")
        else:
            print(f"\n  共 {output_count} 个输出参数需要缓存")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="依赖关系解析测试程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认路径（在 interfacetest/interfaceUnion 目录下查找）
  python utils/other_tools/test_dependency_parser.py
  
  # 指定 JSON 文件路径
  python utils/other_tools/test_dependency_parser.py --json interfacetest/interfaceUnion/api_relation_bailian_da093a41.json
        """
    )
    
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="依赖关系 JSON 文件路径（默认在 interfacetest/interfaceUnion 目录下查找 api_relation_*.json）"
    )
    
    parser.add_argument(
        "--summary",
        action="store_true",
        help="只输出摘要信息（不输出详细依赖关系）"
    )
    
    args = parser.parse_args()
    
    # 确定 JSON 文件路径
    if args.json:
        relation_json_path = Path(args.json)
    else:
        # 默认在 interfacetest/interfaceUnion 目录下查找
        default_dir = project_root / "interfacetest" / "interfaceUnion"
        relation_files = list(default_dir.glob("api_relation_*.json"))
        if relation_files:
            relation_json_path = relation_files[0]
            print(f"[INFO] 使用默认文件: {relation_json_path}")
        else:
            print(f"[ERROR] 未找到依赖关系文件，请使用 --json 参数指定")
            sys.exit(1)
    
    if not relation_json_path.exists():
        print(f"[ERROR] 文件不存在: {relation_json_path}")
        sys.exit(1)
    
    # 创建解析器
    parser = DependencyParser(relation_json_path)
    
    if args.summary:
        # 只输出摘要
        parser.print_dependency_graph()
        parser.print_execution_order()
        parser.print_param_mapping_summary()
        parser.print_output_params_summary()
    else:
        # 输出完整信息
        parser.print_all_dependencies()
        parser.print_dependency_graph()
        parser.print_execution_order()
        parser.print_param_mapping_summary()
        parser.print_output_params_summary()
    
    print("\n" + "=" * 80)
    print("解析完成")
    print("=" * 80)


if __name__ == "__main__":
    main()

