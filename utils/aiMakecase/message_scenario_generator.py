#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
消息场景专用测试用例生成器
---------------------------
- 读取四个文件：scene、relation、json、openapi
- 基于消息场景的特殊要求生成细化的测试用例
- 支持正常场景、异常场景、边界场景等多种场景类型
- 支持外部参数注入（如 message_id、receive_id 等）
- 生成 pytest 测试文件
"""

import sys
import argparse
import os
import json
import re
import time
import yaml
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from urllib.parse import urlparse

# 确保项目根目录在 sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.other_tools.config.model_config import DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_API_KEY
from utils.aiMakecase.message_ai_prompt import (
    build_message_prompt,
    IDENTITY_ANSWER,
    RECEIVE_ID_MAP,
    _extract_json,
    generate_pytest_from_cases,
    _parse_openapi_head_text
)

# 检查 openai 是否可用
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[WARN] openai库不可用，请安装: pip install openai")

# ================= 配置区域 =================
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY") or DEFAULT_API_KEY
DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "deepseek-v3.2")
DEFAULT_AI_BASE_URL = os.getenv("DEFAULT_AI_BASE_URL", DEFAULT_BASE_URL)
DEFAULT_AI_TIMEOUT = int(os.getenv("DEFAULT_AI_TIMEOUT", "120"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "2000"))

# 飞书配置
DEFAULT_APP_ID = os.getenv("FEISHU_APP_ID")
DEFAULT_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
FEISHU_API_BASE_URL = os.getenv("FEISHU_API_BASE_URL", "https://open.feishu.cn/open-apis")
# ===========================================


@dataclass
class MessageTestCase:
    """消息场景测试用例数据类"""
    name: str
    description: str
    test_type: str  # "normal", "exception", "boundary"
    scenario_category: str  # "create", "reply", "forward", "update", "delete" 等
    request_data: Dict[str, Any]
    expected_status_code: int
    expected_response: Dict[str, Any]
    test_case_name: str = ""
    tags: List[str] = field(default_factory=list)
    is_success: bool = True
    
    def to_dict(self):
        return asdict(self)


class MessageScenarioGenerator:
    """消息场景专用测试用例生成器"""
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None,
                 timeout: int = None, max_tokens: int = None):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.model = model or DEFAULT_AI_MODEL
        self.base_url = base_url or DEFAULT_AI_BASE_URL
        self.timeout = timeout or DEFAULT_AI_TIMEOUT
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.receive_id_map = RECEIVE_ID_MAP
        
        # 加载错误码文件
        self.error_codes = self._load_error_codes()
        
        self.client = None
        self.ai_available = False
        self._init_ai_client()
    
    def _load_error_codes(self) -> Dict[int, Dict[str, str]]:
        """加载错误码文件"""
        error_codes = {}
        error_code_file = project_root / "error_code.json"
        
        if error_code_file.exists():
            try:
                with open(error_code_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    error_codes_list = data.get("error_codes", [])
                    for item in error_codes_list:
                        code = item.get("code")
                        if code:
                            error_codes[code] = {
                                "description": item.get("description", ""),
                                "solution": item.get("solution", "")
                            }
                print(f"[OK] 成功加载 {len(error_codes)} 个错误码")
            except Exception as e:
                print(f"[WARN] 加载错误码文件失败: {e}")
        else:
            print(f"[WARN] 错误码文件不存在: {error_code_file}")
        
        return error_codes
    
    def _init_ai_client(self):
        """初始化AI客户端"""
        if not OPENAI_AVAILABLE:
            print("[WARN] openai库不可用，AI功能将无法使用")
            return
        
        if not self.api_key or self.api_key == "sk-your-api-key-here":
            print("[WARN] 未配置有效的API Key，AI功能将无法使用")
            return
        
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            self.ai_available = True
            print(f"[OK] AI客户端初始化成功，使用模型: {self.model}")
        except Exception as e:
            print(f"[ERROR] AI客户端初始化失败: {e}")
    
    def load_api_summary(self, summary_file: str = "feishu-api-summary.json") -> Dict[str, Any]:
        """从feishu-api-summary.json加载API摘要信息"""
        summary_path = project_root / summary_file
        api_summary = None
        
        if summary_path.exists():
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_summary = data.get("apis", [])
                print(f"[OK] 加载API摘要文件: {summary_path}，找到 {len(api_summary)} 个API")
            except Exception as e:
                print(f"[WARN] 加载API摘要文件失败: {e}")
        else:
            print(f"[WARN] API摘要文件不存在: {summary_path}")
        
        return api_summary
    
    def extract_api_info_from_summary(self, api_summary: List[Dict[str, Any]], api_name: str = None) -> Optional[Dict[str, Any]]:
        """从API摘要中提取指定API的信息"""
        if not api_summary:
            return None
        
        # 如果指定了API名称，查找匹配的API
        if api_name:
            for api in api_summary:
                if api_name.lower() in api.get("name", "").lower() or api_name.lower() in api.get("url", "").lower():
                    return self._convert_summary_to_api_info(api)
        
        # 否则返回第一个API
        if api_summary:
            return self._convert_summary_to_api_info(api_summary[0])
        
        return None
    
    def _convert_summary_to_api_info(self, api_summary_item: Dict[str, Any]) -> Dict[str, Any]:
        """将API摘要转换为api_info格式"""
        # 从URL中提取路径
        url = api_summary_item.get("url", "")
        path = ""
        if "/im/v1/message/" in url:
            # 提取路径部分，如 /im/v1/message/create
            path_match = re.search(r'/im/v1/message/([^/]+)', url)
            if path_match:
                operation = path_match.group(1)
                path = f"/im/v1/messages/{operation}" if operation != "create" else "/im/v1/messages"
        
        # 提取参数信息
        path_params = []
        query_params = []
        body_params = []
        required_params = []
        
        for param in api_summary_item.get("pathParameters", []):
            param_name = param.get("name", "")
            path_params.append(param_name)
            if param.get("required"):
                required_params.append(param_name)
        
        for param in api_summary_item.get("queryParameters", []):
            param_name = param.get("name", "")
            param_info = {
                "name": param_name,
                "type": param.get("type", "string"),
                "required": param.get("required", False),
                "description": param.get("description", ""),
                "enum": param.get("enumValues", []),
                "in": "query"  # 标记为查询参数
            }
            query_params.append(param_name)
            if param.get("required"):
                required_params.append(param_name)
        
        for param in api_summary_item.get("bodyParameters", []):
            param_info = {
                "name": param.get("name", ""),
                "type": param.get("type", "string"),
                "required": param.get("required", False),
                "description": param.get("description", ""),
                "enum": param.get("enumValues", []),
                "defaultValue": param.get("defaultValue")
            }
            body_params.append(param_info)
            if param.get("required"):
                required_params.append(param_info["name"])
        
        # 提取支持的消息类型
        supported_msg_types = ["text"]
        for param in body_params:
            if param["name"] == "msg_type" and param.get("enum"):
                supported_msg_types = param["enum"]
                break
        
        # 判断消息API类型
        message_api_type = "unknown"
        name_lower = api_summary_item.get("name", "").lower()
        if "创建" in name_lower or "create" in name_lower or "send" in name_lower:
            message_api_type = "create"
        elif "回复" in name_lower or "reply" in name_lower:
            message_api_type = "reply"
        elif "转发" in name_lower or "forward" in name_lower:
            message_api_type = "forward"
        elif "更新" in name_lower or "update" in name_lower:
            message_api_type = "update"
        elif "删除" in name_lower or "delete" in name_lower:
            message_api_type = "delete"
        elif "获取" in name_lower or "get" in name_lower:
            message_api_type = "get"
        
        return {
            "path": path or "/im/v1/messages",
            "method": api_summary_item.get("method", "POST").upper(),
            "operation_id": api_summary_item.get("name", "api").lower().replace(" ", "_"),
            "summary": api_summary_item.get("name", ""),
            "description": api_summary_item.get("description", ""),
            "parameters": [],
            "request_body": {},
            "responses": {},
            "components": {},
            "required_params": required_params,
            "optional_params": [],
            "path_params": path_params,
            "query_params": query_params,
            "body_params": body_params,
            "supported_msg_types": supported_msg_types,
            "message_api_type": message_api_type
        }
    
    def load_files(self, base_name: str, base_dir: str = "uploads") -> Dict[str, Any]:
        """加载四个相关文件"""
        base_path = Path(base_dir)
        files_data = {
            "scene": None,
            "relation": None,
            "json": None,
            "openapi": None
        }
        
        # 构建文件路径
        scene_file = base_path / "scene" / f"scene_{base_name}.json"
        relation_file = base_path / "relation" / f"relation_{base_name}.json"
        json_file = base_path / "json" / f"json_{base_name}.json"
        openapi_file = base_path / "openapi" / f"openapi_{base_name}.yaml"
        
        # 加载scene文件
        if scene_file.exists():
            try:
                with open(scene_file, 'r', encoding='utf-8') as f:
                    files_data["scene"] = json.load(f)
                print(f"[OK] 加载scene文件: {scene_file}")
            except Exception as e:
                print(f"[WARN] 加载scene文件失败: {e}")
        else:
            print(f"[WARN] scene文件不存在: {scene_file}")
        
        # 加载relation文件
        if relation_file.exists():
            try:
                with open(relation_file, 'r', encoding='utf-8') as f:
                    files_data["relation"] = json.load(f)
                print(f"[OK] 加载relation文件: {relation_file}")
            except Exception as e:
                print(f"[WARN] 加载relation文件失败: {e}")
        else:
            print(f"[WARN] relation文件不存在: {relation_file}")
        
        # 加载json文件
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    files_data["json"] = json.load(f)
                print(f"[OK] 加载json文件: {json_file}")
            except Exception as e:
                print(f"[WARN] 加载json文件失败: {e}")
        else:
            print(f"[WARN] json文件不存在: {json_file}")
        
        # 加载openapi文件
        if openapi_file.exists():
            try:
                with open(openapi_file, 'r', encoding='utf-8') as f:
                    files_data["openapi"] = yaml.safe_load(f)
                print(f"[OK] 加载openapi文件: {openapi_file}")
            except Exception as e:
                print(f"[WARN] 加载openapi文件失败: {e}")
        else:
            print(f"[WARN] openapi文件不存在: {openapi_file}")
        
        return files_data
    
    def _extract_api_details(self, openapi_content: str) -> Dict[str, Any]:
        """从OpenAPI内容中提取详细的API信息"""
        try:
            api_data = yaml.safe_load(openapi_content)
        except Exception:
            return {}
        
        # 提取第一个接口的信息
        api_info = {
            "path": "",
            "method": "POST",
            "operation_id": "",
            "summary": "",
            "description": "",
            "parameters": [],
            "request_body": {},
            "responses": {},
            "required_params": [],
            "optional_params": [],
            "path_params": [],
            "query_params": [],
            "body_params": [],
            "supported_msg_types": ["text"],  # 默认支持文本
            "message_api_type": "unknown"
        }
        
        if not isinstance(api_data, dict):
            return api_info
        
        paths = api_data.get("paths", {})
        if not paths:
            return api_info
        
        # 找到第一个路径和方法
        for path, path_data in paths.items():
            if isinstance(path_data, dict):
                for method, operation_data in path_data.items():
                    if method.lower() in ["get", "post", "put", "delete", "patch"]:
                        api_info["path"] = path
                        api_info["method"] = method.upper()
                        api_info["operation_id"] = operation_data.get("operationId", "")
                        api_info["summary"] = operation_data.get("summary", "")
                        api_info["description"] = operation_data.get("description", "")
                        
                        # 解析参数
                        parameters = operation_data.get("parameters", [])
                        api_info["parameters"] = parameters
                        
                        # 分类参数
                        required_params = []
                        optional_params = []
                        path_params = []
                        query_params = []
                        
                        for param in parameters:
                            param_name = param.get("name", "")
                            param_required = param.get("required", False)
                            param_in = param.get("in", "")
                            
                            if param_required:
                                required_params.append(param_name)
                            else:
                                optional_params.append(param_name)
                            
                            if param_in == "path":
                                path_params.append(param_name)
                            elif param_in == "query":
                                query_params.append(param_name)
                        
                        api_info["required_params"] = required_params
                        api_info["optional_params"] = optional_params
                        api_info["path_params"] = path_params
                        api_info["query_params"] = query_params
                        
                        # 解析请求体
                        request_body = operation_data.get("requestBody", {})
                        api_info["request_body"] = request_body
                        
                        # 提取请求体参数
                        body_params = []
                        if request_body and "content" in request_body:
                            content = request_body.get("content", {})
                            for media_type, media_schema in content.items():
                                if "schema" in media_schema:
                                    schema = media_schema["schema"]
                                    # 检查是否有 $ref
                                    if "$ref" in schema:
                                        # 简单处理引用，实际应该解析components
                                        ref_path = schema["$ref"]
                                        # 尝试从components中获取
                                        components = api_data.get("components", {}).get("schemas", {})
                                        ref_name = ref_path.split("/")[-1]
                                        if ref_name in components:
                                            ref_schema = components[ref_name]
                                            if "properties" in ref_schema:
                                                schema_props = ref_schema["properties"]
                                                required_body = ref_schema.get("required", [])
                                                
                                                for prop_name, prop_schema in schema_props.items():
                                                    body_params.append({
                                                        "name": prop_name,
                                                        "required": prop_name in required_body,
                                                        "type": prop_schema.get("type", "string"),
                                                        "description": prop_schema.get("description", ""),
                                                        "example": prop_schema.get("example", ""),
                                                        "enum": prop_schema.get("enum", []),
                                                        "maxLength": prop_schema.get("maxLength"),
                                                        "minLength": prop_schema.get("minLength"),
                                                        "maximum": prop_schema.get("maximum"),
                                                        "minimum": prop_schema.get("minimum")
                                                    })
                                    elif "properties" in schema:
                                        schema_props = schema["properties"]
                                        required_body = schema.get("required", [])
                                        
                                        for prop_name, prop_schema in schema_props.items():
                                            body_params.append({
                                                "name": prop_name,
                                                "required": prop_name in required_body,
                                                "type": prop_schema.get("type", "string"),
                                                "description": prop_schema.get("description", ""),
                                                "example": prop_schema.get("example", ""),
                                                "enum": prop_schema.get("enum", []),
                                                "maxLength": prop_schema.get("maxLength"),
                                                "minLength": prop_schema.get("minLength"),
                                                "maximum": prop_schema.get("maximum"),
                                                "minimum": prop_schema.get("minimum")
                                            })
                        
                        api_info["body_params"] = body_params
                        
                        # 提取消息类型信息
                        for param in body_params:
                            if param["name"] == "msg_type" and param.get("enum"):
                                api_info["supported_msg_types"] = param["enum"]
                        
                        # 判断消息API类型
                        path_lower = path.lower()
                        operation_lower = operation_data.get("operationId", "").lower()
                        
                        if "create" in path_lower or "create" in operation_lower or "send" in operation_lower:
                            api_info["message_api_type"] = "create"
                        elif "reply" in path_lower or "reply" in operation_lower:
                            api_info["message_api_type"] = "reply"
                        elif "forward" in path_lower or "forward" in operation_lower:
                            api_info["message_api_type"] = "forward"
                        elif "update" in path_lower or "update" in operation_lower or "put" in method.lower():
                            api_info["message_api_type"] = "update"
                        elif "delete" in path_lower or "delete" in operation_lower:
                            api_info["message_api_type"] = "delete"
                        elif "get" in path_lower or "get" in operation_lower:
                            api_info["message_api_type"] = "get"
                        
                        api_info["responses"] = operation_data.get("responses", {})
                        break
                if api_info["path"]:
                    break
        
        return api_info
    
    def extract_api_info(self, files_data: Dict[str, Any], base_name: str = None) -> Dict[str, Any]:
        """从文件中提取API信息，优先使用feishu-api-summary.json"""
        api_info = {
            "path": "",
            "method": "",
            "operation_id": "",
            "summary": "",
            "description": "",
            "parameters": [],
            "request_body": {},
            "responses": {},
            "components": {},
            "required_params": [],
            "optional_params": [],
            "path_params": [],
            "query_params": [],
            "body_params": [],
            "supported_msg_types": ["text"],
            "message_api_type": "unknown"
        }
        
        # 优先从feishu-api-summary.json提取API信息
        api_summary = self.load_api_summary()
        if api_summary and base_name:
            # 尝试从base_name中提取API名称（如：feishu_server-docs_im-v1_message_create -> 创建消息）
            api_name_keywords = ["create", "reply", "update", "forward", "delete"]
            matched_api = None
            
            # 根据base_name中的关键词匹配API
            for keyword in api_name_keywords:
                if keyword in base_name.lower():
                    # 查找匹配的API
                    for api in api_summary:
                        api_name_lower = api.get("name", "").lower()
                        if keyword in api_name_lower:
                            matched_api = api
                            break
                    if matched_api:
                        break
            
            # 如果没找到，尝试使用第一个API
            if not matched_api and api_summary:
                matched_api = api_summary[0]
            
            if matched_api:
                print(f"[INFO] 从feishu-api-summary.json提取API信息: {matched_api.get('name', '')}")
                api_info_from_summary = self.extract_api_info_from_summary(api_summary, matched_api.get("name"))
                if api_info_from_summary:
                    # 合并信息，优先使用summary中的信息
                    # 只更新空值或默认值，保留summary中的信息
                    for key, value in api_info_from_summary.items():
                        if value and value != [] and value != {} and value != "unknown":
                            api_info[key] = value
                    print(f"[OK] 成功从feishu-api-summary.json提取API信息")
                    print(f"  - 路径: {api_info.get('path', '')}")
                    print(f"  - 方法: {api_info.get('method', '')}")
                    print(f"  - 消息类型: {api_info.get('message_api_type', '')}")
                    print(f"  - 必填参数: {', '.join(api_info.get('required_params', []))}")
        
        # 从openapi文件提取（作为补充，只补充缺失的信息）
        if files_data.get("openapi"):
            openapi_data = files_data["openapi"]
            
            # 将openapi数据转换为字符串，供_extract_api_details使用
            openapi_text = yaml.dump(openapi_data, allow_unicode=True, default_flow_style=False)
            detailed_info = self._extract_api_details(openapi_text)
            
            # 合并详细API信息，只补充缺失的信息
            for key, value in detailed_info.items():
                if not api_info.get(key) or api_info.get(key) == [] or api_info.get(key) == {} or api_info.get(key) == "unknown":
                    if value:
                        api_info[key] = value
            
            # 额外从OpenAPI中提取信息
            paths = openapi_data.get("paths", {})
            api_info["components"] = openapi_data.get("components", {})
            
            # 找到第一个路径和方法（确保基础信息存在）
            for path, path_data in paths.items():
                if isinstance(path_data, dict):
                    for method, operation_data in path_data.items():
                        if method.lower() in ["get", "post", "put", "delete", "patch"]:
                            if not api_info["path"]:
                                api_info["path"] = path
                            if not api_info["method"]:
                                api_info["method"] = method.upper()
                            if not api_info["operation_id"]:
                                api_info["operation_id"] = operation_data.get("operationId", "")
                            if not api_info["summary"]:
                                api_info["summary"] = operation_data.get("summary", "")
                            if not api_info["description"]:
                                api_info["description"] = operation_data.get("description", "")
                            break
                    if api_info["path"]:
                        break
        
        # 从json文件提取额外信息
        if files_data.get("json"):
            json_data = files_data["json"]
            if "data" in json_data and "schema" in json_data["data"]:
                schema = json_data["data"]["schema"]
                if "apiSchema" in schema:
                    api_schema = schema["apiSchema"]
                    if not api_info["path"]:
                        api_info["path"] = api_schema.get("path", "")
                    if not api_info["method"]:
                        api_info["method"] = api_schema.get("httpMethod", "").upper()
        
        # 从scene文件提取业务场景信息
        if files_data.get("scene"):
            scene_data = files_data["scene"]
            api_info["business_scenes"] = scene_data.get("business_scenes", {})
        
        return api_info
    
    def extract_scenarios_from_scene(self, files_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """从scene文件中提取细化的场景"""
        scenarios = {
            "normal": [],
            "exception": [],
            "boundary": []
        }
        
        if not files_data.get("scene"):
            return scenarios
        
        scene_data = files_data["scene"]
        
        # 提取业务场景
        if "business_scenes" in scene_data:
            business_scenes = scene_data["business_scenes"]
            if "scenes" in business_scenes:
                for scene in business_scenes["scenes"]:
                    # 正常场景
                    normal_scenarios = scene.get("normal_scenarios", [])
                    scenarios["normal"].extend(normal_scenarios)
                    
                    # 异常场景
                    exception_scenarios = scene.get("exception_scenarios", [])
                    scenarios["exception"].extend(exception_scenarios)
                    
                    # 边界场景
                    boundary_scenarios = scene.get("boundary_scenarios", [])
                    scenarios["boundary"].extend(boundary_scenarios)
        
        return scenarios
    
    def determine_scenario_category(self, api_info: Dict[str, Any]) -> str:
        """根据API信息确定场景类别"""
        return api_info.get("message_api_type", "unknown")
    
    def _build_detailed_scenario_guide(self, api_info: Dict[str, Any], scenario_type: str = "normal") -> str:
        """构建详细的场景指南"""
        message_api_type = api_info.get("message_api_type", "unknown")
        supported_msg_types = api_info.get("supported_msg_types", ["text"])
        required_params = api_info.get("required_params", [])
        body_params = api_info.get("body_params", [])
        
        if scenario_type == "normal":
            guide = f"""
# 正常场景要求（{message_api_type}消息）：
- 生成1个完整的正常场景测试用例，确保能通过
- 所有必填参数必须填写：{', '.join(required_params) if required_params else '无必填参数'}
- msg_type 必须在支持的类型中选择：{', '.join(supported_msg_types)}
- content 必须与 msg_type 匹配（具体格式见下方）
- receive_id 从 RECEIVE_ID_MAP 选择（优先使用 open_id，不要使用 email 和 chat_id）
- 预期HTTP状态码 200，业务码 0
- 使用合理的参数值（避免空字符串、过长内容等边界情况）

# 消息类型匹配示例：
"""
            # 添加消息类型示例
            msg_type_examples = {
                "text": '{"text": "这是一条测试消息"}',
                "image": '{"image_key": "img_v2_12345678-abcd-1234-5678-123456789012"}',
                "file": '{"file_key": "file_v2_12345678-abcd-1234-5678-123456789012"}',
                "audio": '{"file_key": "file_v2_12345678-abcd-1234-5678-123456789012", "duration": 3000}',
                "media": '{"file_key": "file_v2_12345678-abcd-1234-5678-123456789012", "image_key": "img_v2_12345678-abcd-1234-5678-123456789012"}',
                "sticker": '{"sticker_id": "sticker_123456"}',
                "interactive": '{"elements": [{"tag": "markdown", "content": "测试内容"}]}',
                "share_chat": '{"share_chat_id": "oc_1234567890abcdef"}',
                "share_user": '{"user_id": "ou_1234567890abcdef"}',
                "system": '{"text": "系统消息内容"}',
                "post": '{"post": {"zh_cn": {"title": "标题", "content": [[{"tag": "text", "text": "正文内容"}]]}}}'
            }
            
            for msg_type in supported_msg_types:
                if msg_type in msg_type_examples:
                    guide += f"- {msg_type}: content = {msg_type_examples[msg_type]}\n"
            
        elif scenario_type == "exception":
            guide = f"""
# 异常场景要求（{message_api_type}消息）：
- **必须生成5个明确的异常场景测试用例**，覆盖不同的异常情况
- 预期HTTP状态码 400（客户端错误）或 500（服务器错误）
- 预期业务码非 0
- 异常描述要清晰，说明测试什么异常
- **重要**：5个用例应该覆盖不同的异常场景（如缺失必填参数、参数类型错误、无效ID、格式错误、权限错误等）

# 常见的异常场景：
"""
            # 添加常见异常场景
            exception_scenarios = [
                "- 缺失必填参数",
                "- 参数类型错误（如字符串传数字）",
                "- 参数格式错误（如无效的JSON）",
                "- 使用不存在的 receive_id",
                "- 使用无效的 msg_type",
                "- content 与 msg_type 不匹配",
                "- 参数值超过长度限制",
                "- 参数值不符合枚举范围"
            ]
            
            guide += "\n".join(exception_scenarios)
            
            # 添加具体的业务异常码提示（如果API文档中有）
            responses = api_info.get("responses", {})
            if "400" in responses:
                guide += "\n\n# API文档中定义的400错误码："
                content_400 = responses["400"].get("content", {})
                if "application/json" in content_400:
                    examples = content_400["application/json"].get("examples", {})
                    for example_name, example_data in examples.items():
                        if "value" in example_data:
                            value = example_data["value"]
                            if isinstance(value, dict):
                                code = value.get("code")
                                msg = value.get("msg", "")
                                if code:
                                    guide += f"\n- 错误码 {code}: {msg}"
            
            # 添加错误码文件中的常见错误码参考
            if self.error_codes:
                guide += "\n\n# 飞书API常见错误码参考（请优先使用这些错误码）："
                # 选择与消息API相关的常见错误码
                relevant_codes = [
                    23001,      # 参数错误
                    99992402,   # 参数缺失或错误
                    99992351,   # open_id不存在
                    40008,      # open_id不存在
                    40051,      # open_id无效
                    230002,     # 机器人不在群内（如果适用）
                    40007,      # user_id不存在
                    40054,      # user_id或open_id缺失
                    99991672,   # 权限不足
                    99991663,   # token无效
                ]
                
                for code in relevant_codes:
                    if code in self.error_codes:
                        error_info = self.error_codes[code]
                        description = error_info.get("description", "")
                        # 简化描述，只取前80个字符
                        if len(description) > 80:
                            description = description[:80] + "..."
                        guide += f"\n- 错误码 {code}: {description}"
                
                guide += "\n\n**⚠️⚠️⚠️ 极其重要的错误码使用要求 ⚠️⚠️⚠️**："
                guide += "\n1. **必须**从上述错误码列表中选择，绝对不要使用列表中不存在的错误码"
                guide += "\n2. expected_response 中的 code **必须**是上述列表中的错误码之一"
                guide += "\n3. expected_response 中的 msg **必须**与错误码文件中的 description 保持一致或相似"
                guide += "\n4. **严禁编造错误码**：如果上述列表中没有合适的错误码，请选择最接近的错误码"
                guide += "\n5. 错误码选择建议："
                guide += "\n   - '缺失必填参数' → 使用 99992402 或 23001"
                guide += "\n   - '无效的ID（open_id/user_id不存在）' → 使用 99992351、40008 或 40051"
                guide += "\n   - '参数格式错误' → 使用 23001 或 99992402"
                guide += "\n   - '权限不足' → 使用 99991672"
                guide += "\n   - 'token无效' → 使用 99991663"
                guide += "\n6. **再次强调**：不要使用列表中不存在的错误码（如 230013、230002 等），如果必须使用，请先确认该错误码在 error_code.json 文件中存在"
        
        elif scenario_type == "boundary":
            guide = f"""
# 边界场景要求（{message_api_type}消息）：
- 生成1个边界场景测试用例
- 测试参数边界值（如最小长度、最大长度、边界枚举值等）
- **重要**：用例的 request_data 必须与 description 中描述的测试场景完全一致
- 例如：如果 description 说"content字段为空字符串"，则 request_data 中的 content 必须是空字符串 ""
- 根据实际情况判断是正常还是异常
- 如果边界值应该通过，预期HTTP 200，业务码 0
- 如果边界值应该失败，预期HTTP 400，业务码非 0（必须使用 error_code.json 中的错误码）

# 可测试的边界场景：
"""
            # 根据参数定义添加边界场景
            boundary_scenarios = []
            for param in body_params:
                param_name = param["name"]
                param_type = param.get("type", "string")
                
                if param_type == "string":
                    max_len = param.get("maxLength")
                    min_len = param.get("minLength")
                    
                    if max_len is not None:
                        boundary_scenarios.append(f"- {param_name}: 测试最大长度 {max_len}")
                    if min_len is not None:
                        boundary_scenarios.append(f"- {param_name}: 测试最小长度 {min_len}")
                    if param_name.lower() in ["content", "text"]:
                        boundary_scenarios.append(f"- {param_name}: 测试空字符串")
                
                elif param_type == "integer":
                    maximum = param.get("maximum")
                    minimum = param.get("minimum")
                    
                    if maximum is not None:
                        boundary_scenarios.append(f"- {param_name}: 测试最大值 {maximum}")
                    if minimum is not None:
                        boundary_scenarios.append(f"- {param_name}: 测试最小值 {minimum}")
                
                elif param.get("enum"):
                    enum_values = param["enum"]
                    if enum_values:
                        boundary_scenarios.append(f"- {param_name}: 测试第一个枚举值 '{enum_values[0]}'")
                        boundary_scenarios.append(f"- {param_name}: 测试最后一个枚举值 '{enum_values[-1]}'")
            
            if boundary_scenarios:
                guide += "\n".join(boundary_scenarios[:5])  # 限制数量
            else:
                guide += "- 参数长度边界\n- 数值边界\n- 枚举值边界"
        
        return guide
    
    def _build_parameter_guide(self, api_info: Dict[str, Any]) -> str:
        """构建参数使用指南"""
        path_params = api_info.get("path_params", [])
        query_params = api_info.get("query_params", [])
        body_params = api_info.get("body_params", [])
        required_params = api_info.get("required_params", [])
        
        guide_lines = []
        
        if path_params:
            guide_lines.append(f"路径参数（必须包含在URL中）: {', '.join(path_params)}")
        
        if query_params:
            guide_lines.append(f"查询参数（通过?key=value传递）: {', '.join(query_params)}")
        
        if body_params:
            body_info = []
            for param in body_params:
                name = param.get("name", "")
                required = "必填" if param.get("required") else "可选"
                param_type = param.get("type", "string")
                enum_info = f" 枚举值: {param.get('enum')}" if param.get("enum") else ""
                example_info = f" 示例: {param.get('example')}" if param.get("example") else ""
                body_info.append(f"  - {name} ({param_type}) [{required}]{enum_info}{example_info}")
            
            guide_lines.append("请求体参数:")
            guide_lines.extend(body_info)
        
        if required_params:
            guide_lines.append(f"\n⚠️ 必填参数（必须提供）: {', '.join(required_params)}")
        
        return "\n".join(guide_lines)
    
    def _build_message_type_guide(self, supported_msg_types: List[str]) -> str:
        """构建消息类型匹配指南"""
        msg_type_examples = {
            "text": {
                "msg_type": "text",
                "content": '{"text": "这是一条文本消息"}',
                "description": "普通文本消息"
            },
            "image": {
                "msg_type": "image",
                "content": '{"image_key": "img_v2_xxxxxxxx"}',
                "description": "图片消息（需要先上传图片获取image_key）"
            },
            "file": {
                "msg_type": "file",
                "content": '{"file_key": "file_v2_xxxxxxxx"}',
                "description": "文件消息（需要先上传文件获取file_key）"
            },
            "audio": {
                "msg_type": "audio",
                "content": '{"file_key": "file_v2_xxxxxxxx", "duration": 3000}',
                "description": "音频消息"
            },
            "media": {
                "msg_type": "media",
                "content": '{"file_key": "file_v2_xxxxxxxx", "image_key": "img_v2_xxxxxx"}',
                "description": "多媒体消息"
            },
            "sticker": {
                "msg_type": "sticker",
                "content": '{"file_key": "file_v2_xxxxxxxx"}',
                "description": "表情包消息"
            },
            "interactive": {
                "msg_type": "interactive",
                "content": '{"elements": [], "header": {"title": {"tag": "plain_text", "content": "标题"}}}',
                "description": "交互式消息卡片"
            }
        }
        
        guide_lines = ["# 消息类型匹配示例："]
        for msg_type in supported_msg_types:
            if msg_type in msg_type_examples:
                example = msg_type_examples[msg_type]
                guide_lines.append(f"- {msg_type}: {example['description']}")
                guide_lines.append(f"  msg_type: {example['msg_type']}")
                guide_lines.append(f"  content: {example['content']}")
        
        return "\n".join(guide_lines)
    
    def _build_scene_based_hint(self, files_data: Dict[str, Any], scenario_type: str) -> str:
        """基于scene文件构建场景提示"""
        hint = ""
        
        if not files_data.get("scene"):
            return hint
        
        scene_data = files_data["scene"]
        
        if "business_scenes" in scene_data:
            business_scenes = scene_data["business_scenes"]
            if "scenes" in business_scenes:
                scenes = business_scenes["scenes"]
                
                # 添加测试重点
                test_focus_all = set()
                for scene in scenes:
                    test_focus = scene.get("test_focus", [])
                    test_focus_all.update(test_focus)
                
                if test_focus_all:
                    hint += "\n# 业务场景测试重点：\n"
                    for focus in list(test_focus_all)[:5]:  # 限制数量
                        hint += f"- {focus}\n"
                
                # 添加异常场景（针对exception类型）
                if scenario_type == "exception":
                    exception_scenarios_all = []
                    for scene in scenes:
                        exception_scenarios = scene.get("exception_scenarios", [])
                        exception_scenarios_all.extend(exception_scenarios)
                    
                    if exception_scenarios_all:
                        hint += "\n# 业务场景异常情况：\n"
                        for exception in exception_scenarios_all[:10]:  # 限制数量
                            if isinstance(exception, str):
                                hint += f"- {exception}\n"
        
        return hint
    
    def build_message_scenario_prompt(self, api_info: Dict[str, Any], files_data: Dict[str, Any],
                                      scenario_type: str = "normal", external_params: Optional[Dict[str, Any]] = None) -> str:
        """构建消息场景的AI提示词"""
        
        # 获取OpenAPI内容
        openapi_content = ""
        if files_data.get("openapi"):
            openapi_content = yaml.dump(files_data["openapi"], allow_unicode=True, default_flow_style=False)
        
        # 提取API关键信息
        scenario_category = self.determine_scenario_category(api_info)
        supported_msg_types = api_info.get("supported_msg_types", ["text"])
        
        # 构建详细的场景指南
        scenario_guide = self._build_detailed_scenario_guide(api_info, scenario_type)
        
        # 构建参数指南
        param_guide = self._build_parameter_guide(api_info)
        
        # 构建消息类型指南
        msg_type_guide = self._build_message_type_guide(supported_msg_types)
        
        # 构建基于scene文件的提示
        scene_hint = self._build_scene_based_hint(files_data, scenario_type)
        
        # 构建额外提示
        extra_hint = f"""
# API基本信息：
- 接口类型：{scenario_category}消息
- 支持的消息类型：{', '.join(supported_msg_types)}
- 路径：{api_info.get('path', '')}
- 方法：{api_info.get('method', 'POST')}

{scenario_guide}

# 参数使用指南：
{param_guide}

# 消息类型匹配指南：
{msg_type_guide}

{scene_hint}

# 场景说明：
"""
        
        # 根据场景类型添加具体说明
        if scenario_type == "normal":
            extra_hint += f"""
- **必须生成2个完整的正常场景测试用例**，确保都能通过
- 所有必填字段必须给出合理值
- msg_type/content 要严格匹配
- 使用有效的 receive_id（从 RECEIVE_ID_MAP 选择）
- 预期HTTP状态码 200，业务码 0
- 2个用例应该测试不同的场景（如不同的msg_type、不同的参数组合等）
- **输出格式**：返回JSON数组，包含**恰好2个**测试用例对象
- **重要**：必须返回数组格式，即使只有一个用例也要用数组包裹
"""
        elif scenario_type == "exception":
            # 构建错误码列表供AI参考
            error_code_list = ""
            if self.error_codes:
                relevant_codes = [
                    23001,      # 参数错误
                    99992402,   # 参数缺失或错误
                    99992351,   # open_id不存在
                    40008,      # open_id不存在
                    40051,      # open_id无效
                    40007,      # user_id不存在
                    40054,      # user_id或open_id缺失
                    99991672,   # 权限不足
                    99991663,   # token无效
                ]
                error_code_list = "\n可用的错误码列表：\n"
                for code in relevant_codes:
                    if code in self.error_codes:
                        error_info = self.error_codes[code]
                        description = error_info.get("description", "")
                        if len(description) > 60:
                            description = description[:60] + "..."
                        error_code_list += f"- {code}: {description}\n"
            
            extra_hint += f"""
- **必须生成5个异常场景测试用例**，覆盖不同的异常情况
- 可以测试：缺失必填字段、字段类型错误、字段格式错误、无效ID、权限错误等
- 预期HTTP状态码400或500，业务码非0
- 异常描述要清晰，说明测试什么异常
- 5个用例应该覆盖不同的异常场景，确保多样性
{error_code_list}
- **必须使用上述错误码列表中的错误码**，绝对不要编造不存在的错误码
- **输出格式**：返回JSON数组，包含**恰好5个**测试用例对象
- **重要**：必须返回数组格式，包含5个用例，每个用例的expected_response中的code必须来自上述错误码列表
"""
        elif scenario_type == "boundary":
            extra_hint += """
- 生成1个边界场景测试用例
- 可以测试：字段长度边界、数值边界、枚举值边界等
- 根据测试结果判断是正常还是异常
- 如果边界值应该通过，预期HTTP 200，业务码 0
- 如果边界值应该失败，预期HTTP 400，业务码非 0
"""
        
        # 添加消息API类型的特定提示
        message_api_type = api_info.get("message_api_type", "unknown")
        if message_api_type == "reply":
            extra_hint += "\n# 回复消息特定要求：\n- 需要有效的 message_id（路径参数）\n- 回复内容要合理\n"
        elif message_api_type == "forward":
            extra_hint += "\n# 转发消息特定要求：\n- 需要有效的 message_id（路径参数）\n- 可以指定转发目标\n"
        elif message_api_type == "delete":
            extra_hint += "\n# 删除消息特定要求：\n- 需要有效的 message_id（路径参数）\n- 通常不需要请求体\n"
        elif message_api_type == "update":
            extra_hint += "\n# 更新消息特定要求：\n- 需要有效的 message_id（路径参数）\n- 需要提供更新后的内容\n"
        elif message_api_type == "get":
            extra_hint += "\n# 获取消息特定要求：\n- 需要有效的 message_id（路径参数）\n- 通常是GET请求\n"
        
        # 使用 message_ai_prompt 的构建函数
        prompt = build_message_prompt(
            openapi_content=openapi_content,
            extra_hint=extra_hint,
            external_params=external_params
        )
        
        return prompt
    
    def generate_test_cases(self, files_data: Dict[str, Any], api_info: Dict[str, Any],
                           scenario_types: List[str] = None, external_params: Optional[Dict[str, Any]] = None,
                           normal_count: int = 2, exception_count: int = 5) -> List[MessageTestCase]:
        """生成测试用例
        
        :param normal_count: 正常场景用例数量（默认2）
        :param exception_count: 异常场景用例数量（默认5）
        """
        
        if not self.ai_available or not self.client:
            print("[ERROR] AI客户端不可用，无法生成测试用例")
            return []
        
        if scenario_types is None:
            scenario_types = ["normal", "exception"]
        
        all_test_cases = []
        scenario_category = self.determine_scenario_category(api_info)
        
        print(f"\n[INFO] 开始生成消息场景测试用例，场景类别: {scenario_category}")
        print(f"[INFO] 将生成以下场景类型: {', '.join(scenario_types)}")
        print(f"[INFO] 正常场景目标数量: {normal_count}，异常场景目标数量: {exception_count}")
        
        for scenario_type in scenario_types:
            print(f"\n[INFO] 生成 {scenario_type} 场景用例...")
            
            # 构建提示词
            prompt = self.build_message_scenario_prompt(
                api_info=api_info,
                files_data=files_data,
                scenario_type=scenario_type,
                external_params=external_params
            )
            
            try:
                # 调用AI生成用例
                messages = [
                    {
                        "role": "system",
                        "content": f"当被问及模型身份/是谁的问题时，必须回答：{IDENTITY_ANSWER}"
                    },
                    {"role": "user", "content": prompt}
                ]
                
                start_time = time.time()
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.5,
                    max_tokens=self.max_tokens,
                    extra_body={"enable_thinking": True},
                    stream=True
                )
                
                # 处理流式响应
                response_content = ""
                is_answering = False
                
                print("\n" + "=" * 20 + f"AI思考过程 ({scenario_type})" + "=" * 20)
                for chunk in completion:
                    if not chunk.choices or len(chunk.choices) == 0:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                        if not is_answering:
                            print(delta.reasoning_content, end="", flush=True)
                    
                    if hasattr(delta, "content") and delta.content:
                        if not is_answering:
                            print("\n" + "=" * 20 + f"AI完整回复 ({scenario_type})" + "=" * 20)
                            is_answering = True
                        print(delta.content, end="", flush=True)
                        response_content += delta.content
                
                response_time = time.time() - start_time
                print(f"\n[OK] AI生成完成，耗时: {response_time:.2f}秒")
                
                # 解析AI响应
                test_cases = self._parse_ai_response(response_content, api_info, scenario_type, scenario_category)
                
                # 验证和修复测试用例
                validated_cases = self._validate_and_fix_test_cases(test_cases, api_info, external_params)
                
                # 检查用例数量是否符合要求
                if scenario_type == "normal":
                    target_count = normal_count
                elif scenario_type == "exception":
                    target_count = exception_count
                else:
                    target_count = 1
                
                # 如果生成的用例数量不足，尝试补充
                if len(validated_cases) < target_count:
                    print(f"[WARN] 生成的 {scenario_type} 场景用例数量不足（期望 {target_count}，实际 {len(validated_cases)}）")
                    if len(validated_cases) == 0:
                        print(f"[ERROR] 未能生成任何 {scenario_type} 场景用例，请检查AI响应")
                    else:
                        # 如果生成的用例数量不足，尝试基于现有用例生成补充用例
                        print(f"[INFO] 尝试基于现有用例生成补充用例...")
                        # 这里可以添加补充逻辑，暂时只记录警告
                elif len(validated_cases) > target_count:
                    print(f"[INFO] 生成的 {scenario_type} 场景用例数量超过目标（期望 {target_count}，实际 {len(validated_cases)}），将使用前 {target_count} 个")
                    validated_cases = validated_cases[:target_count]
                else:
                    print(f"[OK] 生成的 {scenario_type} 场景用例数量符合要求（期望 {target_count}，实际 {len(validated_cases)}）")
                
                all_test_cases.extend(validated_cases)
                
                if validated_cases:
                    print(f"[OK] 成功生成 {len(validated_cases)} 个 {scenario_type} 场景用例")
                else:
                    print(f"[WARN] 未能生成有效的 {scenario_type} 场景用例")
                
            except Exception as e:
                print(f"[ERROR] 生成 {scenario_type} 场景用例失败: {e}")
                import traceback
                traceback.print_exc()
        
        return all_test_cases
    
    def _parse_ai_response(self, response_content: str, api_info: Dict[str, Any],
                          scenario_type: str, scenario_category: str) -> List[MessageTestCase]:
        """解析AI响应"""
        
        # 尝试提取JSON
        cases_json = _extract_json(response_content)
        
        if not cases_json:
            print("[WARN] 未能从AI响应中解析出JSON")
            # 尝试从响应中提取用例信息
            return self._extract_cases_from_text(response_content, api_info, scenario_type, scenario_category)
        
        # 统一为列表格式
        if isinstance(cases_json, dict):
            cases_data = [cases_json]
        elif isinstance(cases_json, list):
            cases_data = cases_json
        else:
            return []
        
        test_cases = []
        operation_id = api_info.get("operation_id", "api").lower()
        
        for i, case_data in enumerate(cases_data):
            if not isinstance(case_data, dict):
                continue
            
            # 验证必要字段
            if not all(k in case_data for k in ["name", "request_data"]):
                print(f"[WARN] 测试用例 {i} 缺少必要字段，跳过")
                continue
            
            # 生成测试用例名称
            test_case_name = f"test_{operation_id}_{scenario_type}_{i+1}"
            
            # 判断是否为成功场景
            expected_status_code = case_data.get("expected_status_code", 200 if scenario_type == "normal" else 400)
            expected_response = case_data.get("expected_response", {})
            is_success = scenario_type == "normal" or expected_status_code == 200
            
            test_case = MessageTestCase(
                name=case_data.get("name", f"{scenario_type}场景用例{i+1}"),
                description=case_data.get("description", ""),
                test_type=scenario_type,
                scenario_category=scenario_category,
                request_data=case_data.get("request_data", {}),
                expected_status_code=expected_status_code,
                expected_response=expected_response,
                test_case_name=test_case_name,
                tags=case_data.get("tags", [scenario_type]),
                is_success=is_success
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def _extract_cases_from_text(self, response_content: str, api_info: Dict[str, Any],
                                scenario_type: str, scenario_category: str) -> List[MessageTestCase]:
        """从文本中提取用例信息（当JSON解析失败时）"""
        test_cases = []
        
        # 简单地从文本中提取用例信息
        lines = response_content.split('\n')
        case_name = ""
        case_desc = ""
        in_case = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测用例开始
            if "用例" in line or "case" in line.lower():
                if case_name and case_desc:
                    # 创建测试用例
                    test_case = self._create_fallback_test_case(
                        case_name, case_desc, api_info, scenario_type, scenario_category
                    )
                    test_cases.append(test_case)
                
                case_name = line
                case_desc = ""
                in_case = True
            elif in_case and ("请求" in line or "预期" in line or "expect" in line.lower()):
                case_desc += line + "\n"
        
        # 处理最后一个用例
        if case_name and case_desc:
            test_case = self._create_fallback_test_case(
                case_name, case_desc, api_info, scenario_type, scenario_category
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def _create_fallback_test_case(self, case_name: str, case_desc: str, api_info: Dict[str, Any],
                                  scenario_type: str, scenario_category: str) -> MessageTestCase:
        """创建备用测试用例"""
        operation_id = api_info.get("operation_id", "api").lower()
        test_case_name = f"test_{operation_id}_{scenario_type}_{hash(case_name) % 1000}"
        
        # 根据场景类型确定期望状态码
        expected_status_code = 200 if scenario_type == "normal" else 400
        is_success = scenario_type == "normal"
        
        # 构建简单的请求数据
        request_data = {
            "method": api_info.get("method", "POST"),
            "url": api_info.get("path", "/"),
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": {}
        }
        
        # 根据API类型添加基本参数
        if scenario_category in ["create", "reply", "update"]:
            request_data["body"]["receive_id"] = self.receive_id_map.get("open_id", {}).get("user_1", "ou_xxxxxxxx")
            request_data["body"]["msg_type"] = "text"
            request_data["body"]["content"] = '{"text": "测试消息"}'
        
        # 添加查询参数
        request_data["query_params"] = {"receive_id_type": "open_id"}
        
        return MessageTestCase(
            name=case_name,
            description=case_desc,
            test_type=scenario_type,
            scenario_category=scenario_category,
            request_data=request_data,
            expected_status_code=expected_status_code,
            expected_response={"code": 0 if is_success else 230001, "msg": "success" if is_success else "error"},
            test_case_name=test_case_name,
            tags=[scenario_type],
            is_success=is_success
        )
    
    def _validate_and_fix_test_cases(self, test_cases: List[MessageTestCase], api_info: Dict[str, Any],
                                    external_params: Optional[Dict[str, Any]] = None) -> List[MessageTestCase]:
        """验证并修复测试用例"""
        validated_cases = []
        
        for test_case in test_cases:
            # 验证必填参数
            fixed_case = self._fix_missing_required_params(test_case, api_info, external_params)
            
            # 验证消息类型匹配
            fixed_case = self._fix_msg_type_mismatch(fixed_case)
            
            # 验证参数格式
            fixed_case = self._fix_parameter_format(fixed_case)
            
            validated_cases.append(fixed_case)
        
        return validated_cases
    
    def _fix_missing_required_params(self, test_case: MessageTestCase, api_info: Dict[str, Any],
                                    external_params: Optional[Dict[str, Any]] = None) -> MessageTestCase:
        """修复缺失的必填参数"""
        required_params = api_info.get("required_params", [])
        body_params = api_info.get("body_params", [])
        required_body_params = [p["name"] for p in body_params if p.get("required")]
        
        request_data = test_case.request_data
        body = request_data.get("body") or request_data.get("payload") or request_data.get("json") or {}
        
        if not isinstance(body, dict):
            body = {}
        
        # 检查并修复必填参数
        for param in required_body_params:
            if param not in body:
                # 提供合理的默认值
                if param == "receive_id":
                    if external_params and "receive_id" in external_params:
                        body["receive_id"] = external_params["receive_id"]
                    else:
                        body["receive_id"] = self.receive_id_map.get("open_id", {}).get("user_1", "ou_xxxxxxxx")
                elif param == "msg_type":
                    body["msg_type"] = "text"
                elif param == "content":
                    body["content"] = '{"text": "测试消息"}'
                elif param == "uuid":
                    body["uuid"] = str(uuid.uuid4())
        
        # 更新请求数据
        if "body" in request_data:
            request_data["body"] = body
        elif "payload" in request_data:
            request_data["payload"] = body
        elif "json" in request_data:
            request_data["json"] = body
        else:
            request_data["body"] = body
        
        test_case.request_data = request_data
        return test_case
    
    def _fix_msg_type_mismatch(self, test_case: MessageTestCase) -> MessageTestCase:
        """修复消息类型不匹配"""
        request_data = test_case.request_data
        body = request_data.get("body") or request_data.get("payload") or request_data.get("json") or {}
        
        if isinstance(body, dict):
            msg_type = body.get("msg_type", "text")
            content = body.get("content", "")
            
            # 确保 content 与 msg_type 匹配
            if msg_type == "text" and (not content or '{"text":' not in str(content)):
                body["content"] = '{"text": "这是一条文本测试消息"}'
            elif msg_type == "image" and (not content or '"image_key"' not in str(content)):
                body["content"] = '{"image_key": "img_v2_test_image_key"}'
            elif msg_type == "file" and (not content or '"file_key"' not in str(content)):
                body["content"] = '{"file_key": "file_v2_test_file_key"}'
            elif msg_type == "audio" and (not content or '"file_key"' not in str(content)):
                body["content"] = '{"file_key": "file_v2_test_audio_key", "duration": 3000}'
            
            # 更新请求数据
            if "body" in request_data:
                request_data["body"] = body
            elif "payload" in request_data:
                request_data["payload"] = body
            elif "json" in request_data:
                request_data["json"] = body
        
        return test_case
    
    def _fix_parameter_format(self, test_case: MessageTestCase) -> MessageTestCase:
        """修复参数格式"""
        request_data = test_case.request_data
        
        # 确保有 query_params
        if "query_params" not in request_data:
            request_data["query_params"] = {}
        
        # 确保有合适的 headers
        if "headers" not in request_data:
            request_data["headers"] = {"Content-Type": "application/json; charset=utf-8"}
        
        # 确保 method 存在
        if "method" not in request_data:
            request_data["method"] = "POST"
        
        return test_case
    
    def generate_pytest_file(self, api_info: Dict[str, Any], test_cases: List[MessageTestCase],
                            output_path: Path, external_params: Optional[Dict[str, Any]] = None):
        """生成pytest测试文件"""
        
        # 转换为通用格式
        cases_dict = []
        for tc in test_cases:
            cases_dict.append({
                "name": tc.name,
                "description": tc.description,
                "test_type": tc.test_type,
                "request_data": tc.request_data,
                "expected_status_code": tc.expected_status_code,
                "expected_response": tc.expected_response,
                "tags": tc.tags,
                "is_success": tc.is_success
            })
        
        # 生成pytest文件
        generate_pytest_from_cases(
            cases=cases_dict,
            api_info=api_info,
            out_path=output_path,
            external_params=external_params
        )
    
    def _analyze_case_quality(self, test_cases: List[MessageTestCase], 
                             api_info: Dict[str, Any]) -> Dict[str, float]:
        """分析用例质量"""
        total_cases = len(test_cases)
        if total_cases == 0:
            return {}
        
        stats = {
            "required_params_complete": 0,
            "msg_type_matched": 0,
            "parameter_format_correct": 0
        }
        
        body_params = api_info.get("body_params", [])
        required_body_params = [p["name"] for p in body_params if p.get("required")]
        supported_msg_types = api_info.get("supported_msg_types", ["text"])
        
        for test_case in test_cases:
            request_data = test_case.request_data
            body = request_data.get("body") or request_data.get("payload") or request_data.get("json") or {}
            
            # 检查必填参数
            if all(param in body for param in required_body_params):
                stats["required_params_complete"] += 1
            
            # 检查消息类型匹配
            msg_type = body.get("msg_type", "")
            if msg_type in supported_msg_types:
                stats["msg_type_matched"] += 1
            
            # 检查参数格式（简化检查）
            if isinstance(body, dict) and all(isinstance(v, (str, int, float, bool, dict, list)) for v in body.values()):
                stats["parameter_format_correct"] += 1
        
        # 计算百分比
        quality_stats = {
            "required_params_complete_rate": round(stats["required_params_complete"] / total_cases * 100, 2) if total_cases > 0 else 0,
            "msg_type_match_rate": round(stats["msg_type_matched"] / total_cases * 100, 2) if total_cases > 0 else 0,
            "parameter_format_rate": round(stats["parameter_format_correct"] / total_cases * 100, 2) if total_cases > 0 else 0
        }
        
        return quality_stats
    
    def generate_all(self, base_name: str, base_dir: str = "uploads",
                     output_dir: str = "tests", scenario_types: List[str] = None,
                     external_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成所有测试用例"""
        
        print("\n" + "=" * 60)
        print("消息场景专用测试用例生成器")
        print("=" * 60)
        
        # 步骤1: 加载文件
        print("\n1. 加载相关文件")
        files_data = self.load_files(base_name, base_dir)
        
        # 步骤2: 提取API信息
        print("\n2. 提取API信息")
        api_info = self.extract_api_info(files_data, base_name)
        
        if not api_info.get("path"):
            print("[ERROR] 未能提取到API路径信息")
            return {"error": "未能提取到API路径信息"}
        
        print(f"  - API路径: {api_info['path']}")
        print(f"  - 方法: {api_info['method']}")
        print(f"  - 操作ID: {api_info['operation_id']}")
        print(f"  - 消息API类型: {api_info.get('message_api_type', 'unknown')}")
        print(f"  - 支持的消息类型: {', '.join(api_info.get('supported_msg_types', ['text']))}")
        
        # 步骤3: 生成测试用例
        print("\n3. 使用AI生成测试用例")
        # 确保生成2个正常场景和5个异常场景
        test_cases = self.generate_test_cases(
            files_data=files_data,
            api_info=api_info,
            scenario_types=scenario_types or ["normal", "exception"],
            external_params=external_params,
            normal_count=2,  # 固定生成2个正常场景
            exception_count=5  # 固定生成5个异常场景
        )
        
        if not test_cases:
            print("[ERROR] 未能生成测试用例")
            return {"error": "未能生成测试用例"}
        
        # 步骤4: 生成pytest文件
        print("\n4. 生成pytest测试文件")
        output_path = Path(base_dir) / output_dir / f"test_ai_message_{base_name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.generate_pytest_file(api_info, test_cases, output_path, external_params)
        
        # 步骤5: 汇总结果
        print("\n5. 汇总结果")
        normal_count = sum(1 for tc in test_cases if tc.test_type == "normal")
        exception_count = sum(1 for tc in test_cases if tc.test_type == "exception")
        boundary_count = sum(1 for tc in test_cases if tc.test_type == "boundary")
        
        # 统计用例质量
        quality_stats = self._analyze_case_quality(test_cases, api_info)
        
        result = {
            "base_name": base_name,
            "api_path": api_info["path"],
            "operation_id": api_info["operation_id"],
            "message_api_type": api_info.get("message_api_type", "unknown"),
            "scenario_category": test_cases[0].scenario_category if test_cases else "unknown",
            "total_test_cases": len(test_cases),
            "normal_test_cases": normal_count,
            "exception_test_cases": exception_count,
            "boundary_test_cases": boundary_count,
            "generated_file": str(output_path),
            "test_cases": [tc.to_dict() for tc in test_cases],
            "quality_stats": quality_stats
        }
        
        print(f"\n[OK] 生成完成!")
        print(f"  - 总测试用例数: {result['total_test_cases']}")
        print(f"  - 正常场景: {result['normal_test_cases']}")
        print(f"  - 异常场景: {result['exception_test_cases']}")
        print(f"  - 边界场景: {result['boundary_test_cases']}")
        print(f"  - 测试文件: {result['generated_file']}")
        
        # 打印质量统计
        if quality_stats:
            print(f"\n[INFO] 用例质量统计:")
            print(f"  - 必填参数完整率: {quality_stats.get('required_params_complete_rate', 0)}%")
            print(f"  - 消息类型匹配率: {quality_stats.get('msg_type_match_rate', 0)}%")
            print(f"  - 参数格式正确率: {quality_stats.get('parameter_format_rate', 0)}%")
        
        return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="消息场景专用测试用例生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--base-name", required=True,
                       help="接口基础名称（如: feishu_server-docs_im-v1_message_create）")
    parser.add_argument("--base-dir", default="uploads",
                       help="文件基础目录（默认: uploads）")
    parser.add_argument("--api-key", help="AI API Key（可选，默认从环境变量读取）")
    parser.add_argument("--model", default=DEFAULT_AI_MODEL, help="AI模型名称")
    parser.add_argument("--base-url", default=DEFAULT_AI_BASE_URL, help="AI API网关")
    parser.add_argument("--output-dir", default="tests", help="输出目录")
    parser.add_argument("--scenario-types", nargs="+", 
                       choices=["normal", "exception", "boundary"],
                       default=["normal", "exception", "boundary"],
                       help="要生成的场景类型（默认: 全部）")
    parser.add_argument("--external-params", help="外部传入的参数值（JSON格式），如 '{\"message_id\":\"om_xxx\"}'")
    
    args = parser.parse_args()
    
    # 解析外部参数
    external_params = None
    if args.external_params:
        try:
            external_params = json.loads(args.external_params)
            print(f"[INFO] 成功解析外部参数: {external_params}")
        except json.JSONDecodeError as e:
            print(f"[WARN] 无法解析外部参数: {e}")
            print(f"[WARN] 将使用环境变量或占位符")
    
    # 创建生成器
    generator = MessageScenarioGenerator(
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url
    )
    
    # 生成测试用例
    result = generator.generate_all(
        base_name=args.base_name,
        base_dir=args.base_dir,
        output_dir=args.output_dir,
        scenario_types=args.scenario_types,
        external_params=external_params
    )
    
    if "error" in result:
        print(f"[ERROR] 生成失败: {result['error']}")
        sys.exit(1)
    
    print("\n[OK] 所有测试用例已生成完成！")


if __name__ == "__main__":
    main()