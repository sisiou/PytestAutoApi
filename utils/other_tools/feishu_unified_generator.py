#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用飞书接口测试用例生成器

功能：
1. 扫描指定文件夹下的多个 OpenAPI YAML 文件
2. 根据 YAML 文件中的 `order` 属性确定执行顺序
3. 按顺序为每个文件生成对应的测试用例

使用方法：
    python utils/other_tools/feishu_unified_generator.py --folder interfacetest/interfaceUnion/imageSend
    或
    python utils/other_tools/feishu_unified_generator.py --folder interfacetest/interfaceUnion/imageSend --app-id YOUR_APP_ID --app-secret YOUR_APP_SECRET
"""

import sys
import argparse
import os
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import ruamel.yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
except ImportError:
    requests = None

from utils.read_files_tools.case_automatic_control import TestCaseAutomaticGeneration
from utils.other_tools.allure_config_helper import ensure_allure_properties_file


# ================= 配置区域 =================
DEFAULT_APP_ID = os.getenv("FEISHU_APP_ID")
DEFAULT_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
DEFAULT_USER_ID = os.getenv("FEISHU_USER_ID")


DEFAULT_RECEIVE_ID_TYPE = "user_id"
DEFAULT_RECEIVE_ID = DEFAULT_USER_ID  # 使用配置文件中的user_id
RECEIVE_ID_MAP = {
    "user_id": DEFAULT_USER_ID,  # 使用配置文件中的user_id
    "open_id": "ou_0d83637fb561cdc1e0562991339c713b",  # open_id 格式示例
    "union_id": "on_17df3bf51632401d3ab42d6c7a6e32d8",  # union_id 格式示例
    "email": "user@example.com",  # email 格式示例
    "chat_id": "oc_5ad11d72b830411d72b836c20",  # chat_id 格式示例
}
# ===========================================
class OpenAPIFileInfo:
    """OpenAPI 文件信息"""
    def __init__(self, file_path: Path, order: int):
        self.file_path = file_path
        self.order = order
        self.yaml_data = None
        self.api_path = None
        self.operation_id = None
        
    def load_yaml(self) -> bool:
        """加载 YAML 文件并提取关键信息"""
        try:
            yaml = ruamel.yaml.YAML()
            with self.file_path.open("r", encoding="utf-8") as f:
                self.yaml_data = yaml.load(f) or {}
            
            # 提取 API 路径和操作 ID
            if "paths" in self.yaml_data:
                paths = self.yaml_data["paths"]
                for path_key, path_value in paths.items():
                    if isinstance(path_value, dict):
                        for method, operation in path_value.items():
                            if isinstance(operation, dict) and "operationId" in operation:
                                self.api_path = path_key
                                self.operation_id = operation.get("operationId")
                                return True
            return False
        except Exception as e:
            print(f"[ERROR] 加载 YAML 文件失败 {self.file_path}: {e}")
            return False
    
    def __repr__(self):
        return f"OpenAPIFileInfo(path={self.file_path.name}, order={self.order}, api_path={self.api_path})"


def _sanitize_path_for_filename(path: str) -> str:
    """清理路径参数，使其适合作为文件名
    
    Args:
        path: API 路径，可能包含路径参数如 {calendar_id}
    
    Returns:
        清理后的路径，路径参数被移除或替换为通用名称
    """
    import re
    # 将 {param_name} 替换为 param_name（移除花括号）
    # 例如: /calendar/v4/calendars/{calendar_id} -> /calendar/v4/calendars/calendar_id
    sanitized = re.sub(r'\{([^}]+)\}', r'\1', path)
    return sanitized


def _sanitize_for_filename(name: str) -> str:
    """清理字符串，使其适合作为文件名（保留下划线分隔）
    
    Args:
        name: 原始名称，可能包含花括号等
    
    Returns:
        适合作为文件名的字符串（保留下划线，移除花括号）
    """
    import re
    # 移除花括号
    name = re.sub(r'[{}]', '', name)
    # 移除所有非字母数字下划线字符
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return name


def _sanitize_for_python_identifier(name: str) -> str:
    """清理字符串，使其成为有效的 Python 标识符（驼峰命名）
    
    Args:
        name: 原始名称，可能包含花括号、连字符等
    
    Returns:
        有效的 Python 标识符（驼峰命名）
    """
    import re
    # 移除花括号
    name = re.sub(r'[{}]', '', name)
    # 将连字符和下划线后的字符转为大写（用于驼峰命名）
    # 例如: calendar_id -> calendarId
    parts = re.split(r'[-_]', name)
    if len(parts) > 1:
        # 第一个部分小写，后续部分首字母大写
        name = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
    else:
        name = name.lower()
    # 移除所有非字母数字字符（不保留下划线，因为已经是驼峰命名）
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    # 确保以字母或下划线开头
    if name and not name[0].isalpha() and name[0] != '_':
        name = '_' + name
    return name


class FeishuUnifiedGenerator:
    """通用飞书接口测试用例生成器"""
    
    def __init__(self, folder_path: Path, app_id: str = None, app_secret: str = None, 
                 relation_json_path: Path = None, data_output_dir: str = "open-apis2", 
                 test_output_dir: str = "open-apis2"):
        self.folder_path = Path(folder_path)
        self.app_id = app_id or DEFAULT_APP_ID
        self.app_secret = app_secret or DEFAULT_APP_SECRET
        self.openapi_files: List[OpenAPIFileInfo] = []
        self.token: Optional[str] = None
        # 输出目录配置
        self.data_output_dir = data_output_dir  # YAML 文件输出目录
        self.test_output_dir = test_output_dir  # 测试代码输出目录
        # 记录本次生成的所有 YAML 文件路径
        self.generated_yaml_files: List[Path] = []
        # 默认值配置（可以从模块级别常量获取）
        self.default_receive_id_type = DEFAULT_RECEIVE_ID_TYPE
        self.default_receive_id = DEFAULT_RECEIVE_ID
        self.receive_id_map = RECEIVE_ID_MAP  # ID 类型映射表
        
        # 依赖关系 JSON 文件路径
        if relation_json_path:
            self.relation_json_path = Path(relation_json_path)
        else:
            # 优先查找 uploads/relation/ 目录下的 api_relation_*.json 文件
            # 如果 folder_path 在 uploads/scene/ 下，则从 uploads/relation/ 查找
            relation_json_path = None
            if "uploads" in str(self.folder_path):
                # 如果路径包含 uploads，尝试从 uploads/relation/ 查找
                uploads_root = self.folder_path
                # 向上查找 uploads 根目录
                while uploads_root.name != "uploads" and uploads_root.parent != uploads_root:
                    uploads_root = uploads_root.parent
                if uploads_root.name == "uploads":
                    relation_dir = uploads_root / "relation"
                    if relation_dir.exists():
                        relation_files = list(relation_dir.glob("api_relation_*.json"))
                        if relation_files:
                            relation_json_path = relation_files[0]
                            print(f"[INFO] 从 uploads/relation/ 找到依赖关系文件: {relation_json_path}")
            
            # 如果还没找到，尝试在 folder_path 的父目录下查找
            if not relation_json_path:
                parent_dir = self.folder_path.parent
                relation_files = list(parent_dir.glob("api_relation_*.json"))
                if relation_files:
                    relation_json_path = relation_files[0]
                    print(f"[INFO] 从父目录找到依赖关系文件: {relation_json_path}")
            
            if relation_json_path:
                self.relation_json_path = relation_json_path
            else:
                self.relation_json_path = None
                print(f"[WARN] 未找到依赖关系文件，已尝试从 uploads/relation/ 和父目录查找")
        self.api_relations: Dict = {}
        self._load_api_relations()
        
    def scan_yaml_files(self) -> List[OpenAPIFileInfo]:
        """扫描文件夹下的所有 YAML 文件（不再依赖 order 属性）"""
        if not self.folder_path.exists():
            print(f"[ERROR] 文件夹不存在 {self.folder_path}")
            return []
        
        yaml_files = []
        for yaml_file in self.folder_path.glob("*.yaml"):
            if yaml_file.is_file():
                # 不再读取 order，直接加载文件
                file_info = OpenAPIFileInfo(yaml_file, 0)  # order 设为 0，后续根据依赖关系排序
                if file_info.load_yaml():
                    yaml_files.append(file_info)
                else:
                    print(f"[WARN] 警告: 无法加载 {yaml_file.name}，跳过")
        
        return yaml_files
    
    def _load_api_relations(self):
        """加载 API 依赖关系 JSON 文件"""
        if not self.relation_json_path or not self.relation_json_path.exists():
            print(f"[WARN] 依赖关系文件不存在，将不处理接口依赖")
            return
        
        try:
            import json
            with self.relation_json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self.api_relations = data.get("relation_info", {}).get("relations", [])
                print(f"[OK] 已加载 {len(self.api_relations)} 个接口的依赖关系")
        except Exception as e:
            print(f"[ERROR] 加载依赖关系文件失败: {e}")
            self.api_relations = []
    
    def _find_relation_for_api(self, api_path: str) -> Optional[Dict]:
        """查找指定 API 的依赖关系"""
        # 确保路径包含 open-apis 前缀
        if not api_path.startswith("/open-apis"):
            api_path = "/open-apis" + api_path
        
        for relation in self.api_relations:
            if relation.get("api_path") == api_path:
                return relation
        return None
    
    def _get_dependent_apis(self, api_path: str) -> List[Dict]:
        """获取指定 API 的所有依赖接口"""
        relation = self._find_relation_for_api(api_path)
        if not relation:
            return []
        
        dependent_apis = []
        # 全局依赖
        global_deps = relation.get("global_dependent_apis", [])
        for dep_api in global_deps:
            dependent_apis.append({
                "api_path": dep_api,
                "optional": False,
                "param_mapping": []
            })
        
        # 条件依赖
        conditional_deps = relation.get("conditional_dependent_apis", [])
        for dep in conditional_deps:
            dependent_apis.append({
                "api_path": dep.get("dependent_api_path"),
                "optional": dep.get("optional", False),
                "param_mapping": dep.get("param_mapping", []),
                "trigger_conditions": dep.get("trigger_conditions", [])
            })
        
        # 从 data_flow.conditional_input 中解析依赖关系
        # 这用于处理那些在 conditional_dependent_apis 中没有定义，但在 conditional_input 中定义的依赖
        data_flow = relation.get("data_flow", {})
        conditional_input = data_flow.get("conditional_input", [])
        for input_item in conditional_input:
            input_api_path = input_item.get("api_path", "")
            input_params = input_item.get("params", [])
            
            if input_api_path:
                # 检查是否已经存在这个依赖（避免重复）
                existing = False
                for dep in dependent_apis:
                    if dep.get("api_path") == input_api_path:
                        existing = True
                        break
                
                if not existing:
                    # 构建参数映射：从输入 API 的输出参数映射到当前 API 的路径参数或请求参数
                    param_mapping = []
                    for param in input_params:
                        # 尝试从其他接口的 output_data_dest 中找到参数映射规则
                        # 如果找不到，使用默认映射：参数名相同
                        param_mapping.append({
                            "source_param": param,
                            "source_param_type": "string",
                            "target_param": param,  # 默认映射到同名参数
                            "target_param_location": "path",  # 默认是路径参数（如 calendar_id）
                            "mapping_rule": f"直接传递 {param} 参数"
                        })
                    
                    dependent_apis.append({
                        "api_path": input_api_path,
                        "optional": False,  # conditional_input 中的依赖通常是必需的
                        "param_mapping": param_mapping,
                        "trigger_conditions": []
                    })
        
        # 反向推导：根据其他接口的 output_data_dest 推导依赖关系
        # 如果其他接口的输出参数指向当前接口，且当前接口需要这些参数，则建立依赖
        import re
        
        # 提取当前接口的路径参数（支持 {param} 和 :param 两种格式）
        path_params_from_braces = re.findall(r'\{([^}]+)\}', api_path)
        path_params_from_colon = re.findall(r':(\w+)', api_path)
        path_params = list(set(path_params_from_braces + path_params_from_colon))
        
        if path_params:
            # 查找所有其他接口，看它们的 output_data_dest 是否指向当前接口
            for other_relation in self.api_relations:
                other_api_path = other_relation.get("api_path", "")
                if other_api_path == api_path:
                    continue  # 跳过自己
                
                other_data_flow = other_relation.get("data_flow", {})
                other_output_dest = other_data_flow.get("output_data_dest", [])
                
                for dest in other_output_dest:
                    dest_api_path = dest.get("api_path", "")
                    dest_params = dest.get("params", [])
                    
                    # 检查目标 API 路径是否匹配当前接口（支持路径参数匹配）
                    # 例如：/open-apis/calendar/v4/calendars/:calendar_id 匹配 /open-apis/calendar/v4/calendars/{calendar_id}
                    if dest_api_path:
                        # 将路径参数格式统一（:param 和 {param} 都视为相同）
                        normalized_dest = re.sub(r':(\w+)', r'{\1}', dest_api_path)
                        normalized_current = re.sub(r':(\w+)', r'{\1}', api_path)
                        
                        # 提取路径的基础部分（去掉参数）
                        # 将 :param 和 {param} 都替换为空，只保留基础路径
                        base_dest = re.sub(r'[:\{][^}/]+', '', normalized_dest)
                        base_current = re.sub(r'[:\{][^}/]+', '', normalized_current)
                        
                        # 如果基础路径匹配，且参数名匹配，则建立依赖
                        if base_dest == base_current:
                            for param in dest_params:
                                if param in path_params:
                                    # 检查是否已经存在这个依赖
                                    existing = False
                                    for dep in dependent_apis:
                                        if dep.get("api_path") == other_api_path:
                                            # 检查参数映射中是否已有这个参数
                                            for mapping in dep.get("param_mapping", []):
                                                if mapping.get("source_param") == param:
                                                    existing = True
                                                    break
                                            if existing:
                                                break
                                    
                                    if not existing:
                                        # 添加到依赖列表
                                        # 查找是否已有这个 API 的依赖
                                        dep_found = None
                                        for dep in dependent_apis:
                                            if dep.get("api_path") == other_api_path:
                                                dep_found = dep
                                                break
                                        
                                        if dep_found:
                                            # 添加参数映射
                                            dep_found["param_mapping"].append({
                                                "source_param": param,
                                                "source_param_type": "string",
                                                "target_param": param,
                                                "target_param_location": "path",
                                                "mapping_rule": f"直接传递 {param} 作为路径参数"
                                            })
                                        else:
                                            # 创建新的依赖
                                            dependent_apis.append({
                                                "api_path": other_api_path,
                                                "optional": False,
                                                "param_mapping": [{
                                                    "source_param": param,
                                                    "source_param_type": "string",
                                                    "target_param": param,
                                                    "target_param_location": "path",
                                                    "mapping_rule": f"直接传递 {param} 作为路径参数"
                                                }],
                                                "trigger_conditions": []
                                            })
        
        return dependent_apis
    
    def _get_output_params(self, api_path: str) -> List[str]:
        """获取指定 API 的输出参数（用于设置缓存）"""
        relation = self._find_relation_for_api(api_path)
        if not relation:
            return []
        
        data_flow = relation.get("data_flow", {})
        output_dest = data_flow.get("output_data_dest", [])
        
        output_params = []
        for dest in output_dest:
            params = dest.get("params", [])
            output_params.extend(params)
        
        return list(set(output_params))  # 去重
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """构建依赖关系图，返回 {api_path: [依赖的api_path列表]}"""
        graph = {}
        api_paths = set()
        
        # 收集所有 API 路径
        for file_info in self.openapi_files:
            if file_info.api_path:
                full_path = file_info.api_path
                if not full_path.startswith("/open-apis"):
                    full_path = "/open-apis" + full_path
                api_paths.add(full_path)
                graph[full_path] = []
        
        # 根据依赖关系 JSON 构建图
        for relation in self.api_relations:
            api_path = relation.get("api_path", "")
            if not api_path:
                continue
            
            # 全局依赖
            global_deps = relation.get("global_dependent_apis", [])
            for dep in global_deps:
                if dep in api_paths:
                    if api_path not in graph:
                        graph[api_path] = []
                    if dep not in graph[api_path]:
                        graph[api_path].append(dep)
            
            # 条件依赖
            conditional_deps = relation.get("conditional_dependent_apis", [])
            for dep in conditional_deps:
                dep_api_path = dep.get("dependent_api_path", "")
                if dep_api_path and dep_api_path in api_paths:
                    if api_path not in graph:
                        graph[api_path] = []
                    if dep_api_path not in graph[api_path]:
                        graph[api_path].append(dep_api_path)
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]], api_path_to_file: Dict[str, OpenAPIFileInfo]) -> List[OpenAPIFileInfo]:
        """拓扑排序：根据依赖关系确定执行顺序"""
        # 计算每个节点的入度
        in_degree = {api: 0 for api in graph.keys()}
        for api, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[api] += 1
        
        # 找到所有入度为 0 的节点（没有依赖的接口）
        queue = [api for api, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 按 API 路径排序，确保稳定性
            queue.sort()
            current = queue.pop(0)
            
            # 添加到结果
            if current in api_path_to_file:
                result.append(api_path_to_file[current])
            
            # 更新依赖当前节点的其他节点的入度
            for api, deps in graph.items():
                if current in deps:
                    in_degree[api] -= 1
                    if in_degree[api] == 0:
                        queue.append(api)
        
        # 处理有循环依赖或不在图中的节点（按原始顺序添加）
        for file_info in self.openapi_files:
            if file_info not in result:
                result.append(file_info)
        
        return result
    
    def get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        if requests is None:
            print("[ERROR] 错误: 需要安装 requests 库才能获取 token")
            return None
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                expire = data.get("expire", 0)
                print(f"[OK] 成功获取 tenant_access_token (过期时间: {expire} 秒)")
                return token
            print(f"[ERROR] 获取 token 失败: code={data.get('code')} msg={data.get('msg')}")
            return None
        except Exception as exc:
            print(f"[ERROR] 获取 token 出错: {exc}")
            return None
    
    def _create_generic_swagger_generator(self, file_info: OpenAPIFileInfo):
        """创建通用的 OpenAPI YAML 生成器"""
        class GenericOpenAPIGenerator:
            """通用的 OpenAPI YAML 生成器，支持任何 OpenAPI 3.0 规范文件"""
            
            _class_yaml_path: Optional[str] = None
            
            def __init__(self, yaml_path: Path, generator_instance):
                from utils.read_files_tools.swagger_for_yaml import SwaggerForYaml
                # 设置类级路径
                GenericOpenAPIGenerator._class_yaml_path = str(yaml_path)
                # 创建基类实例，但需要重写 get_swagger_json
                self._base_swagger = SwaggerForYaml.__new__(SwaggerForYaml)
                self._base_swagger._data = self.get_swagger_json()
                self._base_swagger._host = self._base_swagger.get_host()
                self.yaml_path = yaml_path
                self._generator = generator_instance  # 保存生成器实例，用于访问依赖关系
                # 保存文件名，用于特殊处理
                self.yaml_file_name = yaml_path.name
                
            @classmethod
            def get_swagger_json(cls):
                """从 YAML 文件读取 OpenAPI 数据"""
                try:
                    import yaml
                except ImportError as e:
                    raise ImportError("缺少依赖 yaml，请安装 pyyaml: pip install pyyaml") from e
                
                if not cls._class_yaml_path:
                    raise RuntimeError("未设置 _class_yaml_path")
                
                path = Path(cls._class_yaml_path)
                try:
                    with path.open("r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except FileNotFoundError as e:
                    raise FileNotFoundError(f"OpenAPI 文件不存在: {path}") from e
            
            def get_allure_epic(self):
                """获取 allure epic"""
                if "info" in self._base_swagger._data and "title" in self._base_swagger._data["info"]:
                    return self._base_swagger._data["info"]["title"]
                return "API 接口测试"
            
            def get_allure_feature(self, value):
                """获取 allure feature"""
                try:
                    if value.get("tags"):
                        return value["tags"][0] if isinstance(value["tags"], list) else value["tags"]
                except Exception:
                    pass
                return value.get("summary") or "接口测试"
            
            def get_allure_story(self, value):
                """获取 allure story"""
                return value.get("summary") or "接口调用"
            
            def get_detail(self, value):
                """获取用例详情"""
                summary = value.get("summary")
                if summary:
                    return "测试" + summary
                return "测试接口调用"
            
            def get_case_id(self, value):
                """生成 case_id"""
                # 确保路径包含 open-apis 前缀
                if not value.startswith("/open-apis"):
                    value = "/open-apis" + value
                # 清理路径参数，移除花括号
                sanitized_value = _sanitize_path_for_filename(value)
                _case_id = sanitized_value.replace("/", "_")
                return "01" + _case_id
            
            def _get_parameter_example(self, param: dict):
                """获取参数的示例值"""
                schema = param.get("schema", {})
                example = param.get("example")
                if example is not None:
                    return example
                
                # 从 schema 中获取示例值
                if schema:
                    example = schema.get("example")
                    if example is not None:
                        return example
                    
                    # 如果有枚举值，使用第一个
                    enum_values = schema.get("enum", [])
                    if enum_values:
                        return enum_values[0]
                    
                    # 使用默认值
                    default = schema.get("default")
                    if default is not None:
                        return default
                
                return None
            
            def _get_response_schema(self, v: dict) -> dict:
                """从 OpenAPI 操作定义中获取响应 schema"""
                responses = v.get("responses", {})
                # 优先使用 200 响应
                success_response = responses.get("200") or responses.get("201") or responses.get("204")
                if not success_response:
                    # 如果没有 200，使用第一个响应
                    success_response = list(responses.values())[0] if responses else {}
                
                if not success_response:
                    return {}
                
                content = success_response.get("content", {})
                if not content:
                    return {}
                
                # 获取第一个 content type 的 schema
                content_type = list(content.keys())[0] if content else None
                if not content_type:
                    return {}
                
                schema_ref = content[content_type].get("schema", {})
                schema = schema_ref
                
                # 如果是引用，需要解析
                if isinstance(schema_ref, dict) and "$ref" in schema_ref:
                    ref_path = schema_ref["$ref"]
                    if ref_path.startswith("#/components/schemas/"):
                        schema_name = ref_path.split("/")[-1]
                        components = self._base_swagger._data.get("components", {})
                        schemas = components.get("schemas", {})
                        schema = schemas.get(schema_name, {})
                
                return schema if isinstance(schema, dict) else {}
            
            def _find_param_jsonpath(self, schema: dict, param_name: str, current_path: str = "$.data") -> str:
                """递归查找参数在响应 schema 中的 jsonpath"""
                if not isinstance(schema, dict):
                    return ""
                
                # 检查当前层级的 properties
                properties = schema.get("properties", {})
                if param_name in properties:
                    return f"{current_path}.{param_name}"
                
                # 递归检查每个属性（但跳过与参数名相同的属性，避免无限递归）
                for prop_name, prop_schema in properties.items():
                    if prop_name == param_name:
                        # 如果属性名与参数名相同，已经在上面处理了
                        continue
                    
                    if not isinstance(prop_schema, dict):
                        continue
                    
                    # 如果是对象类型，递归查找
                    if prop_schema.get("type") == "object" or "$ref" in prop_schema:
                        # 解析引用
                        resolved_schema = prop_schema
                        if "$ref" in prop_schema:
                            ref_path = prop_schema["$ref"]
                            if ref_path.startswith("#/components/schemas/"):
                                schema_name = ref_path.split("/")[-1]
                                components = self._base_swagger._data.get("components", {})
                                schemas = components.get("schemas", {})
                                resolved_schema = schemas.get(schema_name, {})
                        
                        # 递归查找
                        nested_path = f"{current_path}.{prop_name}"
                        result = self._find_param_jsonpath(resolved_schema, param_name, nested_path)
                        if result:
                            return result
                
                return ""
            
            def _extract_request_body_data(self, v: dict, dependent_fields: set = None, receive_id_type: str = None) -> dict:
                """从 requestBody 中提取请求体数据
                
                Args:
                    v: OpenAPI 操作定义
                    dependent_fields: 会通过依赖用例填充的字段集合（字段名）
                    receive_id_type: receive_id_type 查询参数的值（用于从映射表中选择对应的 receive_id）
                """
                from jsonpath import jsonpath
                body_data = {}
                
                if dependent_fields is None:
                    dependent_fields = set()
                
                request_body = v.get("requestBody")
                if not request_body:
                    return body_data
                
                content = request_body.get("content", {})
                if not content:
                    return body_data
                
                # 获取第一个 content type 的 schema
                content_type = list(content.keys())[0] if content else None
                if not content_type:
                    return body_data
                
                schema_ref = content[content_type].get("schema", {})
                schema = schema_ref
                
                # 如果是引用，需要解析
                if isinstance(schema_ref, dict) and "$ref" in schema_ref:
                    ref_path = schema_ref["$ref"]
                    if ref_path.startswith("#/components/schemas/"):
                        schema_name = ref_path.split("/")[-1]
                        components = self._base_swagger._data.get("components", {})
                        schemas = components.get("schemas", {})
                        schema = schemas.get(schema_name, {})
                
                if not isinstance(schema, dict):
                    return body_data
                
                # 获取必需字段
                required_fields = schema.get("required", [])
                properties = schema.get("properties", {})
                
                # 第一遍：为所有字段生成默认值（除了 content，需要特殊处理）
                for prop_name, prop_schema in properties.items():
                    if not isinstance(prop_schema, dict):
                        continue
                    
                    # content 字段稍后特殊处理
                    if prop_name == "content":
                        continue
                    
                    # 获取示例值或默认值
                    example_value = prop_schema.get("example")
                    default_value = prop_schema.get("default")
                    enum_values = prop_schema.get("enum", [])
                    
                    # 检查是否是 ID 类型字段（通常需要从依赖用例或实际环境中获取）
                    is_id_field = (
                        prop_name.endswith("_id") or 
                        prop_name.endswith("Id") or 
                        prop_name.endswith("ID") or
                        prop_name == "id" or
                        "id" in prop_name.lower()
                    )
                    
                    # 特殊处理：如果是 receive_id 字段，且提供了 receive_id_type，优先从映射表选择
                    # 这样可以确保 receive_id 和 receive_id_type 匹配
                    # 但如果该字段会通过依赖用例填充，则不设置值
                    if prop_name == "receive_id":
                        if prop_name in dependent_fields:
                            # 该字段会通过依赖用例填充，不设置默认值
                            body_data[prop_name] = None
                        elif receive_id_type and receive_id_type in self._generator.receive_id_map:
                            # 从映射表中选择对应的 ID，忽略示例值
                            body_data[prop_name] = self._generator.receive_id_map[receive_id_type]
                        elif example_value is not None:
                            # 如果映射表中没有，但有示例值，使用示例值
                            body_data[prop_name] = example_value
                        elif default_value is not None:
                            body_data[prop_name] = default_value
                        elif prop_name in required_fields:
                            # 必需字段但没有值，设为空字符串，后续会应用默认值
                            body_data[prop_name] = ""
                        else:
                            body_data[prop_name] = None
                    elif prop_name == "uuid":
                        # uuid 字段：每次生成时使用随机 UUID，忽略示例值和默认值
                        # 但如果该字段会通过依赖用例填充，则不设置值
                        if prop_name in dependent_fields:
                            # 该字段会通过依赖用例填充，不设置默认值
                            body_data[prop_name] = None
                        else:
                            # 生成随机 UUID
                            body_data[prop_name] = str(uuid.uuid4())
                    elif prop_name == "msg_type":
                        # 特殊情况：如果是特定文件，强制使用 image
                        # 检查是否是特定文件：openapi_server-docs_im-v1_message_create_e4166feb.yaml
                        if "openapi_server-docs_im-v1_message_create_e4166feb.yaml" in self.yaml_file_name:
                            body_data[prop_name] = "image"
                        elif example_value is not None:
                            body_data[prop_name] = example_value
                        elif default_value is not None:
                            body_data[prop_name] = default_value
                        elif enum_values:
                            body_data[prop_name] = enum_values[0]
                        elif prop_name in required_fields:
                            body_data[prop_name] = "text"  # 默认使用 text
                        else:
                            body_data[prop_name] = None
                    elif example_value is not None:
                        # 有明确的示例值，使用它
                        body_data[prop_name] = example_value
                    elif default_value is not None:
                        # 有默认值，使用它
                        body_data[prop_name] = default_value
                    elif enum_values:
                        # 有枚举值，使用第一个
                        body_data[prop_name] = enum_values[0]
                    elif prop_name in required_fields:
                        # 必需字段但没有默认值
                        # 如果该字段会通过依赖用例填充，则不设置默认值（设为 None，后续会被过滤）
                        # 依赖用例会通过 replace_key 来填充该字段
                        if prop_name in dependent_fields:
                            # 该字段会通过依赖用例填充，不设置默认值
                            body_data[prop_name] = None
                        else:
                            prop_type = prop_schema.get("type", "string")
                            if is_id_field:
                                # ID 类型字段：设为空字符串，避免使用无效的硬编码示例值
                                # 用户需要手动填写或通过依赖用例获取（通过 dependence_case_data 配置）
                                body_data[prop_name] = ""  # 保留字段但设为空，用户需要填写
                            elif prop_type == "string":
                                body_data[prop_name] = ""
                            elif prop_type == "integer":
                                body_data[prop_name] = 0
                            elif prop_type == "boolean":
                                body_data[prop_name] = False
                            elif prop_type == "array":
                                body_data[prop_name] = []
                            else:
                                body_data[prop_name] = None
                    else:
                        # 可选字段，设为 None（后续会被过滤）
                        body_data[prop_name] = None
                
                # 第二遍：特殊处理 content 字段（需要根据 msg_type 生成）
                if "content" in properties:
                    content_schema = properties["content"]
                    if isinstance(content_schema, dict):
                        # 检查是否有 msg_type 字段
                        msg_type = body_data.get("msg_type", "text")
                        if msg_type == "text":
                            body_data["content"] = '{"text":"测试消息"}'
                        elif msg_type == "image":
                            # 图片消息：content 需要包含 image_key（通常从依赖用例获取）
                            # 使用缓存引用格式，依赖用例会通过缓存填充（使用 $cache{redis:image_key} 格式）
                            body_data["content"] = '{"image_key":"$cache{redis:image_key}"}'
                        elif msg_type == "file":
                            # 文件消息：content 需要包含 file_key
                            body_data["content"] = '{"file_key":"$cache{redis:file_key}"}'
                        elif msg_type == "audio":
                            # 音频消息：content 需要包含 file_key
                            body_data["content"] = '{"file_key":"$cache{redis:file_key}"}'
                        elif msg_type == "media":
                            # 视频消息：content 需要包含 file_key
                            body_data["content"] = '{"file_key":"$cache{redis:file_key}"}'
                        elif msg_type == "sticker":
                            # 表情包消息：content 需要包含 sticker_id
                            body_data["content"] = '{"sticker_id":"test_sticker_id"}'
                        elif msg_type == "share_chat":
                            # 群名片消息：content 需要包含 share_chat_id
                            body_data["content"] = '{"share_chat_id":"oc_test_chat_id"}'
                        elif msg_type == "share_user":
                            # 个人名片消息：content 需要包含 user_id
                            body_data["content"] = '{"user_id":"ou_test_user_id"}'
                        elif msg_type == "system":
                            # 系统消息：content 需要包含 text
                            body_data["content"] = '{"text":"系统消息"}'
                        elif msg_type == "interactive":
                            body_data["content"] = '{"elements":[{"tag":"markdown","content":"测试卡片消息"}]}'
                        elif "content" in required_fields:
                            # 必需字段但没有特殊处理，使用空 JSON
                            body_data["content"] = '{}'
                        else:
                            # 可选字段，设为 None
                            body_data["content"] = None
                
                # 过滤掉 None 值（可选字段），但保留空字符串（必需字段的占位符）
                body_data = {k: v for k, v in body_data.items() if v is not None}
                
                # 应用默认值：如果 receive_id 字段存在但为空字符串，且不会通过依赖填充
                # 注意：如果 receive_id 已经在上面根据 receive_id_type 设置了，这里不会再次设置
                if "receive_id" in body_data:
                    if body_data["receive_id"] == "" and "receive_id" not in dependent_fields:
                        # 如果还没有根据 receive_id_type 设置，尝试使用默认值
                        if receive_id_type and receive_id_type in self._generator.receive_id_map:
                            # 这种情况理论上不应该发生，因为上面已经处理了
                            body_data["receive_id"] = self._generator.receive_id_map[receive_id_type]
                        else:
                            # 如果没有匹配的映射，使用默认值
                            default_value = self._generator.default_receive_id
                            if default_value:
                                body_data["receive_id"] = default_value
                
                return body_data
            
            def _separate_query_and_body_params(self, v: dict, dependent_fields: set = None) -> Tuple[dict, dict, str]:
                """分离查询参数和请求体参数
                
                Args:
                    v: OpenAPI 操作定义
                    dependent_fields: 会通过依赖用例填充的字段集合（字段名）
                
                Returns:
                    (query_params, body_data, receive_id_type) 元组
                    - query_params: 查询参数字典
                    - body_data: 请求体数据字典
                    - receive_id_type: receive_id_type 查询参数的值（如果有）
                """
                from jsonpath import jsonpath
                from urllib.parse import urlencode
                
                query_params = {}
                body_data = {}
                receive_id_type_value = None
                
                # 处理 parameters 中的查询参数
                if jsonpath(obj=v, expr="$.parameters") is not False:
                    _parameters = v.get("parameters", [])
                    for param in _parameters:
                        param_in = param.get("in", "")
                        if param_in == "query":
                            # 查询参数
                            param_name = param.get("name")
                            example_value = self._get_parameter_example(param)
                            if param_name:
                                # 如果参数名为 receive_id_type 且没有示例值，使用默认值
                                if param_name == "receive_id_type" and example_value is None:
                                    # 使用生成器实例中的默认值
                                    default_value = self._generator.default_receive_id_type
                                    final_value = default_value if default_value else None
                                    query_params[param_name] = final_value
                                    receive_id_type_value = final_value
                                else:
                                    final_value = example_value if example_value is not None else None
                                    query_params[param_name] = final_value
                                    # 记录 receive_id_type 的值
                                    if param_name == "receive_id_type":
                                        receive_id_type_value = final_value
                        elif param_in not in ["header", "path", "cookie"]:
                            # 其他非 header/path/cookie 参数（旧版 Swagger 可能放在这里）
                            param_name = param.get("name")
                            example_value = self._get_parameter_example(param)
                            if param_name:
                                body_data[param_name] = example_value if example_value is not None else None
                
                # 从 requestBody 中提取请求体数据，传入 receive_id_type 以便选择对应的 receive_id
                request_body_data = self._extract_request_body_data(v, dependent_fields, receive_id_type_value)
                body_data.update(request_body_data)
                
                return query_params, body_data, receive_id_type_value
            
            def _is_file_upload_request(self, v: dict) -> Tuple[bool, dict]:
                """检测是否是文件上传请求，返回 (是否为文件上传, schema信息)"""
                request_body = v.get("requestBody", {})
                if not request_body:
                    return False, {}
                
                content = request_body.get("content", {})
                if "multipart/form-data" not in content:
                    return False, {}
                
                # 获取 schema
                schema_ref = content.get("multipart/form-data", {}).get("schema", {})
                schema = schema_ref
                
                # 如果是引用，需要解析
                if "$ref" in schema_ref:
                    ref_path = schema_ref["$ref"]
                    # 解析 #/components/schemas/ImageUploadRequest
                    if ref_path.startswith("#/components/schemas/"):
                        schema_name = ref_path.split("/")[-1]
                        components = self._base_swagger._data.get("components", {})
                        schemas = components.get("schemas", {})
                        schema = schemas.get(schema_name, {})
                
                # 检查是否有 format: binary 的字段（文件字段）
                properties = schema.get("properties", {})
                file_fields = {}
                data_fields = {}
                
                for prop_name, prop_schema in properties.items():
                    if isinstance(prop_schema, dict):
                        if prop_schema.get("format") == "binary":
                            # 这是文件字段
                            file_fields[prop_name] = "sendImage.png"  # 默认文件名
                        else:
                            # 这是普通数据字段
                            # 尝试获取默认值或示例值
                            default_value = prop_schema.get("default")
                            example_value = prop_schema.get("example")
                            enum_values = prop_schema.get("enum", [])
                            
                            if default_value is not None:
                                data_fields[prop_name] = default_value
                            elif example_value is not None:
                                data_fields[prop_name] = example_value
                            elif enum_values:
                                data_fields[prop_name] = enum_values[0]  # 使用第一个枚举值
                            else:
                                data_fields[prop_name] = None
                
                is_file_upload = len(file_fields) > 0
                return is_file_upload, {"file": file_fields, "data": data_fields}
            
            def write_yaml_handler(self):
                """生成 YAML 测试用例"""
                from utils.read_files_tools.swagger_for_yaml import SwaggerForYaml
                import yaml
                import os
                from urllib.parse import urlencode
                
                _api_data = self._base_swagger._data.get("paths", {})
                for key, value in _api_data.items():
                    for k, v in value.items():
                        if not isinstance(v, dict):
                            continue
                        
                        headers = self._base_swagger.get_headers(v)
                        # 确保 headers 是字典类型
                        if headers is None:
                            headers = {}
                        elif not isinstance(headers, dict):
                            headers = dict(headers) if hasattr(headers, '__iter__') else {}
                        
                        # 确保所有接口都包含 Authorization header（如果还没有）
                        if "Authorization" not in headers:
                            # 使用占位符，后续会通过 _update_yaml_with_token 更新
                            headers["Authorization"] = "Bearer <tenant_access_token>"
                        
                        request_type = self._base_swagger.get_request_type(v, headers)
                        
                        # 确保 file_path 包含 open-apis 前缀，以便生成正确的文件路径
                        file_path = key
                        if not file_path.startswith("/open-apis"):
                            file_path = "/open-apis" + file_path
                        
                        # 获取当前 API 的完整路径（用于查找依赖关系）
                        full_api_path = key
                        if not full_api_path.startswith("/open-apis"):
                            full_api_path = "/open-apis" + full_api_path
                        
                        # 获取依赖接口（在生成请求体数据之前，以便知道哪些字段会通过依赖填充）
                        dependent_apis = self._generator._get_dependent_apis(full_api_path)
                        
                        # 获取所有已存在的 API 路径（用于检查依赖是否真的存在）
                        # 这个集合会在后面构建 dependence_case_data 时复用
                        existing_api_paths = set()
                        for file_info in self._generator.openapi_files:
                            if file_info.api_path:
                                full_path = file_info.api_path
                                if not full_path.startswith("/open-apis"):
                                    full_path = "/open-apis" + full_path
                                existing_api_paths.add(full_path)
                        
                        # 收集会通过依赖用例填充的字段
                        # 只添加那些依赖接口确实存在且会被添加到 dependence_case_data 的字段
                        # 这样可以避免将不存在的依赖接口的字段标记为依赖填充，导致字段被错误过滤
                        dependent_fields = set()
                        if dependent_apis:
                            for dep_api in dependent_apis:
                                dep_api_path = dep_api.get("api_path", "")
                                if not dep_api_path:
                                    continue
                                
                                # 确保路径包含 open-apis 前缀
                                if not dep_api_path.startswith("/open-apis"):
                                    dep_api_path = "/open-apis" + dep_api_path
                                
                                # 检查依赖的 API 是否真的存在
                                # 如果依赖不存在，不应该将字段标记为依赖填充
                                # 因为依赖用例不会被添加到 dependence_case_data 中，字段不会被填充
                                if dep_api_path not in existing_api_paths:
                                    optional = dep_api.get("optional", False)
                                    if not optional:
                                        # 非可选依赖但不存在，记录警告但不添加字段
                                        print(f"[WARN] 依赖接口 {dep_api_path} 不存在，但标记为非可选，跳过添加依赖字段")
                                    # 可选依赖不存在时，也不将字段标记为依赖填充（因为不会被填充）
                                    continue
                                
                                # 只有依赖接口确实存在时，才将字段标记为依赖填充
                                param_mapping = dep_api.get("param_mapping", [])
                                for mapping in param_mapping:
                                    target_param = mapping.get("target_param")
                                    target_location = mapping.get("target_param_location", "body")
                                    # 对于 body 和 query 参数，都标记为依赖字段
                                    # path 参数在 URL 中已经使用 $cache{redis:param_name} 格式，不需要标记
                                    if target_param and target_location in ["body", "query"]:
                                        dependent_fields.add(target_param)
                        
                        # 检测是否是文件上传接口
                        is_file_upload, file_upload_data = self._is_file_upload_request(v)
                        if is_file_upload:
                            # 文件上传接口：设置 requestType 为 FILE，生成文件上传数据
                            request_type = "FILE"
                            case_data = file_upload_data if file_upload_data else {}
                            query_params = {}  # 文件上传接口通常没有查询参数
                            # 为文件上传接口添加 Content-Type header（代码执行时会自动替换为包含 boundary 的正确值）
                            if "Content-Type" not in headers:
                                headers["Content-Type"] = "multipart/form-data"
                        else:
                            # 分离查询参数和请求体参数（传入依赖字段信息）
                            query_params, case_data, receive_id_type_value = self._separate_query_and_body_params(v, dependent_fields)
                        
                        # 构建 URL（包含查询参数和路径参数替换）
                        final_url = key
                        
                        # 处理 URL 中的路径参数（如 {calendar_id}），从缓存中获取值
                        import re
                        path_params = re.findall(r'\{([^}]+)\}', final_url)
                        for param_name in path_params:
                            # 使用缓存引用格式替换路径参数
                            cache_ref = f"$cache{{redis:{param_name}}}"
                            final_url = final_url.replace(f"{{{param_name}}}", cache_ref)
                        
                        if query_params:
                            # 过滤掉 None 值
                            filtered_params = {k: v for k, v in query_params.items() if v is not None}
                            if filtered_params:
                                final_url = f"{final_url}?{urlencode(filtered_params)}"
                        
                        # 获取输出参数（用于设置缓存）
                        output_params = self._generator._get_output_params(full_api_path)
                        
                        # 构建 current_request_set_cache（如果有输出参数）
                        current_request_set_cache = None
                        if output_params:
                            cache_config = []
                            # 从响应 schema 中解析正确的 jsonpath
                            response_schema = self._get_response_schema(v)
                            for param in output_params:
                                # 从响应 schema 中查找参数的正确路径
                                # 响应结构通常是 {code, msg, data: {...}}，所以从 data 属性开始查找
                                jsonpath = ""
                                if response_schema:
                                    # 先检查 data 属性
                                    data_schema = response_schema.get("properties", {}).get("data", {})
                                    if data_schema:
                                        # 解析 data 的 schema（可能是引用）
                                        if isinstance(data_schema, dict) and "$ref" in data_schema:
                                            ref_path = data_schema["$ref"]
                                            if ref_path.startswith("#/components/schemas/"):
                                                schema_name = ref_path.split("/")[-1]
                                                components = self._base_swagger._data.get("components", {})
                                                schemas = components.get("schemas", {})
                                                data_schema = schemas.get(schema_name, {})
                                        
                                        # 从 data 属性开始查找参数
                                        # 注意：data_schema 是 data 属性的 schema，所以参数应该直接在 data 下
                                        # 例如：响应是 {code, msg, data: {image_key: ...}}，所以 jsonpath 应该是 $.data.image_key
                                        # 直接检查 data_schema 的 properties 中是否包含 param
                                        if isinstance(data_schema, dict):
                                            data_properties = data_schema.get("properties", {})
                                            if param in data_properties:
                                                # 参数直接在 data 下，返回 $.data.param
                                                jsonpath = f"$.data.{param}"
                                            else:
                                                # 参数不在 data 的直接 properties 中，递归查找
                                                jsonpath = self._find_param_jsonpath(data_schema, param, "$.data")
                                
                                if not jsonpath:
                                    # 如果找不到，使用默认路径 $.data.param_name
                                    jsonpath = f"$.data.{param}"
                                cache_config.append({
                                    "type": "response",
                                    "jsonpath": jsonpath,
                                    "name": f"redis:{param}"  # 使用 redis: 前缀
                                })
                            if cache_config:
                                current_request_set_cache = cache_config
                        
                        # 构建 dependence_case_data
                        # 只添加已存在的依赖用例（检查依赖的 API 是否在 openapi_files 中）
                        # 注意：existing_api_paths 已经在上面构建过了，这里直接使用
                        dependence_case_data = None
                        dependence_case = False
                        if dependent_apis:
                            dep_case_data = []
                            
                            for dep_api in dependent_apis:
                                dep_api_path = dep_api.get("api_path", "")
                                if not dep_api_path:
                                    continue
                                
                                # 确保路径包含 open-apis 前缀
                                if not dep_api_path.startswith("/open-apis"):
                                    dep_api_path = "/open-apis" + dep_api_path
                                
                                # 检查依赖的 API 是否存在
                                # 对于路径参数，需要支持模糊匹配（例如 /calendars 匹配 /calendars/{id}）
                                dep_api_exists = False
                                if dep_api_path in existing_api_paths:
                                    dep_api_exists = True
                                else:
                                    # 尝试模糊匹配：如果依赖路径是基础路径，检查是否有带路径参数的版本
                                    # 例如：/open-apis/calendar/v4/calendars 匹配 /open-apis/calendar/v4/calendars/{calendar_id}
                                    import re
                                    base_path = re.sub(r'[:\{][^}/]+', '', dep_api_path)
                                    for existing_path in existing_api_paths:
                                        existing_base = re.sub(r'[:\{][^}/]+', '', existing_path)
                                        if base_path == existing_base:
                                            dep_api_exists = True
                                            break
                                
                                if not dep_api_exists:
                                    # 如果依赖不存在，跳过（可选依赖）或记录警告
                                    optional = dep_api.get("optional", False)
                                    if not optional:
                                        print(f"[WARN] 依赖接口 {dep_api_path} 不存在，但标记为非可选，跳过添加依赖")
                                    continue
                                
                                # 生成依赖用例的 case_id
                                dep_case_id = self.get_case_id(dep_api_path.replace("/open-apis", ""))
                                
                                # 获取参数映射
                                param_mapping = dep_api.get("param_mapping", [])
                                
                                dependent_data = []
                                for mapping in param_mapping:
                                    source_param = mapping.get("source_param")
                                    target_param = mapping.get("target_param")
                                    target_location = mapping.get("target_param_location", "body")
                                    
                                    if source_param:
                                        # 根据 target_location 设置 replace_key
                                        # 用于在执行当前接口前，从缓存中读取数据并替换到请求中
                                        replace_key = None
                                        if target_param:
                                            if target_location == "body":
                                                # body 参数：使用 data.target_param 格式
                                                replace_key = f"data.{target_param}"
                                            elif target_location == "query":
                                                # query 参数：使用 params.target_param 格式
                                                replace_key = f"params.{target_param}"
                                            elif target_location == "path":
                                                # path 参数：已经在 URL 中使用 $cache{redis:param_name} 格式
                                                # 不需要 replace_key，框架会自动处理
                                                replace_key = None
                                        
                                        # 即使 replace_key 为 None（路径参数），也需要添加依赖数据项
                                        # 这样框架才知道需要执行依赖用例
                                        dependent_data.append({
                                            "dependent_type": "response",
                                            "jsonpath": f"$.data.{source_param}",
                                            "set_cache": f"redis:{source_param}",  # 存入缓存
                                            "replace_key": replace_key  # 从缓存读取并替换到请求中（路径参数为 None）
                                        })
                                
                                if dependent_data:
                                    dep_case_data.append({
                                        "case_id": dep_case_id,
                                        "dependent_data": dependent_data
                                    })
                            
                            if dep_case_data:
                                dependence_case = True
                                dependence_case_data = dep_case_data
                        
                        yaml_data = {
                            "case_common": {
                                "allureEpic": self.get_allure_epic(),
                                "allureFeature": self.get_allure_feature(v),
                                "allureStory": self.get_allure_story(v)
                            },
                            self.get_case_id(key): {
                                "host": self._base_swagger._host,
                                "url": final_url,  # URL 包含查询参数（如果有）
                                "method": k,
                                "detail": self.get_detail(v),
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": case_data,  # 请求体数据（不包含查询参数）
                                "dependence_case": dependence_case,
                                "dependence_case_data": dependence_case_data,
                                "current_request_set_cache": current_request_set_cache,
                                "assert": {"status_code": 200},
                                "sql": None
                            }
                        }
                        
                        # 使用自定义方法写入文件到 open-apis2 目录
                        self._generator._write_yaml_to_custom_path(yaml_data, file_path)
        
        return GenericOpenAPIGenerator(file_info.file_path, self)
    
    def _write_yaml_to_custom_path(self, yaml_data: Dict, file_path: str):
        """将 YAML 数据写入到自定义路径（open-apis2 目录）"""
        try:
            from common.setting import ensure_path_sep
            
            # 使用 ruamel.yaml 来保持格式
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            yaml.default_flow_style = False
            
            # 构建文件路径：open-apis2/{api_path}.yaml
            # file_path 格式：/open-apis/im/v1/images 或 /open-apis/calendar/v4/calendars/{calendar_id}
            # 清理路径参数，使其适合作为文件名
            sanitized_path = _sanitize_path_for_filename(file_path)
            yaml_path_str = sanitized_path[1:] + ".yaml"  # 去掉开头的 /，添加 .yaml
            output_path = Path(self.data_output_dir) / yaml_path_str.replace("/", os.sep)
            
            # 创建目录
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入 YAML 文件
            with output_path.open("w", encoding="utf-8") as f:
                yaml.dump(yaml_data, f)
                f.write('\n')
            
            # 记录生成的 YAML 文件路径
            self.generated_yaml_files.append(output_path)
            
            print(f"[OK] 已生成 YAML 文件: {output_path.absolute()}")
        except Exception as e:
            print(f"[ERROR] 写入 YAML 文件失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_yaml_with_token(self, yaml_file_path: Path, token: str) -> bool:
        """通用的更新 YAML 文件中 token 的方法"""
        try:
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            yaml.default_flow_style = False
            
            if not yaml_file_path.exists():
                print(f"[WARN] YAML 文件不存在: {yaml_file_path}")
                return False
            
            with yaml_file_path.open("r", encoding="utf-8") as f:
                data = yaml.load(f) or {}
            
            updated = False
            for key, value in data.items():
                if key == "case_common" or not isinstance(value, dict):
                    continue
                
                headers = value.get("headers")
                if headers is None:
                    headers = {}
                    value["headers"] = headers
                elif not isinstance(headers, dict):
                    headers = dict(headers) if hasattr(headers, '__iter__') else {}
                    value["headers"] = headers
                
                # 跳过无效 token 的用例（用于测试认证失败场景）
                detail = value.get("detail", "")
                if "Token无效" in detail or "Token过期" in detail or "TC_AUTH_001" in detail:
                    continue
                
                # 更新 Authorization（包括占位符）
                current_auth = headers.get("Authorization", "")
                if current_auth == "Bearer <tenant_access_token>" or not current_auth or current_auth.startswith("Bearer <"):
                    headers["Authorization"] = f"Bearer {token}"
                    updated = True
            
            if updated:
                with yaml_file_path.open("w", encoding="utf-8") as f:
                    yaml.dump(data, f)
                print(f"[OK] 已更新 {yaml_file_path.name} 中的 Authorization")
                return True
            return False
        except Exception as e:
            print(f"[ERROR] 更新 YAML 文件时出错: {e}")
            return False
    
    def _find_generated_yaml_file(self, api_path: str) -> Optional[Path]:
        """根据 API 路径查找生成的 YAML 文件（在 open-apis2 目录）"""
        # 确保路径包含 open-apis 前缀
        if not api_path.startswith("/open-apis"):
            api_path = "/open-apis" + api_path
        
        # 清理路径参数（如 {calendar_id} -> calendar_id），使其与生成的文件名匹配
        sanitized_path = _sanitize_path_for_filename(api_path)
        
        # 转换为文件路径：open-apis2/{sanitized_path}.yaml
        yaml_path_str = sanitized_path[1:] + ".yaml"  # 去掉开头的 /
        yaml_path = Path(self.data_output_dir) / yaml_path_str.replace("/", os.sep)
        
        if yaml_path.exists():
            return yaml_path
        
        # 如果找不到，尝试查找 open-apis2 下的所有 YAML 文件
        # 根据 API 路径的最后部分匹配（清理后的）
        api_name = sanitized_path.split("/")[-1]
        data_dir = Path(self.data_output_dir)
        if data_dir.exists():
            for yaml_file in data_dir.rglob("*.yaml"):
                if api_name in yaml_file.stem:
                    return yaml_file
        
        return None
    
    def generate_for_file(self, file_info: OpenAPIFileInfo) -> bool:
        """为单个文件生成测试用例（通用方法，不依赖特定接口类型）"""
        print(f"\n{'=' * 60}")
        print(f"处理文件: {file_info.file_path.name}")
        print(f"API 路径: {file_info.api_path}")
        print(f"{'=' * 60}")
        
        try:
            # 使用通用生成器
            generator = self._create_generic_swagger_generator(file_info)
            generator.write_yaml_handler()
            
            # 更新 token（如果已获取）
            if self.token and file_info.api_path:
                yaml_file = self._find_generated_yaml_file(file_info.api_path)
                if yaml_file:
                    self._update_yaml_with_token(yaml_file, self.token)
                else:
                    print(f"[WARN] 未找到生成的 YAML 文件，无法更新 token")
            
            print(f"[OK] 用例生成完成: {file_info.file_path.name}")
            return True
                
        except Exception as e:
            print(f"[ERROR] 生成用例失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_test_cases_for_custom_path(self):
        """为自定义路径生成 pytest 测试用例"""
        from utils.read_files_tools.testcase_template import write_testcase_file
        from utils.read_files_tools.yaml_control import GetYamlData
        from utils.read_files_tools.get_all_files_path import get_all_files
        from common.setting import ensure_path_sep
        import os
        
        # 获取 open-apis2 目录下的所有 YAML 文件
        data_dir = Path(self.data_output_dir)
        if not data_dir.exists():
            print(f"[WARN] 输出目录不存在: {data_dir}")
            return
        
        yaml_files = list(data_dir.rglob("*.yaml"))
        if not yaml_files:
            print(f"[WARN] 在 {data_dir} 中未找到 YAML 文件")
            return
        
        for yaml_file in yaml_files:
            try:
                # 跳过代理拦截文件
                if 'proxy_data.yaml' in str(yaml_file):
                    continue
                
                # 读取 YAML 数据
                yaml_case_process = GetYamlData(str(yaml_file)).get_yaml_data()
                
                # 检查 YAML 数据是否有效
                if yaml_case_process is None:
                    print(f"[WARN] YAML 文件为空或格式错误: {yaml_file}")
                    continue
                
                # 计算测试文件路径
                # yaml_file: open-apis2/im/v1/images.yaml
                # test_file: open-apis2/im/v1/test_images.py
                relative_path = yaml_file.relative_to(data_dir)
                
                # 清理文件 stem，移除路径参数（如 {calendar_id}）
                # 对于文件名，保留下划线分隔（如 calendar_id）
                # 对于类名，使用驼峰命名（如 CalendarId）
                file_stem = relative_path.stem
                sanitized_filename = _sanitize_for_filename(file_stem)  # 用于文件名
                sanitized_identifier = _sanitize_for_python_identifier(file_stem)  # 用于类名和函数名
                
                # 使用清理后的文件名创建测试文件路径
                test_file_path = Path(self.test_output_dir) / relative_path.parent / f"test_{sanitized_filename}.py"
                
                # 创建测试文件目录
                test_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 生成测试用例
                case_ids = [k for k in yaml_case_process.keys() if k != "case_common"]
                if not case_ids:
                    print(f"[WARN] YAML 文件中没有测试用例: {yaml_file}")
                    continue
                
                # 获取 allure 信息
                case_common = yaml_case_process.get("case_common", {})
                allure_epic = case_common.get("allureEpic", "API 接口测试")
                allure_feature = case_common.get("allureFeature", "接口测试")
                allure_story = case_common.get("allureStory", "接口调用")
                
                # 生成类名和函数名（使用已清理的 sanitized_identifier）
                
                # 生成类名：使用驼峰命名，并确保以 Test 开头
                if not sanitized_identifier:
                    class_title = "TestApi"
                else:
                    # 将驼峰命名转为 PascalCase（首字母大写）
                    # 例如: calendarId -> CalendarId
                    # 注意：sanitized_identifier 已经是驼峰命名（如 calendarId），不是 TestCalendarId
                    pascal_case = sanitized_identifier[0].upper() + sanitized_identifier[1:] if len(sanitized_identifier) > 0 else "Api"
                    
                    # 如果已经是 Test 开头，不要重复添加
                    if pascal_case.startswith("Test"):
                        class_title = pascal_case
                    else:
                        class_title = "Test" + pascal_case
                    
                    # 确保类名以字母开头（如果转换后仍不是字母，添加前缀）
                    if class_title and not class_title[0].isalpha():
                        class_title = "Test" + class_title
                
                # 函数名使用清理后的文件名（保留下划线分隔）
                func_title = sanitized_filename if sanitized_filename else "test_api"
                
                # 写入测试文件
                write_testcase_file(
                    allure_epic=allure_epic,
                    allure_feature=allure_feature,
                    class_title=class_title,
                    func_title=func_title,
                    case_path=str(test_file_path),
                    case_ids=case_ids,
                    file_name=test_file_path.name,
                    allure_story=allure_story
                )
                
                print(f"[OK] 已生成测试文件: {test_file_path.absolute()}")
            except Exception as e:
                print(f"[ERROR] 生成测试文件失败 {yaml_file}: {e}")
                import traceback
                traceback.print_exc()
    
    def _create_test_case_init_file(self):
        """创建测试用例初始化文件，用于加载 open-apis2 目录下的 YAML 文件到缓存"""
        from common.setting import ensure_path_sep
        from utils.read_files_tools.get_yaml_data_analysis import CaseData
        from utils.read_files_tools.get_all_files_path import get_all_files
        from utils.cache_process.cache_control import CacheHandler, _cache_config
        
        # 创建 __init__.py 文件在 test_output_dir 目录
        init_file_path = Path(self.test_output_dir) / "__init__.py"
        init_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成初始化代码
        init_content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : Auto-generated by feishu_unified_generator
# 此文件用于加载 {self.data_output_dir} 目录下的 YAML 测试用例到缓存中

from common.setting import ensure_path_sep
from utils.read_files_tools.get_yaml_data_analysis import CaseData
from utils.read_files_tools.get_all_files_path import get_all_files
from utils.cache_process.cache_control import CacheHandler, _cache_config


def write_case_process():
    """
    获取所有用例，写入用例池中
    :return:
    """
    # 循环拿到所有存放用例的文件路径（从 {self.data_output_dir} 目录）
    for i in get_all_files(file_path=ensure_path_sep("\\\\{self.data_output_dir}"), yaml_data_switch=True):
        # 循环读取文件中的数据
        case_process = CaseData(i).case_process(case_id_switch=True)
        if case_process is not None:
            # 转换数据类型
            for case in case_process:
                for k, v in case.items():
                    # 判断 case_id 是否已存在
                    case_id_exit = k in _cache_config.keys()
                    # 如果case_id 不存在，则将用例写入缓存池中
                    if case_id_exit is False:
                        CacheHandler.update_cache(cache_name=k, value=v)
                    # 当 case_id 为 True 存在时，则抛出异常
                    elif case_id_exit is True:
                        raise ValueError(f"case_id: {{k}} 存在重复项, 请修改case_id\\n"
                                         f"文件路径: {{i}}")


write_case_process()
'''
        
        with init_file_path.open("w", encoding="utf-8") as f:
            f.write(init_content)
        
        print(f"[OK] 已创建初始化文件: {init_file_path.absolute()}")
    
    def run_all(self):
        """执行完整的生成流程"""
        print("\n" + "=" * 60)
        print("通用飞书接口测试用例生成器")
        print("=" * 60)
        
        # 步骤 1: 扫描 YAML 文件
        print("\n步骤 1: 扫描 OpenAPI YAML 文件")
        print("-" * 60)
        self.openapi_files = self.scan_yaml_files()
        
        if not self.openapi_files:
            print("[ERROR] 未找到任何有效的 OpenAPI YAML 文件")
            return
        
        print(f"[OK] 找到 {len(self.openapi_files)} 个文件")
        
        # 步骤 1.5: 根据依赖关系排序
        if self.api_relations:
            print("\n步骤 1.5: 根据依赖关系确定执行顺序")
            print("-" * 60)
            # 构建 API 路径到文件信息的映射
            api_path_to_file = {}
            for file_info in self.openapi_files:
                if file_info.api_path:
                    full_path = file_info.api_path
                    if not full_path.startswith("/open-apis"):
                        full_path = "/open-apis" + full_path
                    api_path_to_file[full_path] = file_info
            
            # 构建依赖图
            graph = self._build_dependency_graph()
            
            # 拓扑排序
            sorted_files = self._topological_sort(graph, api_path_to_file)
            self.openapi_files = sorted_files
            
            print(f"[OK] 根据依赖关系排序完成:")
            for i, file_info in enumerate(self.openapi_files, 1):
                print(f"  {i}. {file_info.file_path.name}")
                if file_info.api_path:
                    full_path = file_info.api_path
                    if not full_path.startswith("/open-apis"):
                        full_path = "/open-apis" + full_path
                    deps = graph.get(full_path, [])
                    if deps:
                        print(f"     依赖: {', '.join([d.split('/')[-1] for d in deps])}")
        else:
            print(f"[WARN] 未加载依赖关系，按文件顺序处理")
        
        # 步骤 2: 获取 token
        print("\n步骤 2: 获取 tenant_access_token")
        print("-" * 60)
        self.token = self.get_tenant_access_token()
        if not self.token:
            print("[WARN] 警告: 未获取到 token，部分用例可能需要手动填写 Authorization")
        
        # 步骤 3: 按顺序生成用例
        print("\n步骤 3: 按顺序生成测试用例")
        print("-" * 60)
        success_count = 0
        for file_info in self.openapi_files:
            if self.generate_for_file(file_info):
                success_count += 1
            else:
                print(f"[WARN] 警告: {file_info.file_path.name} 生成失败，继续处理下一个")
        
        # 步骤 4: 生成 pytest 测试用例（使用自定义路径）
        print("\n步骤 4: 生成 pytest 测试用例")
        print("-" * 60)
        self._generate_test_cases_for_custom_path()
        print("[OK] pytest 用例生成完成")
        
        # 步骤 4.5: 创建测试用例初始化文件（用于加载 YAML 到缓存）
        print("\n步骤 4.5: 创建测试用例初始化文件")
        print("-" * 60)
        self._create_test_case_init_file()
        print("[OK] 初始化文件创建完成")
        
        # 步骤 5: 总结
        print("\n步骤 5: 总结")
        print("-" * 60)
        ensure_allure_properties_file("./report/tmp")
        print(f"[OK] 处理完成: {success_count}/{len(self.openapi_files)} 个文件成功生成用例")
        print(f"\n生成的测试用例位于:")
        print(f"  - YAML: {self.data_output_dir}/")
        print(f"  - Test: {self.test_output_dir}/")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="通用飞书接口测试用例生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置
  python utils/other_tools/feishu_unified_generator.py --folder interfacetest/interfaceUnion/imageSend
  
  # 指定 App ID 和 Secret
  python utils/other_tools/feishu_unified_generator.py \\
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
        help="飞书应用 App ID (默认使用配置中的值)"
    )
    
    parser.add_argument(
        "--app-secret",
        type=str,
        default=None,
        help="飞书应用 App Secret (默认使用配置中的值)"
    )
    
    args = parser.parse_args()
    
    try:
        generator = FeishuUnifiedGenerator(
            folder_path=Path(args.folder),
            app_id=args.app_id,
            app_secret=args.app_secret
        )
        generator.run_all()
        print("\n[OK] 全部完成")
    except KeyboardInterrupt:
        print("\n用户中断，退出")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] 执行出错: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
