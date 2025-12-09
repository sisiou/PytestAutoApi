#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用自动化测试用例生成器 - 专注于异常值和边界值测试
支持读取四个文件：scene、relation、json、openapi
通过AI生成异常值和边界值测试用例
"""

import sys
import argparse
import os
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
import yaml
import requests

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[WARN] openai库未安装，请安装: pip install openai")

# ================= 配置区域 =================
# 从环境变量读取所有配置
import os
from dotenv import load_dotenv

# 加载.env文件
# 尝试从项目根目录加载.env文件
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

# 从环境变量读取AI配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")  # AI API Key
DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "deepseek-v3.2")
DEFAULT_AI_BASE_URL = os.getenv("DEFAULT_AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DEFAULT_AI_TIMEOUT = int(os.getenv("DEFAULT_AI_TIMEOUT", "120"))  # AI API调用超时时间（秒）
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1300"))  # 最大token数

# 从环境变量读取飞书应用配置
DEFAULT_APP_ID = os.getenv("FEISHU_APP_ID")  # 飞书应用App ID
DEFAULT_APP_SECRET = os.getenv("FEISHU_APP_SECRET")  # 飞书应用App Secret
DEFAULT_USER_ID = os.getenv("FEISHU_USER_ID")  # 飞书用户ID
# 导入feishu_config以使用自动刷新令牌
try:
    # 尝试从项目根目录导入
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from utils.feishu_config import feishu_config
    DEFAULT_AUTHORIZATION = feishu_config.get_authorization()  # 使用自动刷新的令牌
except ImportError:
    DEFAULT_AUTHORIZATION = os.getenv("FEISHU_AUTHORIZATION")  # 飞书授权码（备用方案）

# 从环境变量读取API配置
FEISHU_API_BASE_URL = os.getenv("FEISHU_API_BASE_URL", "https://open.feishu.cn/open-apis")
FEISHU_API_TIMEOUT = int(os.getenv("FEISHU_API_TIMEOUT", "30"))

# 从环境变量读取接收者ID配置
DEFAULT_RECEIVE_ID_TYPE = os.getenv("DEFAULT_RECEIVE_ID_TYPE")
DEFAULT_RECEIVE_ID = os.getenv("DEFAULT_RECEIVE_ID")

# 从环境变量读取真实资源示例
DEFAULT_CALENDAR_ID = os.getenv("DEFAULT_CALENDAR_ID")
DEFAULT_IMAGE_KEY = os.getenv("DEFAULT_IMAGE_KEY")

# 接收者ID映射（可从环境变量读取JSON字符串，否则使用默认值）

    
RECEIVE_ID_MAP = {
    "user_id": os.getenv("DEFAULT_USER_ID"),  # 默认 user_id
    "open_id": os.getenv("FEISHU_OPEN_ID"),  # open_id 格式示例
    "union_id": os.getenv("FEISHU_UNION_ID"),  # union_id 格式示例
    "email": os.getenv("DEFAULT_EMAIL"),  # email 格式示例
    "chat_id": os.getenv("FEISHU_CHAT_ID"),  # chat_id 格式示例
}

# ===========================================

@dataclass
class TestCase:
    """测试用例数据类"""
    name: str
    description: str
    test_type: str  # "normal" 或 "exception"
    request_data: Dict[str, Any]
    expected_status_code: int
    expected_response: Dict[str, Any]
    test_case_name: str = ""
    tags: List[str] = field(default_factory=list)
    is_success: bool = True  # 是否为成功场景
    
    def to_dict(self):
        return asdict(self)

class UniversalAITestGenerator:
    """通用AI测试用例生成器（专注于异常值和边界值）"""
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None,
                 app_id: str = None, app_secret: str = None, user_id: str = None, 
                 authorization: str = None, timeout: int = None, max_tokens: int = None):
        # 优先级：传入参数 > 环境变量配置
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.model = model or DEFAULT_AI_MODEL
        self.base_url = base_url or DEFAULT_AI_BASE_URL
        self.app_id = app_id or DEFAULT_APP_ID
        self.app_secret = app_secret or DEFAULT_APP_SECRET
        self.user_id = user_id or DEFAULT_USER_ID
        self.authorization = authorization or DEFAULT_AUTHORIZATION
        self.timeout = timeout or DEFAULT_AI_TIMEOUT
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.receive_id_type = DEFAULT_RECEIVE_ID_TYPE
        self.receive_id = DEFAULT_RECEIVE_ID or self.user_id or "test_user_id"
        self.receive_id_map = RECEIVE_ID_MAP
        self.feishu_api_base_url = FEISHU_API_BASE_URL
        self.feishu_api_timeout = FEISHU_API_TIMEOUT
        
        self.client = None
        self.ai_available = False
        self.token_cache = None
        self.token_expire_time = 0
        
        self._init_ai_client()
    
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
            print(f"[OK] AI客户端初始化成功，使用模型: {self.model}，超时时间: {self.timeout}秒")
        except Exception as e:
            print(f"[ERROR] AI客户端初始化失败: {e}")
    
    def get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        if requests is None:
            print("[ERROR] 错误: 需要安装 requests 库才能获取 token")
            return None
        
        # 检查缓存
        current_time = time.time()
        if self.token_cache and current_time < self.token_expire_time:
            return self.token_cache
        
        url = f"{self.feishu_api_base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.feishu_api_timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                expire = data.get("expire", 0)
                # 缓存token（提前5分钟过期）
                self.token_cache = token
                self.token_expire_time = current_time + expire - 300
                print(f"[OK] 成功获取 tenant_access_token (过期时间: {expire} 秒)")
                return token
            print(f"[ERROR] 获取 token 失败: code={data.get('code')} msg={data.get('msg')}")
            return None
        except Exception as exc:
            print(f"[ERROR] 获取 token 出错: {exc}")
            return None
    
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
    
    def extract_api_info(self, files_data: Dict[str, Any]) -> Dict[str, Any]:
        """从文件中提取API信息"""
        api_info = {
            "path": "",
            "method": "",
            "operation_id": "",
            "summary": "",
            "description": "",
            "parameters": [],
            "request_body": {},
            "responses": {},
            "security": [],
            "examples": {},
            "components": {}
        }
        
        # 从openapi文件提取
        if files_data.get("openapi"):
            openapi_data = files_data["openapi"]
            paths = openapi_data.get("paths", {})
            api_info["components"] = openapi_data.get("components", {})
            
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
                            api_info["parameters"] = operation_data.get("parameters", [])
                            api_info["request_body"] = operation_data.get("requestBody", {})
                            api_info["responses"] = operation_data.get("responses", {})
                            api_info["security"] = operation_data.get("security", [])
                            
                            # 提取示例
                            if "requestBody" in operation_data:
                                content = operation_data["requestBody"].get("content", {})
                                if "application/json" in content:
                                    if "example" in content["application/json"]:
                                        api_info["examples"]["request"] = content["application/json"]["example"]
                                    if "examples" in content["application/json"]:
                                        api_info["examples"]["request_examples"] = content["application/json"]["examples"]
                            
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
        
        return api_info
    
    def build_ai_prompt(self, api_info: Dict[str, Any], files_data: Dict[str, Any]) -> str:
        """构建AI提示词（专注于异常值和边界值测试）"""
        
        # 提取关键信息
        path = api_info.get("path", "")
        method = api_info.get("method", "")
        operation_id = api_info.get("operation_id", "")
        summary = api_info.get("summary", "")
        description = api_info.get("description", "")
        parameters = api_info.get("parameters", [])
        request_body = api_info.get("request_body", {})
        responses = api_info.get("responses", {})
        examples = api_info.get("examples", {})
        
        # 提取请求参数信息，按类型分类
        path_params = []
        query_params = []
        header_params = []
        for param in parameters:
            param_info = {
                "name": param.get("name", ""),
                "in": param.get("in", ""),
                "required": param.get("required", False),
                "type": param.get("schema", {}).get("type", ""),
                "description": param.get("description", ""),
                "minLength": param.get("schema", {}).get("minLength"),
                "maxLength": param.get("schema", {}).get("maxLength"),
                "minimum": param.get("schema", {}).get("minimum"),
                "maximum": param.get("schema", {}).get("maximum"),
                "enum": param.get("schema", {}).get("enum", []),
            }
            param_in = param.get("in", "").lower()
            if param_in == "path":
                path_params.append(param_info)
            elif param_in == "query":
                query_params.append(param_info)
            elif param_in == "header":
                header_params.append(param_info)
        
        # 为了兼容，保留原有的 param_info（包含所有参数）
        param_info = path_params + query_params + header_params
        
        # 提取请求体信息
        request_body_info = {}
        request_body_schema = None
        components = api_info.get("components", {})
        if request_body:
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                resolved_schema = self._resolve_ref(schema, components)
                request_body_schema = resolved_schema
                request_body_info = self._extract_schema_info(resolved_schema, components=components)
        
        # 提取异常场景（从scene文件）
        exception_scenarios = []
        if files_data.get("scene") and "business_scenes" in files_data["scene"]:
            scenes = files_data["scene"]["business_scenes"].get("scenes", [])
            for scene in scenes:
                exceptions = scene.get("exception_scenarios", [])
                exception_scenarios.extend(exceptions)
        
        # 检查API是否需要 receive_id / receive_id_type / msg_type 参数
        needs_receive_id = False
        receive_id_type_param = None
        needs_msg_type_param = False
        
        # 检查请求参数中是否有 receive_id_type / msg_type
        for param in parameters:
            param_name = param.get("name", "").lower()
            if param_name in ["receive_id_type", "receive_id"]:
                needs_receive_id = True
                if param_name == "receive_id_type":
                    receive_id_type_param = param
            if param_name in ["msg_type", "msgtype", "message_type"]:
                needs_msg_type_param = True
        
        # 检查请求体中是否有 receive_id / msg_type 字段
        if not needs_receive_id and request_body_info:
            for field_name in request_body_info.keys():
                if "receive_id" in field_name.lower():
                    needs_receive_id = True
                    break
        if not needs_msg_type_param and request_body_info:
            for field_name in request_body_info.keys():
                if "msg_type" in field_name.lower() or "msgtype" in field_name.lower():
                    needs_msg_type_param = True
                    break
        
        # 构建接收者ID配置部分（仅在需要时添加）
        msg_type_hint = ""
        receive_id_config = ""
        if needs_receive_id:
            receive_id_config = f"""
# 接收者ID配置（请使用这些真实值，不要编造）
- DEFAULT_RECEIVE_ID_TYPE: "{self.receive_id_type}"
- DEFAULT_RECEIVE_ID: "{self.receive_id}"
- RECEIVE_ID_MAP: {json.dumps(self.receive_id_map, ensure_ascii=False, indent=2)}
**重要**：如果测试用例中需要使用接收者ID（如user_id、open_id、union_id、email、chat_id等），请使用上面提供的真实值，不要编造或使用示例值。
"""
        resource_config = f"""
# 真实资源示例（请优先复用，避免乱造导致404/校验失败）
- calendar_id: "{DEFAULT_CALENDAR_ID}"
- image_key: "{DEFAULT_IMAGE_KEY}"
"""
        if needs_msg_type_param:
            msg_type_hint = "\n# 提示：请求包含 msg_type 参数，请务必在 request_data 中填写有效的 msg_type（如 text）"
        
        prompt = f"""你是一个专业的软件测试工程师，擅长编写API的异常值和边界值测试用例。不要请求参数中出现以下字段 expected_status、url_path、expected_code、response_time

# 接口信息
- 路径: {path}
- 方法: {method}
- 操作ID: {operation_id}
- 摘要: {summary}
- 描述: {description}

# 请求参数信息（按类型分类）
## 路径参数（path parameters）- 需要替换到URL路径中，例如 /api/users/{{user_id}} 中的 user_id
{json.dumps(path_params, ensure_ascii=False, indent=2) if path_params else "无路径参数"}

## 查询参数（query parameters）- 需要放在URL查询字符串中，例如 ?receive_id_type=user_id&page=1
{json.dumps(query_params, ensure_ascii=False, indent=2) if query_params else "无查询参数"}

## 请求头参数（header parameters）- 需要放在HTTP请求头中不要出现以下字段 expected_status、url_path、expected_code、response_time
{json.dumps(header_params, ensure_ascii=False, indent=2) if header_params else "无请求头参数"}

# 请求体信息（request body）- 需要放在HTTP请求体中（JSON格式）,不要出现以下字段 expected_status、url_path、expected_code、response_time
{json.dumps(request_body_info, ensure_ascii=False, indent=2) if request_body_info else "无请求体"}

# ⚠️⚠️⚠️ 请求体必填字段列表（极其重要：这些字段必须在所有正常场景测试用例中出现，绝对不能遗漏）⚠️⚠️⚠️
{self._get_required_fields_summary(request_body_schema, components) if request_body_schema else "无请求体"}

**⚠️ 关键提醒（必须严格遵守，直接影响测试通过率）**：
1. 上面的必填字段列表中的**每一个字段**都必须出现在**所有正常场景测试用例**的request_data中
2. 如果遗漏任何必填字段，(如msg_type))API会返回400错误（field validation failed），测试用例会失败
3. 生成测试用例后，请对照上面的必填字段列表，逐一检查每个正常场景的request_data是否包含所有字段
4. 如果发现缺少任何字段，必须立即补充，使用合理的默认值或示例值
5. 如果存在 uuid 字段，长度必须 ≤ 50 字符（超长将返回400，field validation failed）
6. msg_type 必须与 content 类型匹配，不能全部写成 "text"。例如纯文本用 text，富文本/卡片用 post，图片用 image，结构体按 OpenAPI 的定义选择。
7. type 字段同样必须依据 OpenAPI 的枚举/示例选择，不能写死固定值；无枚举/示例时请明确标注占位值并说明需人工确认。
8. 如需要 calendar_id / image_key，请直接使用提供的真实值，避免自造无效资源导致404：
   - calendar_id: "{DEFAULT_CALENDAR_ID}"
   - image_key: "{DEFAULT_IMAGE_KEY}"

# 响应信息
{json.dumps(list(responses.keys()), ensure_ascii=False)}

# 已知异常场景
{json.dumps(exception_scenarios, ensure_ascii=False, indent=2)}

# 请求示例
{json.dumps(examples.get("request", {}), ensure_ascii=False, indent=2) if examples.get("request") else "无"}
{receive_id_config}{msg_type_hint}

# 任务要求
请为以上API接口生成**总共6~8个测试用例**，要求：

1. **正常场景测试用例（5~6个）**：
   - 覆盖典型、完整字段、最小必填、边界/可选字段组合等多种正常输入。
   - **⚠️必须包含上面"请求体必填字段列表"中的每一个字段，一个都不能少！未标明“非必填”的字段也不能少。**
   - 根据字段定义选择合适的 msg_type / type / content 形态，确保匹配。
   
   **关键检查点**：生成每个正常场景测试用例后，请检查request_data是否包含了必填字段列表中的每一个字段。如果缺少任何一个，必须补充！

2. **异常场景测试用例（1~2个）**：
   - 选择最重要的异常场景：优先缺失必填字段；如字段都可选，则用类型错误或格式错误。
   - 异常场景判定：只要 HTTP 状态码不是 200 即视为异常通过（不要强制依赖业务码为非0）

**重要**：正样例（正常场景）必须明显多于负样例（异常场景），即 5~6 个正常场景 + 1~2 个异常场景，总计 6~8 个场景。

# 可用资源与ID（务必优先使用，避免编造）
{resource_config}
**⚠️ 关键提醒：在生成request_data时，绝对不要包含以下测试元数据字段**：
- expected_status, expected_status_code, expected_code
- response_time, url_path, test_type
- expected_response, status_code, code
这些字段会导致测试失败，请确保request_data中只包含API实际需要的参数和字段。

**提高通过率的关键要点**：
1. **仔细阅读请求参数和请求体信息**：确保理解每个字段的类型、是否必填、约束条件（如minLength、maxLength、enum等）
2. **正确区分参数位置（非常重要）**：
   - **路径参数（path parameters）**：必须包含在request_data中，但会在代码中自动替换到URL路径中
   - **查询参数（query parameters）**：必须包含在request_data中，但会在代码中自动作为URL查询参数发送（如 ?receive_id_type=user_id）
   - **请求体参数（request body）**：必须包含在request_data中，会作为JSON body发送
   - **重要**：不要将查询参数（如receive_id_type）放在请求体中，也不要将请求体参数放在查询参数中
3. **绝对禁止在request_data中包含测试元数据字段（极其重要）**：
   - **以下字段绝对不能出现在request_data的任何位置（包括路径参数、查询参数、请求体）**：
     * expected_status, expected_status_code, expected_code
     * response_time, url_path, test_type
     * expected_response, status_code, code
   - 这些字段是测试框架的元数据，**绝对不能**出现在实际的API请求中
   - 如果这些字段出现在request_data中，会导致测试失败，因为API服务器会拒绝这些未知字段
   - **请仔细检查生成的request_data，确保不包含以上任何字段**
3. **使用正确的数据类型**：
   - 字符串字段使用字符串值（用双引号）
   - 数字字段使用数字值（不用引号）
   - 布尔字段使用 true/false（不用引号）
   - 数组字段使用数组格式 []
   - 对象字段使用对象格式 {{}}
4. **遵循字段约束**：
   - 如果字段有enum限制，必须使用enum中的值
   - 如果字段有minLength/maxLength，确保字符串长度在范围内
   - 如果字段有minimum/maximum，确保数字在范围内
5. **正常场景必须使用有效值**：
   - 不要使用空字符串、null、undefined等无效值
   - 确保所有值都符合字段的类型和约束
   - 如果字段有示例值，优先参考示例值的格式
6. **异常场景要合理**：
   - 缺失必填字段：直接不包含该字段，而不是设置为null或空字符串
   - 类型错误：使用错误的类型（如字符串字段传入数字）
   - 格式错误：使用不符合格式的值（如email字段传入非email格式）

# 返回格式
返回一个JSON数组，每个元素是一个测试用例对象，格式如下：
{{
  "name": "测试用例名称",
  "description": "测试用例描述",
  "test_type": "normal" 或 "exception"（正常场景用"normal"，异常场景用"exception"）,
  "request_data": {{"字段名": "测试值"}},
  "expected_status_code": 200（正常场景）或 400/500（异常场景）,
  "expected_response": {{"code": 0（正常场景）或 错误码（异常场景）, "msg": "success"（正常场景）或 "错误信息"（异常场景）}},
  "tags": ["normal"] 或 ["exception"]
}}

**关于request_data的严格要求（必须严格遵守）**：
- request_data必须只包含API实际需要的参数和字段
- **绝对禁止**在request_data中包含以下任何字段（这些字段会导致测试失败）：
  * expected_status, expected_status_code, expected_code
  * response_time, url_path, test_type
  * expected_response, status_code, code
- 这些字段是测试框架的元数据，**绝对不能**出现在实际的API请求中
- 如果这些字段出现在request_data中，API服务器会拒绝请求，导致测试失败
- request_data应该只包含：路径参数、查询参数、请求体字段（根据API定义）
- **请仔细检查生成的request_data，确保不包含以上任何字段，包括大小写变体**

# 注意事项
1. **必须生成正好4个测试用例**：3个正常场景（test_type="normal"）+ 1个异常场景（test_type="exception"）
2. **状态码和响应码**：
   - 正常场景的expected_status_code必须是200，expected_response中code必须是0，msg应该是"success"或类似的成功消息
   - 异常场景（如缺失必填字段）expected_status_code默认400，expected_response中code默认99992402，msg默认"field validation failed"
3. **请求数据完整性（关键，直接影响测试通过率）**：
   - 每个测试用例的request_data应该包含**所有必需的参数和字段**，但需要正确分类：
   - **路径参数**：如果API路径中有路径参数（如 /api/users/{{user_id}}），必须在request_data中包含该参数
   - **查询参数**：如果API有查询参数（如 receive_id_type、page、limit等），必须在request_data中包含这些参数
   - **请求体参数（最重要）**：如果API有请求体（requestBody），**必须在request_data中包含请求体中的所有必填字段**。**请仔细查看上面的"请求体必填字段列表"，确保每个正常场景测试用例都包含列表中的每一个字段！**
   - **检查清单**：生成每个正常场景测试用例后，请对照"请求体必填字段列表"逐一检查，确保request_data中包含列表中的每一个字段。如果缺少任何一个，必须补充！
   - **重要示例**：
     - 如果 receive_id_type 是查询参数（in="query"），它应该在request_data中，但会作为URL查询参数发送
     - 如果 receive_id 是请求体字段，它应该在request_data中，会作为JSON body的一部分发送
     - 不要混淆：查询参数不会进入请求体，请求体字段不会进入查询参数
   - **禁止在request_data中包含测试元数据字段（极其重要，必须严格遵守）**：
     - **绝对禁止**在request_data中包含以下字段：
       * expected_status, expected_status_code, expected_code
       * response_time, url_path, test_type
       * expected_response, status_code, code
     - 这些字段是测试框架使用的元数据，**绝对不能**出现在实际的API请求中
     - 如果这些字段出现在request_data中，API服务器会拒绝请求，导致测试失败
     - **重要**：request_data应该只包含API实际需要的参数和字段，不要包含任何测试相关的元数据
     - **请仔细检查生成的request_data，确保不包含以上任何字段，包括大小写变体（如ExpectedStatus、EXPECTED_STATUS等）**
     - 如果AI在request_data中包含了这些字段，生成的测试用例将无法正常工作
4. **测试用例命名**：
   - 测试用例名称要清晰描述测试内容
   - 正常场景命名：如"正常场景_完整字段"、"正常场景_最小字段"、"正常场景_典型用例"
   - 异常场景命名：如"异常场景_缺失必填字段data"、"异常场景_类型错误"、"异常场景_格式错误"
5. **JSON格式要求**：
   - 所有字符串值中的双引号必须转义为\\"
   - 不要使用单引号，统一使用双引号
   - 确保JSON格式完全正确，可以直接被json.loads()解析
   - 如果request_data中包含嵌套的JSON字符串，需要正确转义所有引号
   - 示例：如果字段值是JSON字符串，应该写成 "{{\\"key\\": \\"value\\"}}" 而不是 "{{"key": "value"}}"
6. **数据类型要求（非常重要）**：
   - 如果API接口期望某个字段是JSON对象或数组，request_data中应该直接使用JSON对象/数组，而不是JSON字符串
   - 例如：如果form_content字段期望是数组，应该写成 {{"form_content": [{{"id": "field1"}}]}} 而不是 {{"form_content": "[{{\\"id\\": \\"field1\\"}}]"}}
   - 只有在API明确要求字段值为JSON字符串时（如某些API的data字段需要JSON字符串），才使用转义的JSON字符串
   - 判断方法：查看请求体信息中字段的type，如果是"object"或"array"，则直接使用对象/数组；如果是"string"且description中明确说明是JSON字符串，才使用转义的JSON字符串
7. **字段值选择策略**：
   - 优先使用请求示例中的值（如果存在）
   - 如果字段有enum，必须使用enum中的值
   - 如果字段有示例值（example），优先使用示例值
   - 如果字段有默认值（default），可以使用默认值
   - 对于字符串字段，使用有意义的字符串，避免使用"test"、"123"等过于简单的值
   - 对于数字字段，使用合理的数字，避免使用0、1等边界值（除非是边界测试）
8. **提高通过率的额外建议（非常重要）**：
   - **⚠️ 首先检查必填字段**：生成每个正常场景测试用例前，先查看"请求体必填字段列表"，确保request_data中包含列表中的每一个字段
   - **⚠️ 对照检查**：生成测试用例后，对照"请求体必填字段列表"逐一检查，确保没有遗漏任何必填字段
   - **⚠️ 如果字段有enum，必须使用enum中的值**（这是最常见的错误来源）
   - **⚠️ 如果字段是msg_type类型，通常应该使用"text"作为默认值**
   - 仔细检查每个字段的类型和约束，确保值符合要求
   - 如果字段有format（如"email"、"uri"、"date-time"），确保值符合该格式
   - 如果字段有pattern（正则表达式），确保值匹配该pattern
   - 对于嵌套对象，确保所有嵌套字段也符合要求
   - 对于数组字段，确保数组元素符合items的定义

请直接返回JSON数组，不要包含任何其他内容，不要有markdown代码块标记，确保JSON格式完全正确。"""
        
        return prompt
    
    def _resolve_ref(self, schema: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
        """解析 $ref 引用"""
        if not schema or "$ref" not in schema or not components:
            return schema
        ref_path = schema.get("$ref", "")
        # 仅处理本地引用 #/components/schemas/Name
        if ref_path.startswith("#/components/"):
            parts = ref_path.lstrip("#/").split("/")
            cur = components
            for p in parts[1:]:  # 跳过首个 "components"
                cur = cur.get(p, {})
            if cur:
                return cur
        return schema

    def _extract_schema_info(self, schema: Dict[str, Any], prefix: str = "", components: Dict[str, Any] = None) -> Dict[str, Any]:
        """递归提取schema信息，支持$ref解析"""
        info = {}
        
        # 处理 $ref
        schema = self._resolve_ref(schema, components)
        
        schema_type = schema.get("type", "")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        if schema_type == "object" and properties:
            for prop_name, prop_schema in properties.items():
                prop_path = f"{prefix}.{prop_name}" if prefix else prop_name
                prop_info = {
                    "name": prop_path,
                    "type": prop_schema.get("type", ""),
                    "required": prop_name in required,
                    "description": prop_schema.get("description", ""),
                }
                
                # 提取约束信息
                if "minLength" in prop_schema:
                    prop_info["minLength"] = prop_schema["minLength"]
                if "maxLength" in prop_schema:
                    prop_info["maxLength"] = prop_schema["maxLength"]
                if "minimum" in prop_schema:
                    prop_info["minimum"] = prop_schema["minimum"]
                if "maximum" in prop_schema:
                    prop_info["maximum"] = prop_schema["maximum"]
                if "enum" in prop_schema:
                    prop_info["enum"] = prop_schema["enum"]
                if "format" in prop_schema:
                    prop_info["format"] = prop_schema["format"]
                
                # 递归处理嵌套对象
                if prop_schema.get("type") == "object" and "properties" in prop_schema:
                    nested_info = self._extract_schema_info(prop_schema, prop_path, components)
                    info.update(nested_info)
                else:
                    info[prop_path] = prop_info
        
        elif schema_type == "array":
            items = schema.get("items", {})
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            info["array_info"] = {
                "type": "array",
                "minItems": min_items,
                "maxItems": max_items,
                "items": self._extract_schema_info(items, f"{prefix}[items]", components) if items else {}
            }
        
        return info
    
    def _get_required_fields_summary(self, schema: Dict[str, Any], components: Dict[str, Any] = None) -> str:
        """提取并格式化必需字段摘要，支持$ref"""
        if not schema:
            return "无请求体"
        
        schema = self._resolve_ref(schema, components)
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})
        
        if not required_fields:
            return "无必填字段（所有字段都是可选的）"
        
        required_info = []
        for field_name in required_fields:
            field_schema = self._resolve_ref(properties.get(field_name, {}), components)
            field_type = field_schema.get("type", "unknown")
            field_desc = field_schema.get("description", "")
            enum_values = field_schema.get("enum", [])
            
            field_summary = f"- {field_name} (类型: {field_type}"
            if enum_values:
                field_summary += f", 可选值: {enum_values}"
            if field_desc:
                field_summary += f", 说明: {field_desc[:50]}"
            field_summary += ")"
            required_info.append(field_summary)
        
        return "\n".join(required_info)
    
    def _ensure_required_fields(self, request_data: Dict[str, Any], 
                                api_info: Dict[str, Any]) -> Dict[str, Any]:
        """确保正常场景的测试用例包含所有必填字段，如果缺失则自动补充"""
        request_body = api_info.get("request_body", {})
        if not request_body:
            return request_data
        
        # 提取请求体的schema
        content = request_body.get("content", {})
        if "application/json" not in content:
            return request_data
        
        schema = content["application/json"].get("schema", {})
        components = api_info.get("components", {})
        schema = self._resolve_ref(schema, components)
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # 检查并补充缺失的必填字段（即便 required 为空也会做关键字段兜底）
        updated_data = request_data.copy()
        missing_fields = []

        def add_field_if_missing(field_name: str):
            nonlocal updated_data, missing_fields
            if field_name in updated_data:
                return
            field_schema = self._resolve_ref(properties.get(field_name, {}), components)
            field_type = field_schema.get("type", "string")
            enum_values = field_schema.get("enum", [])
            default_value = field_schema.get("default")
            example_value = field_schema.get("example")

            if default_value is not None:
                updated_data[field_name] = default_value
                missing_fields.append(f"{field_name} (使用默认值: {default_value})")
            elif example_value is not None:
                updated_data[field_name] = example_value
                missing_fields.append(f"{field_name} (使用示例值: {example_value})")
            elif enum_values:
                updated_data[field_name] = enum_values[0]
                missing_fields.append(f"{field_name} (使用枚举值: {enum_values[0]})")
            elif field_name == "msg_type":
                # 不再硬编码为 text，优先使用schema提供的枚举/默认/示例
                if enum_values:
                    updated_data[field_name] = enum_values[0]
                    missing_fields.append(f"{field_name} (使用枚举值: {enum_values[0]})")
                elif default_value is not None:
                    updated_data[field_name] = default_value
                    missing_fields.append(f"{field_name} (使用默认值: {default_value})")
                elif example_value is not None:
                    updated_data[field_name] = example_value
                    missing_fields.append(f"{field_name} (使用示例值: {example_value})")
                else:
                    # 无任何提示时，留空提示开发者自行确认
                    updated_data[field_name] = "msg_type_required"
                    missing_fields.append(f"{field_name} (缺少枚举/示例/默认，使用占位符 msg_type_required，请确认)")
            elif field_name == "type":
                # 避免写死 type，按 schema 提示，否则占位
                if enum_values:
                    updated_data[field_name] = enum_values[0]
                    missing_fields.append(f"{field_name} (使用枚举值: {enum_values[0]})")
                elif default_value is not None:
                    updated_data[field_name] = default_value
                    missing_fields.append(f"{field_name} (使用默认值: {default_value})")
                elif example_value is not None:
                    updated_data[field_name] = example_value
                    missing_fields.append(f"{field_name} (使用示例值: {example_value})")
                else:
                    updated_data[field_name] = "type_required"
                    missing_fields.append(f"{field_name} (缺少枚举/示例/默认，使用占位符 type_required，请确认)")
            elif field_name == "content":
                updated_data[field_name] = json.dumps({"text": "auto test message"}, ensure_ascii=False)
                missing_fields.append(f"{field_name} (使用默认文本内容)")
            elif field_type == "string":
                if "id" in field_name.lower():
                    # 使用self.receive_id，如果为None则使用默认值
                    receive_id = self.receive_id or self.user_id or "test_user_id"
                    updated_data[field_name] = receive_id
                    missing_fields.append(f"{field_name} (使用默认ID: {receive_id})")
                else:
                    updated_data[field_name] = f"test_{field_name}"
                    missing_fields.append(f"{field_name} (使用测试值: test_{field_name})")
            elif field_type in ("integer", "number"):
                updated_data[field_name] = 1
                missing_fields.append(f"{field_name} (使用默认数字: 1)")
            elif field_type == "boolean":
                updated_data[field_name] = True
                missing_fields.append(f"{field_name} (使用默认布尔值: True)")
            else:
                updated_data[field_name] = "" if field_type == "string" else {}
                missing_fields.append(f"{field_name} (使用空值)")

        for field_name in required_fields:
            add_field_if_missing(field_name)

        # 对常见关键字段做兜底（即使未标 required）
        for key_field in ("msg_type", "content"):
            if key_field in properties:
                add_field_if_missing(key_field)

        if missing_fields:
            print(f"[INFO] 自动补充缺失的必填字段: {', '.join(missing_fields)}")
        
        return updated_data
    
    def generate_test_cases(self, files_data: Dict[str, Any], api_info: Dict[str, Any]) -> List[TestCase]:
        """使用AI生成测试用例"""
        
        if not self.ai_available or not self.client:
            print("[ERROR] AI客户端不可用，无法生成测试用例")
            return []
        
        print(f"[INFO] 使用AI生成异常值和边界值测试用例...")
        
        # 构建提示词
        prompt = self.build_ai_prompt(api_info, files_data)
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的软件测试工程师，擅长编写API的异常值和边界值测试用例。请严格按照要求返回JSON格式的测试用例数组。"
                },
                {"role": "user", "content": prompt}
            ]
            
            # 调用AI API（带超时控制）
            start_time = time.time()
            print(f"[INFO] 开始调用AI API，超时时间: {self.timeout}秒，最大token: {self.max_tokens}")
            
            try:
                # 关闭thinking模式以加快响应速度
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.5,  # 降低temperature以加快响应
                    max_tokens=self.max_tokens,
                    extra_body={},  # 关闭thinking模式以加快速度
                    stream=True
                )
            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    print(f"[ERROR] AI API调用超时（{self.timeout}秒）")
                else:
                    print(f"[ERROR] AI API调用失败: {e}")
                return []
            
            # 处理流式响应（带超时控制）
            response_content = ""
            is_answering = False
            last_chunk_time = time.time()
            
            print("\n" + "=" * 20 + "AI思考过程" + "=" * 20)
            for chunk in completion:
                # 检查超时
                current_time = time.time()
                if current_time - start_time > self.timeout:
                    print(f"\n[WARN] 响应处理超时（{self.timeout}秒），使用已接收的内容")
                    break
                
                # 更新最后接收时间
                if current_time - last_chunk_time > 30:  # 如果30秒没有新数据，可能超时
                    print(f"\n[WARN] 响应中断（30秒无新数据），使用已接收的内容")
                    break
                
                last_chunk_time = current_time
                
                if not chunk.choices or len(chunk.choices) == 0:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # 处理思考过程
                if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                    if not is_answering:
                        print(delta.reasoning_content, end="", flush=True)
                
                # 处理回复内容
                if hasattr(delta, "content") and delta.content:
                    if not is_answering:
                        print("\n" + "=" * 20 + "AI完整回复" + "=" * 20)
                        is_answering = True
                    print(delta.content, end="", flush=True)
                    response_content += delta.content
            
            response_time = time.time() - start_time
            print(f"\n[OK] AI生成完成，耗时: {response_time:.2f}秒")
            print(f"[INFO] 接收到的响应内容长度: {len(response_content)} 字符")
            
            # 检查响应内容是否完整
            if len(response_content) < 100:
                print(f"[WARN] 响应内容过短，可能不完整")
            elif not response_content.strip().startswith('['):
                print(f"[WARN] 响应内容不是以数组开始，可能格式不正确")
            
            # 解析AI响应
            test_cases = self._parse_ai_response(response_content, api_info)
            
            if test_cases:
                print(f"[OK] 成功生成 {len(test_cases)} 个测试用例")
            else:
                print(f"[WARN] AI未能生成有效测试用例")
            
            return test_cases
            
        except Exception as e:
            print(f"[ERROR] AI生成失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    def sanitize_request_data_recursive(self, data: Any, metadata_fields: Optional[set] = None) -> Any:
        """
        递归清理 request_data，删除任何层级中与测试元数据相关的字段（键名匹配大小写/近似/包含）。
        - 支持 dict、list、tuple、基本类型
        - 返回清理后的新对象（不就地修改原数据以避免副作用）
        """
        if metadata_fields is None:
            metadata_fields = {
                "expected_status", "expected_status_code", "expected_code",
                "response_time", "url_path", "test_type",
                "expected_response",  
                "status_code", "code"
            }
        # 预计算小写集用于快速比较
        metadata_lower = {f.lower() for f in metadata_fields}

        # 辅助：判断键是否是元数据（大小写不敏感、或包含关键词且长度相近）
        safe_keys = {"msg_type", "message_type"}
        def is_metadata_key(k: str) -> bool:
            if not isinstance(k, str):
                return False
            kl = k.lower()
            if kl in safe_keys:
                return False
            if kl in metadata_lower:
                return True
            # 包含关键词（防止变体），并且长度相近（避免误杀太长的业务字段）
            for mf in metadata_lower:
                if mf in kl or kl in mf:
                    if abs(len(kl) - len(mf)) <= 5 and kl not in safe_keys:
                        return True
            return False

        # 递归处理
        if isinstance(data, dict):
            new_obj = {}
            for k, v in data.items():
                if is_metadata_key(k):
                    # 跳过该键并记录（可选：打印debug）
                    # print(f"[DEBUG] 移除测试元数据字段: {k}")
                    continue
                # 递归清理值
                clean_v = self.sanitize_request_data_recursive(v, metadata_fields)
                # 如果值本身是空 dict/list/null，可视情况保留或忽略；这里保留但允许空
                new_obj[k] = clean_v
            return new_obj
        elif isinstance(data, (list, tuple)):
            new_list = []
            for item in data:
                new_item = self.sanitize_request_data_recursive(item, metadata_fields)
                new_list.append(new_item)
            return new_list
        else:
            # 基本类型直接返回
            return data
    
    def _parse_ai_response(self, response_content: str, api_info: Dict[str, Any]) -> List[TestCase]:
        """解析AI响应"""
        
        try:
            # 清理响应内容，提取JSON部分
            cleaned_content = response_content.strip()
            
            # 移除可能的Markdown代码块标记
            if cleaned_content.startswith("```"):
                lines = cleaned_content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_content = "\n".join(lines)
            
            # 尝试找到JSON数组的开始和结束位置（通过括号匹配）
            bracket_count = 0
            json_start = -1
            json_end = -1
            in_string = False
            escape_next = False
            
            for i, char in enumerate(cleaned_content):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '[':
                        if bracket_count == 0:
                            json_start = i
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0 and json_start != -1:
                            json_end = i + 1
                            break
            
            if json_start != -1 and json_end != -1:
                cleaned_content = cleaned_content[json_start:json_end]
            
            # 尝试解析JSON
            test_cases_data = json.loads(cleaned_content)
            
            if not isinstance(test_cases_data, list):
                print(f"[ERROR] AI响应不是数组格式")
                return []
            
            test_cases = []
            operation_id = api_info.get("operation_id", "api").lower()
            
            for i, case_data in enumerate(test_cases_data):
                # 验证必要字段
                if not all(k in case_data for k in ["name", "request_data", "expected_status_code", "test_type"]):
                    print(f"[WARN] 测试用例 {i} 缺少必要字段，跳过")
                    continue
                
                # 生成测试用例名称
                test_type = case_data.get("test_type", "exception")
                if test_type == "normal":
                    test_case_name = f"test_{operation_id}_normal_{i+1}"
                else:
                    test_case_name = f"test_{operation_id}_exception_{i+1}"
                
                # 判断是否为成功场景
                is_success = test_type == "normal" or case_data.get("expected_status_code", 400) == 200
                
                # 清理request_data，移除测试元数据字段
                request_data = case_data.get("request_data", {})
                # 定义所有不应该出现在request_data中的测试元数据字段
                test_metadata_fields = {
                    "expected_status", "expected_status_code", "expected_code", 
                    "response_time", "url_path", "test_type", "is_success",
                    "expected_response", "tags", "name", "description",
                    "status_code", "code", "msg", "message",
                    "performance", "_performance", "duration", "time"
                }
                # 创建大小写不敏感的黑名单
                test_metadata_fields_lower = {f.lower() for f in test_metadata_fields}
                # 严格过滤：精确匹配 + 大小写不敏感匹配
                cleaned_request_data = {}
                for k, v in request_data.items():
                    # 跳过精确匹配
                    if k in test_metadata_fields:
                        continue
                    # 跳过大小写不敏感匹配
                    if k.lower() in test_metadata_fields_lower:
                        continue
                    # 跳过包含测试元数据关键词的字段（防止变体）
                    key_lower = k.lower()
                    should_skip = False
                    for field in test_metadata_fields:
                        field_lower = field.lower()
                        # 如果字段名包含测试元数据关键词，且长度相近，则跳过
                        if (field_lower in key_lower or key_lower in field_lower) and abs(len(key_lower) - len(field_lower)) <= 5:
                            should_skip = True
                            break
                    if not should_skip:
                        cleaned_request_data[k] = v
                
                # 对于正常场景，检查并自动补充缺失的必填字段
                if test_type == "normal":
                    cleaned_request_data = self._ensure_required_fields(
                        cleaned_request_data, api_info
                    )
                
                # 针对异常场景默认业务码/状态码兜底（字段缺失常见返回 99992402）
                expected_response = case_data.get("expected_response", {})
                expected_status_code = case_data.get("expected_status_code", 400 if test_type == "exception" else 200)
                if test_type == "exception":
                    expected_response = expected_response or {}
                    if "code" not in expected_response:
                        expected_response["code"] = 99992402
                    if "msg" not in expected_response:
                        expected_response["msg"] = "field validation failed"
                    # HTTP 状态码若未提供，默认 400
                    expected_status_code = expected_status_code or 400
                
                test_case = TestCase(
                    name=case_data.get("name", f"测试用例 {i+1}"),
                    description=case_data.get("description", ""),
                    test_type=test_type,
                    request_data=cleaned_request_data,  # 使用清理后的数据
                    expected_status_code=expected_status_code,
                    expected_response=expected_response,
                    test_case_name=test_case_name,
                    tags=case_data.get("tags", []),
                    is_success=is_success
                )
                test_cases.append(test_case)
            
            return test_cases
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] 解析AI响应JSON失败: {e}")
            error_pos = getattr(e, 'pos', None)
            if error_pos:
                print(f"错误位置: 字符位置 {error_pos}")
                if 'cleaned_content' in locals() and error_pos < len(cleaned_content):
                    start = max(0, error_pos - 50)
                    end = min(len(cleaned_content), error_pos + 50)
                    print(f"错误位置附近内容: ...{cleaned_content[start:end]}...")
            print(f"响应内容前500字符: {response_content[:500]}")
            if 'cleaned_content' in locals():
                print(f"清理后内容前500字符: {cleaned_content[:500]}")
            
            # 尝试提取可能的JSON片段
            try:
                # 方法1: 尝试找到所有可能的JSON对象
                import re
                # 更精确的JSON对象匹配（考虑嵌套和字符串）
                json_objects = []
                depth = 0
                start = -1
                in_string = False
                escape_next = False
                
                for i, char in enumerate(response_content):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            if depth == 0:
                                start = i
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0 and start != -1:
                                json_obj_str = response_content[start:i+1]
                                try:
                                    json_obj = json.loads(json_obj_str)
                                    json_objects.append(json_obj)
                                except:
                                    pass
                                start = -1
                
                if json_objects:
                    print(f"[INFO] 找到 {len(json_objects)} 个可能的JSON对象，尝试解析...")
                    # 验证并处理这些对象
                    test_cases = []
                    operation_id = api_info.get("operation_id", "api").lower()
                    
                    for i, case_data in enumerate(json_objects[:4]):  # 最多取4个
                        # 验证必要字段
                        if not isinstance(case_data, dict):
                            continue
                        if not all(k in case_data for k in ["name", "request_data", "expected_status_code", "test_type"]):
                            print(f"[WARN] JSON对象 {i} 缺少必要字段，跳过")
                            continue
                        
                        # 生成测试用例名称
                        test_type = case_data.get("test_type", "exception")
                        if test_type == "normal":
                            test_case_name = f"test_{operation_id}_normal_{i+1}"
                        else:
                            test_case_name = f"test_{operation_id}_exception_{i+1}"
                        
                        # 判断是否为成功场景
                        is_success = test_type == "normal" or case_data.get("expected_status_code", 400) == 200
                        
                        # 清理request_data，移除测试元数据字段
                        request_data = case_data.get("request_data", {})
                        # 定义所有不应该出现在request_data中的测试元数据字段
                        test_metadata_fields = {
                            "expected_status", "expected_status_code", "expected_code", 
                            "response_time", "url_path", "test_type", "is_success",
                            "expected_response", "tags", "name", "description",
                            "status_code", "code", "msg", "message",
                            "performance", "_performance", "duration", "time"
                        }
                        # 创建大小写不敏感的黑名单
                        test_metadata_fields_lower = {f.lower() for f in test_metadata_fields}
                        # 严格过滤：精确匹配 + 大小写不敏感匹配
                        cleaned_request_data = {}
                        for k, v in request_data.items():
                            # 跳过精确匹配
                            if k in test_metadata_fields:
                                continue
                            # 跳过大小写不敏感匹配
                            if k.lower() in test_metadata_fields_lower:
                                continue
                            # 跳过包含测试元数据关键词的字段（防止变体）
                            key_lower = k.lower()
                            should_skip = False
                            for field in test_metadata_fields:
                                field_lower = field.lower()
                                # 如果字段名包含测试元数据关键词，且长度相近，则跳过
                                if (field_lower in key_lower or key_lower in field_lower) and abs(len(key_lower) - len(field_lower)) <= 5:
                                    should_skip = True
                                    break
                            if not should_skip:
                                cleaned_request_data[k] = v
                        
                        test_case = TestCase(
                            name=case_data.get("name", f"测试用例 {i+1}"),
                            description=case_data.get("description", ""),
                            test_type=test_type,
                            request_data=cleaned_request_data,  # 使用清理后的数据
                            expected_status_code=case_data.get("expected_status_code", 400 if test_type == "exception" else 200),
                            expected_response=case_data.get("expected_response", {}),
                            test_case_name=test_case_name,
                            tags=case_data.get("tags", []),
                            is_success=is_success
                        )
                        test_cases.append(test_case)
                    
                    if test_cases:
                        print(f"[OK] 成功从片段中解析出 {len(test_cases)} 个测试用例")
                        return test_cases
                    else:
                        print(f"[WARN] 从片段中解析出的JSON对象都不完整，无法生成测试用例")
            except Exception as fallback_err:
                print(f"[WARN] 备用解析方法也失败: {fallback_err}")
            
            return []
        except Exception as e:
            print(f"[ERROR] 处理AI响应失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def generate_pytest_file(self, api_info: Dict[str, Any], test_cases: List[TestCase],
                            output_dir: str = "test_code", base_name: str = None, 
                            base_dir: str = "uploads", skip_if_exists: bool = True) -> str:
        """生成pytest测试文件"""
        
        # 生成类名
        operation_id = api_info.get("operation_id", "Api")
        class_name = "Test" + ''.join(word.capitalize() for word in re.split(r'[^a-zA-Z0-9]', operation_id))
        
        # 生成文件名：优先使用base_name，如果没有则使用operation_id
        if base_name:
            # 清理base_name，移除特殊字符，只保留字母、数字、下划线和连字符
            sanitized_base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', base_name)
            file_name = f"test_{sanitized_base_name}_normal_exception.py"
        else:
            file_name = f"test_{operation_id.lower()}_normal_exception.py"
        
        # 构建完整输出路径，包含base_dir
        full_output_dir = Path(base_dir) / output_dir
        file_path = full_output_dir / file_name
        
        # 检查文件是否已存在
        if skip_if_exists and file_path.exists():
            print(f"[INFO] 测试文件已存在，跳过生成: {file_path}")
            return str(file_path)
        
        # 如果文件已存在且skip_if_exists为False，添加时间戳避免覆盖
        if file_path.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_stem = file_path.stem
            file_suffix = file_path.suffix
            file_path = file_path.parent / f"{file_stem}_{timestamp}{file_suffix}"
            print(f"[INFO] 文件已存在，使用新文件名: {file_path.name}")
        
        # 确保目录存在
        full_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建测试文件内容
        test_content = self._build_test_file_content(api_info, test_cases, class_name)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"[OK] 生成测试文件: {file_path}")
        return str(file_path)

    def generate_yaml_cases(self, api_info: Dict[str, Any], test_cases: List[TestCase],
                            output_dir: str = "tests_yaml", base_name: str = None, base_dir: str = "uploads") -> str:
        """生成 YAML 测试用例文件（不生成pytest代码）"""
        operation_id = api_info.get("operation_id", "api")
        file_stem = base_name or operation_id
        file_name = f"cases_{file_stem}.yaml"
        base_path = Path(base_dir)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_path / out_dir / file_name
        
        # 确保文件的完整路径目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 仅保留核心字段，便于后续自定义运行
        data = []
        for tc in test_cases:
            data.append({
                "name": tc.name,
                "description": tc.description,
                "test_type": tc.test_type,
                "request_data": tc.request_data,
                "expected_status_code": tc.expected_status_code,
                "expected_response": tc.expected_response,
                "tags": tc.tags,
            })

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

        print(f"[OK] 生成YAML测试用例: {file_path}")
        return str(file_path)

    def convert_yaml_to_pytest(self, base_name: str, yaml_path: str,
                               base_dir: str = "uploads", output_dir: str = "tests",
                               skip_if_exists: bool = True) -> Dict[str, Any]:
        """
        将已生成的 YAML 用例转换为 pytest 测试文件，不调用大模型。
        步骤：
        1. 读取 YAML 用例
        2. 依据 base_name 重新解析 openapi 信息，保证路径/方法等元数据完整
        3. 将 YAML 中的用例转为 TestCase 对象
        4. 使用现有的 generate_pytest_file 生成 .py 文件
        """
        yaml_file = Path(yaml_path)
        if not yaml_file.exists():
            return {"error": f"YAML用例文件不存在: {yaml_file}"}

        # 复用已有文件解析逻辑，确保无需调用AI
        files_data = self.load_files(base_name, base_dir)
        api_info = self.extract_api_info(files_data)
        if not api_info.get("path"):
            return {"error": "未能提取到API路径信息，请检查base_name或openapi文件是否存在"}

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                cases_data = yaml.safe_load(f) or []
        except Exception as e:
            return {"error": f"读取YAML用例失败: {e}"}

        if not isinstance(cases_data, list):
            return {"error": "YAML文件内容格式不正确，应为用例数组"}

        test_cases: List[TestCase] = []
        operation_id = api_info.get("operation_id", "api").lower()

        for idx, item in enumerate(cases_data):
            if not isinstance(item, dict):
                print(f"[WARN] 第 {idx+1} 条记录不是对象，已跳过")
                continue

            test_type = item.get("test_type", "exception")
            is_success = test_type == "normal"
            request_data = item.get("request_data", {}) or {}

            # 彻底清理测试元数据字段，防止污染请求
            request_data = self.sanitize_request_data_recursive(request_data)
            if is_success:
                # 对正常场景补齐必填字段
                request_data = self._ensure_required_fields(request_data, api_info)

            test_case_name = f"test_{operation_id}_{'normal' if is_success else 'exception'}_{idx+1}"

            tc = TestCase(
                name=item.get("name", f"用例{idx+1}"),
                description=item.get("description", ""),
                test_type=test_type,
                request_data=request_data,
                expected_status_code=item.get("expected_status_code", 200 if is_success else 400),
                expected_response=item.get("expected_response", {}) or {},
                test_case_name=test_case_name,
                tags=item.get("tags", []) or [],
                is_success=is_success
            )
            test_cases.append(tc)

        if not test_cases:
            return {"error": "YAML文件中未找到有效的测试用例"}

        test_file = self.generate_pytest_file(api_info, test_cases, output_dir, base_name=base_name, base_dir=base_dir, skip_if_exists=skip_if_exists)
        
        print(f"[OK] 已生成pytest文件: {test_file}")

        return {
            "base_name": base_name,
            "api_path": api_info["path"],
            "operation_id": api_info["operation_id"],
            "total_test_cases": len(test_cases),
            "generated_file": test_file,
            "source_yaml": str(yaml_file)
        }
    
    def _build_test_file_content(self, api_info: Dict[str, Any], test_cases: List[TestCase],
                                 class_name: str) -> str:
        """构建测试文件内容"""
        
        # 导入部分
        imports = """import pytest
import requests
import json
import os
import time
from typing import Dict, Any

"""
        
        # 类定义
        path = api_info.get("path", "")
        method = api_info.get("method", "").upper()
        summary = api_info.get("summary", "")
        
        class_def = f'''class {class_name}:
    """{summary} - 异常值和边界值测试类
    
    API路径: {path}
    方法: {method}
    """
    
    # 基础URL
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    # API路径
    API_PATH = "{path}"
    
    # 接收者ID配置（供测试用例使用）
    DEFAULT_RECEIVE_ID_TYPE = "{self.receive_id_type}"
    DEFAULT_RECEIVE_ID = "{self.receive_id}"
    RECEIVE_ID_MAP = {json.dumps(self.receive_id_map, ensure_ascii=False)}
    
    # 测试指标统计
    test_metrics = {{
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "total_response_time": 0.0,
        "min_response_time": float("inf"),
        "max_response_time": 0.0,
        "success_rate": 0.0,
        "avg_response_time": 0.0
    }}
    
    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        cls.app_id = "{self.app_id}"  # 硬编码的App ID（不再从环境变量读取）
        cls.app_secret = "{self.app_secret}"  # 硬编码的App Secret（不再从环境变量读取）
        cls.token = cls._get_tenant_access_token()
        # 初始化测试指标
        cls.test_metrics = {{
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "total_response_time": 0.0,
            "min_response_time": float("inf"),
            "max_response_time": 0.0,
            "success_rate": 0.0,
            "avg_response_time": 0.0
        }}
    
    @classmethod
    def teardown_class(cls):
        """测试类清理，输出测试指标"""
        metrics = cls.test_metrics
        if metrics["total_tests"] > 0:
            metrics["success_rate"] = (metrics["passed_tests"] / metrics["total_tests"]) * 100
            metrics["avg_response_time"] = metrics["total_response_time"] / metrics["total_tests"]
            if metrics["min_response_time"] == float("inf"):
                metrics["min_response_time"] = 0.0
        
        print("\\n" + "=" * 60)
        print("测试评价指标汇总")
        print("=" * 60)
        print(f"总测试用例数: {{metrics['total_tests']}}")
        print(f"通过用例数: {{metrics['passed_tests']}}")
        print(f"失败用例数: {{metrics['failed_tests']}}")
        print(f"成功率: {{metrics['success_rate']:.2f}}%")
        print(f"平均响应时间: {{metrics['avg_response_time']:.3f}}秒")
        print(f"最小响应时间: {{metrics['min_response_time']:.3f}}秒")
        print(f"最大响应时间: {{metrics['max_response_time']:.3f}}秒")
        print("=" * 60)
    
    @classmethod
    def _get_tenant_access_token(cls) -> str:
        """获取tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {{"Content-Type": "application/json; charset=utf-8"}}
        payload = {{"app_id": cls.app_id, "app_secret": cls.app_secret}}
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") == 0:
                return data.get("tenant_access_token")
            else:
                raise Exception(f"获取token失败: {{data.get('code')}} - {{data.get('msg')}}")
                
        except Exception as e:
            raise Exception(f"获取token出错: {{e}}")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {{
            "Authorization": f"Bearer {{self.token}}",
            "Content-Type": "application/json"
        }}
    
    def _get_full_url(self, url_path: str = None) -> str:
        """获取完整URL"""
        path = url_path if url_path is not None else self.API_PATH
        return f"{{self.BASE_URL}}{{path}}"
    
    def _send_request(self, data: Dict[str, Any] = None, params: Dict[str, Any] = None, 
                     expected_status: int = None, url_path: str = None) -> Dict[str, Any]:
        """发送请求并验证响应"""
        url = self._get_full_url(url_path=url_path)
        headers = self._get_headers()
        
        start_time = time.time()
        
        # 根据方法选择请求函数
        method = "{method}".lower()
        if method == "post":
            response = requests.post(url, json=data, params=params, headers=headers)
        elif method == "get":
            response = requests.get(url, params=params or data, headers=headers)
        elif method == "put":
            response = requests.put(url, json=data, params=params, headers=headers)
        elif method == "delete":
            response = requests.delete(url, json=data, params=params, headers=headers)
        else:
            response = requests.post(url, json=data, params=params, headers=headers)
        
        response_time = time.time() - start_time
        
        # 验证状态码（如果状态码不符，先打印响应内容再断言，便于调试）
        if expected_status is not None:
            if response.status_code != expected_status:
                try:
                    error_response = response.json()
                    print(f"\\n[DEBUG] 状态码不符，响应内容: {{json.dumps(error_response, ensure_ascii=False, indent=2)}}")
                except:
                    print(f"\\n[DEBUG] 状态码不符，响应文本: {{response.text[:500]}}")
            assert response.status_code == expected_status, \\
                f"状态码不符: 期望{{expected_status}}，实际{{response.status_code}}"
        
        # 解析响应
        try:
            response_data = response.json()
        except:
            response_data = {{"raw_response": response.text}}
        
        # 添加性能数据
        response_data["_performance"] = {{
            "response_time": response_time,
            "status_code": response.status_code
        }}
        
        # 更新测试指标
        self._update_test_metrics(response_time, response.status_code, response_data.get("code", -1))
        
        return response_data
    
    def _update_test_metrics(self, response_time: float, status_code: int, business_code: int):
        """更新测试指标"""
        metrics = self.test_metrics
        metrics["total_tests"] += 1
        
        # 判断测试是否通过（正常场景code=0，异常场景code!=0）
        # 这里简化处理，实际应该根据test_type判断
        if status_code == 200 and business_code == 0:
            metrics["passed_tests"] += 1
        elif status_code >= 400:
            metrics["failed_tests"] += 1
        else:
            # 根据业务码判断
            if business_code == 0:
                metrics["passed_tests"] += 1
            else:
                metrics["failed_tests"] += 1
        
        # 更新响应时间统计
        metrics["total_response_time"] += response_time
        if response_time < metrics["min_response_time"]:
            metrics["min_response_time"] = response_time
        if response_time > metrics["max_response_time"]:
            metrics["max_response_time"] = response_time
'''
        
        # 测试方法
        test_methods = []
        for test_case in test_cases:
            test_method = self._build_test_method(test_case, api_info)
            test_methods.append(test_method)
        
        # 组合所有部分
        test_file = imports + class_def + "\n\n".join(test_methods)
        return test_file
    
    def _build_test_method(self, test_case: TestCase, api_info: Dict[str, Any] = None) -> str:
        """构建单个测试方法"""
        
        # 构建装饰器
        decorators = []
        if test_case.test_type == "normal":
            decorators.append("@pytest.mark.normal")
        elif test_case.test_type == "exception":
            decorators.append("@pytest.mark.exception")
            decorators.append("@pytest.mark.xfail")  # 预期失败的测试
        
        decorator_str = "\n    ".join(decorators) + "\n    " if decorators else ""
        
        # 分离路径参数、查询参数、请求头参数和请求体参数
        parameters = api_info.get("parameters", []) if api_info else []
        request_body = api_info.get("request_body", {}) if api_info else {}
        
        # 获取参数名称映射（按in类型分类）
        path_param_names = {p.get("name") for p in parameters if p.get("in") == "path"}
        query_param_names = {p.get("name") for p in parameters if p.get("in") == "query"}
        header_param_names = {p.get("name") for p in parameters if p.get("in") == "header"}
        
        # 检查请求体是否有字段
        has_request_body = bool(request_body)
        request_body_fields = set()
        if has_request_body:
            # 从请求体中提取字段名（递归提取）
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if "properties" in schema:
                    request_body_fields = set(schema["properties"].keys())
        
        # 分离参数
        # 定义不应该出现在请求中的测试元数据字段（黑名单）
        test_metadata_fields = {
            "expected_status", "expected_status_code", "expected_code", 
            "response_time", "url_path", "test_type", "is_success",
            "expected_response", "tags", "name", "description",
            "status_code", "code", "msg", "message",
            "performance", "_performance", "duration", "time"
        }
        test_metadata_fields_lower = {f.lower() for f in test_metadata_fields}
        safe_keys = {"msg_type", "message_type"}
        
        path_params = {}
        query_params = {}
        header_params = {}
        body_data = {}
        
        # 首先，从test_case.request_data中过滤掉所有测试元数据字段
        # 注意：test_case.request_data在解析时已经清理过，但这里再次确保
        filtered_request_data = {}
        for key, value in test_case.request_data.items():
            # 精确匹配
            if key in test_metadata_fields and key not in safe_keys:
                continue
            # 大小写不敏感匹配
            if key.lower() in test_metadata_fields_lower and key.lower() not in safe_keys:
                continue
            # 关键词匹配（防止变体）
            key_lower = key.lower()
            is_metadata = False
            for field in test_metadata_fields:
                field_lower = field.lower()
                if key_lower in safe_keys:
                    continue
                if (field_lower in key_lower or key_lower in field_lower) and abs(len(key_lower) - len(field_lower)) <= 5:
                    is_metadata = True
                    break
            if not is_metadata:
                filtered_request_data[key] = value
        
        # 现在使用过滤后的数据来分离参数
        # 优先级：路径参数 > 查询参数 > 请求头参数 > 请求体参数
        for key, value in filtered_request_data.items():
            if key in path_param_names:
                # 路径参数：替换到URL路径中（如 /api/users/{user_id}）
                path_params[key] = value
            elif key in query_param_names:
                # 查询参数：放在URL查询字符串中（如 ?receive_id_type=user_id&page=1）
                query_params[key] = value
            elif key in header_param_names:
                # 请求头参数：放在HTTP请求头中（如 Authorization、Content-Type等）
                header_params[key] = value
            elif has_request_body and key in request_body_fields:
                # 请求体参数：放在HTTP请求体中（JSON格式，用于POST/PUT/PATCH等）
                body_data[key] = value
            else:
                # 默认处理：根据HTTP方法和API定义判断
                method = api_info.get("method", "").upper() if api_info else "POST"
                if method == "GET":
                    # GET请求：默认放入查询参数
                    query_params[key] = value
                elif has_request_body:
                    # POST/PUT/PATCH且有requestBody：如果字段不在已知的请求体字段中，可能是请求体字段但未在properties中列出
                    # 尝试放入请求体（某些API可能使用additionalProperties）
                    body_data[key] = value
                else:
                    # POST/PUT/PATCH但没有requestBody：放入查询参数
                    query_params[key] = value
        
        # 最终安全检查：确保测试元数据字段不会出现在任何请求数据中
        # 强制移除所有测试元数据字段（包括大小写变体）
        for field in test_metadata_fields:
            # 精确匹配移除
            if field in body_data:
                del body_data[field]
            if field in query_params:
                del query_params[field]
            if field in header_params:
                del header_params[field]
            if field in path_params:
                del path_params[field]
        
        # 大小写不敏感移除
        for field_lower in test_metadata_fields_lower:
            for key in list(body_data.keys()):
                if key.lower() == field_lower and key.lower() not in safe_keys:
                    del body_data[key]
            for key in list(query_params.keys()):
                if key.lower() == field_lower and key.lower() not in safe_keys:
                    del query_params[key]
            for key in list(header_params.keys()):
                if key.lower() == field_lower and key.lower() not in safe_keys:
                    del header_params[key]
            for key in list(path_params.keys()):
                if key.lower() == field_lower and key.lower() not in safe_keys:
                    del path_params[key]
        
        # 构建路径参数替换代码（如果有路径参数）
        path_param_code = ""
        if path_params:
            # 需要替换URL中的路径参数
            api_path = api_info.get("path", "") if api_info else ""
            path_param_replacements = []
            for param_name, param_value in path_params.items():
                # 转义值以确保安全
                escaped_value = json.dumps(str(param_value), ensure_ascii=False)
                path_param_replacements.append(f'api_path = api_path.replace("{{{{{param_name}}}}}", {escaped_value})')
            if path_param_replacements:
                path_param_code = "\n        ".join(path_param_replacements) + "\n        "
        
        # 构建请求数据代码
        # 在生成JSON字符串之前，最后一次强制清理，确保绝对不包含测试元数据字段
        # 创建新的字典，只包含非元数据字段
        body_data_clean = {}
        for k, v in body_data.items():
            # 再次检查：精确匹配
            if k in test_metadata_fields and k not in safe_keys:
                continue
            # 再次检查：大小写不敏感匹配
            if k.lower() in test_metadata_fields_lower and k.lower() not in safe_keys:
                continue
            # 再次检查：关键词匹配
            key_lower = k.lower()
            is_metadata = False
            for field in test_metadata_fields:
                field_lower = field.lower()
                if key_lower in safe_keys:
                    continue
                if (field_lower in key_lower or key_lower in field_lower) and abs(len(key_lower) - len(field_lower)) <= 5:
                    is_metadata = True
                    break
            if not is_metadata:
                body_data_clean[k] = v
        
        query_params_clean = {}
        for k, v in query_params.items():
            if k in test_metadata_fields and k not in safe_keys:
                continue
            if k.lower() in test_metadata_fields_lower and k.lower() not in safe_keys:
                continue
            key_lower = k.lower()
            is_metadata = False
            for field in test_metadata_fields:
                field_lower = field.lower()
                if key_lower in safe_keys:
                    continue
                if (field_lower in key_lower or key_lower in field_lower) and abs(len(key_lower) - len(field_lower)) <= 5:
                    is_metadata = True
                    break
            if not is_metadata:
                query_params_clean[k] = v
        
        # 在所有清理步骤之后，检查必需的查询参数是否缺失，如果缺失且是receive_id_type，自动添加
        # 这个步骤必须在所有清理之后执行，确保添加的参数不会被移除
        if query_param_names:
            for param_name in query_param_names:
                if param_name not in query_params_clean:
                    # 检查这个参数是否是必需的
                    param_def = next((p for p in parameters if p.get("name") == param_name and p.get("in") == "query"), None)
                    if param_def and param_def.get("required", False):
                        # 如果是receive_id_type且是必需的，使用默认值
                        if param_name == "receive_id_type":
                            query_params_clean[param_name] = self.receive_id_type
                            print(f"[INFO] 自动添加必需的查询参数 {param_name}={self.receive_id_type}")
                        else:
                            # 对于其他必需的查询参数，也尝试添加默认值（如果有的话）
                            default_value = param_def.get("schema", {}).get("default")
                            if default_value is not None:
                                query_params_clean[param_name] = default_value
                                print(f"[INFO] 自动添加必需的查询参数 {param_name}={default_value}（使用默认值）")
                            else:
                                print(f"[WARN] API定义了必需的查询参数 {param_name}，但测试用例中没有包含，可能导致测试失败")
        
        # 生成JSON字符串
        # 注意：即使字典为空，也序列化为{}，这样代码更清晰
        # 直接序列化，不管是否为空（空字典会序列化为{}）
        query_params_str = json.dumps(query_params_clean, ensure_ascii=False, indent=12)
        body_data_str = json.dumps(body_data_clean, ensure_ascii=False, indent=12)
        
        # 最终验证：检查生成的JSON字符串中是否包含测试元数据字段名
        # 如果包含，说明过滤失败，需要强制修复
        for field in test_metadata_fields:
            # 检查body_data_str中是否包含该字段（作为JSON键）
            field_patterns = [f'"{field}"', f'"{field.lower()}"']
            for pattern in field_patterns:
                if pattern in body_data_str:
                    # 强制修复：重新解析JSON，移除该字段，再重新生成
                    try:
                        body_data_dict = json.loads(body_data_str)
                        body_data_dict = {k: v for k, v in body_data_dict.items() 
                                         if k != field and k.lower() != field.lower()}
                        body_data_str = json.dumps(body_data_dict, ensure_ascii=False, indent=12) if body_data_dict else "None"
                    except:
                        # 如果解析失败，使用字符串替换（最后手段）
                        body_data_str = re.sub(rf'"{re.escape(field)}"\s*:\s*[^,}}]+[,}}]?', '', body_data_str)
                        body_data_str = re.sub(rf'"{re.escape(field.lower())}"\s*:\s*[^,}}]+[,}}]?', '', body_data_str)
                    break
            
            # 检查query_params_str中是否包含该字段
            for pattern in field_patterns:
                if pattern in query_params_str:
                    try:
                        query_params_dict = json.loads(query_params_str)
                        query_params_dict = {k: v for k, v in query_params_dict.items() 
                                           if k != field and k.lower() != field.lower()}
                        query_params_str = json.dumps(query_params_dict, ensure_ascii=False, indent=12) if query_params_dict else "None"
                    except:
                        import re
                        query_params_str = re.sub(rf'"{re.escape(field)}"\s*:\s*[^,}}]+[,}}]?', '', query_params_str)
                        query_params_str = re.sub(rf'"{re.escape(field.lower())}"\s*:\s*[^,}}]+[,}}]?', '', query_params_str)
                    break
        
        # 如果有路径参数，需要构建URL替换逻辑
        url_code = ""
        url_path_param = ""
        if path_params:
            # 构建路径参数替换（OpenAPI路径参数格式是 {param_name}）
            path_replacements = []
            for param_name, param_value in path_params.items():
                # 转义值以确保安全
                value_str = json.dumps(str(param_value), ensure_ascii=False)
                # OpenAPI路径参数格式: {param_name}，需要替换为实际值
                path_replacements.append(f'url_path = url_path.replace("{{{{{param_name}}}}}", {value_str})')
            if path_replacements:
                url_code = f'''        # 处理路径参数（替换URL中的 {{param_name}} 格式）
        url_path = self.API_PATH
        {"        ".join(path_replacements)}
        
        '''
                url_path_param = "url_path=url_path,"
        
        test_method = f'''    {decorator_str}def {test_case.test_case_name}(self):
        """{test_case.name}
        
        {test_case.description}
        测试类型: {test_case.test_type}
        """
        
        # 准备请求数据
        {url_code}# 查询参数（URL查询字符串，如 ?receive_id_type=user_id）
        query_params = {query_params_str}
        
        # 请求体数据（JSON body，POST/PUT/PATCH请求使用）
        body_data = {body_data_str}
        
        # 发送请求
        response_data = self._send_request(
            data=body_data if body_data else None,
            params=query_params if query_params else None,
            expected_status={test_case.expected_status_code}{", " + url_path_param if url_path_param else ""}
        )
        
        # 验证响应
        if {test_case.is_success}:
            # 正常场景验证
            assert response_data.get("code") == 0, f"正常测试应该返回成功码0，实际: {{response_data}}"
            # 验证预期字段
{self._generate_success_assertions(test_case)}
        else:
            # 异常场景验证
            # 只要HTTP状态码不是200即可视为通过（负样例）
            assert status_code != 200, f"异常测试期望HTTP状态码非200，实际: {{status_code}}，响应: {{response_data}}"
            # 验证预期错误信息（如提供）
{self._generate_error_assertions(test_case)}
        
        # 打印测试信息和评价指标
        perf = response_data.get('_performance', {{}})
        status_code = perf.get('status_code', 'N/A')
        response_time = perf.get('response_time', 0)
        business_code = response_data.get('code', 'N/A')
        msg = response_data.get('msg', 'N/A')
        
        # 判断测试结果
        test_result = "通过" if ({test_case.is_success} and business_code == 0) or (not {test_case.is_success} and status_code != 200) else "失败"
        
        print(f"\\n场景: {test_case.name}")
        print(f"测试结果: {{test_result}}")
        print(f"HTTP状态码: {{status_code}}")
        print(f"业务码: {{business_code}}")
        print(f"响应时间: {{response_time:.3f}}秒")
        print(f"消息: {{msg}}")'''
        
        return test_method
    
    def _generate_success_assertions(self, test_case: TestCase) -> str:
        """生成成功场景的断言"""
        assertions = []
        
        expected_response = test_case.expected_response
        if expected_response:
            for key, expected_value in expected_response.items():
                if key.startswith("_"):  # 跳过性能数据等内部字段
                    continue
                
                if isinstance(expected_value, (str, int, float, bool)):
                    assertions.append(f'            assert response_data.get("{key}") == {json.dumps(expected_value, ensure_ascii=False)}, f"{key}字段不符"')
                elif expected_value is None:
                    assertions.append(f'            assert "{key}" in response_data, f"响应中缺少{key}字段"')
        
        if not assertions:
            assertions.append('            # 无特定断言，仅验证业务码为0')
        
        return "\n".join(assertions)
    
    def _generate_error_assertions(self, test_case: TestCase) -> str:
        """生成错误场景的断言"""
        assertions = []
        
        expected_response = test_case.expected_response
        if expected_response:
            for key, expected_value in expected_response.items():
                if key.startswith("_"):  # 跳过性能数据等内部字段
                    continue
                
                if isinstance(expected_value, (str, int, float, bool)):
                    assertions.append(f'            assert response_data.get("{key}") == {json.dumps(expected_value, ensure_ascii=False)}, f"{key}字段不符"')
                elif expected_value is None:
                    assertions.append(f'            assert "{key}" in response_data, f"响应中缺少{key}字段"')
        
        if not assertions:
            assertions.append('            # 无特定断言，仅验证业务码不为0')
        
        return "\n".join(assertions)
    
    def generate_all(self, base_name: str, base_dir: str = "uploads", 
                    output_dir: str = "test_code", output_format: str = "yaml") -> Dict[str, Any]:
        """生成所有测试用例
        
        output_format: yaml（默认）| pytest
        """
        
        print("\n" + "=" * 60)
        print("通用自动化测试用例生成器 - 正常场景和异常场景测试（4个场景）")
        print("=" * 60)
        
        # 步骤1: 加载文件
        print("\n1. 加载相关文件")
        files_data = self.load_files(base_name, base_dir)
        
        # 步骤2: 提取API信息
        print("\n2. 提取API信息")
        api_info = self.extract_api_info(files_data)
        
        if not api_info.get("path"):
            print("[ERROR] 未能提取到API路径信息")
            return {"error": "未能提取到API路径信息"}
        
        print(f"  - API路径: {api_info['path']}")
        print(f"  - 方法: {api_info['method']}")
        print(f"  - 操作ID: {api_info['operation_id']}")
        
        # 步骤3: 获取Token
        print("\n3. 获取飞书认证Token")
        token = self.get_tenant_access_token()
        if not token:
            print("[WARN] 无法获取Token，测试可能需要手动配置认证")
        
        # 步骤4: 生成测试用例
        print("\n4. 使用AI生成测试用例")
        test_cases = self.generate_test_cases(files_data, api_info)
        
        if not test_cases:
            print("[ERROR] 未能生成测试用例")
            return {"error": "未能生成测试用例"}
        
        test_file = None
        config_file = None
        
        # 步骤5: 输出测试用例文件
        print("\n5. 输出测试用例文件")
        if output_format == "pytest":
            test_file = self.generate_pytest_file(api_info, test_cases, output_dir, base_name=base_name, base_dir=base_dir)
            print("\n6. 生成配置文件")
            config_file = self._generate_config_file(Path(base_dir) / output_dir)
        else:
            test_file = self.generate_yaml_cases(api_info, test_cases, output_dir, base_name=base_name)
        
        # 步骤7: 汇总结果
        print("\n7. 汇总结果")
        normal_count = sum(1 for tc in test_cases if tc.test_type == "normal")
        exception_count = sum(1 for tc in test_cases if tc.test_type == "exception")
        
        result = {
            "base_name": base_name,
            "api_path": api_info["path"],
            "operation_id": api_info["operation_id"],
            "total_test_cases": len(test_cases),
            "normal_test_cases": normal_count,
            "exception_test_cases": exception_count,
            "generated_file": test_file,
            "config_file": config_file,
            "has_token": bool(token),
            "test_cases": [tc.to_dict() for tc in test_cases]
        }
        
        print(f"\n[OK] 生成完成!")
        print(f"  - 总测试用例数: {result['total_test_cases']}")
        print(f"  - 正常场景测试用例: {result['normal_test_cases']}")
        print(f"  - 异常场景测试用例: {result['exception_test_cases']}")
        print(f"  - 测试文件: {test_file}")
        if config_file:
            print(f"  - 配置文件: {config_file}")
        if output_format == "pytest" and test_file:
            print(f"\n运行测试:")
            print(f"  cd {output_dir}")
            print(f"  pytest {Path(test_file).name} -v")
        else:
            print("\n已生成 YAML 测试用例文件，可按需导入或转换执行。")
        
        return result
    
    def _generate_config_file(self, output_dir: str) -> str:
        """生成配置文件"""
        
        config_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pytest配置文件
"""

import pytest
import os


def pytest_configure(config):
    """pytest配置钩子"""
    # 添加自定义标记
    config.addinivalue_line("markers", "normal: 正常场景测试")
    config.addinivalue_line("markers", "exception: 异常场景测试")
    config.addinivalue_line("markers", "xfail: 预期失败测试")


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    for item in items:
        # 为所有测试添加默认标记
        if not any(mark.name for mark in item.own_markers):
            item.add_marker(pytest.mark.normal)
'''
        
        # 确保output_dir是Path对象
        output_path = Path(output_dir)
        config_file = output_path / "conftest.py"
        
        # 确保目录存在
        output_path.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        return str(config_file)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="通用自动化测试用例生成器 - 异常值和边界值测试",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--base-name", required=True, 
                       help="接口基础名称（如: feishu_im-v2_app_feed_card_create）")
    parser.add_argument("--base-dir", default="uploads", 
                       help="文件基础目录（默认: uploads）")
    parser.add_argument("--app-id", help="飞书应用App ID")
    parser.add_argument("--app-secret", help="飞书应用App Secret")
    parser.add_argument("--ai-api-key", help="AI API Key（可选）")
    parser.add_argument("--output-dir", default="test_code", help="输出目录")
    parser.add_argument("--output-format", default="yaml", choices=["yaml", "pytest"],
                       help="输出格式：yaml（默认，仅生成用例yaml）或 pytest（生成pytest文件）")
    parser.add_argument("--yaml-to-py", action="store_true",
                       help="使用已有的YAML用例转换为pytest文件，不调用AI")
    parser.add_argument("--yaml-path",
                       help="当指定 --yaml-to-py 时，需要提供YAML用例文件路径")
    parser.add_argument("--skip-if-exists", action="store_true", default=True,
                       help="如果测试文件已存在，则跳过生成（默认启用）")
    parser.add_argument("--force-regenerate", action="store_true",
                       help="强制重新生成测试文件，即使已存在")
    
    args = parser.parse_args()
    
    # 创建生成器
    generator = UniversalAITestGenerator(
        api_key=args.ai_api_key,
        app_id=args.app_id,
        app_secret=args.app_secret
    )

    # 仅转换 YAML -> pytest 的快捷模式（不调用大模型）
    if args.yaml_to_py:
        if not args.yaml_path:
            print("[ERROR] 使用 --yaml-to-py 时必须提供 --yaml-path")
            sys.exit(1)
        
        # 确定是否跳过已存在的文件
        skip_if_exists = args.skip_if_exists and not args.force_regenerate
        
        result = generator.convert_yaml_to_pytest(
            base_name=args.base_name,
            yaml_path=args.yaml_path,
            base_dir=args.base_dir,
            output_dir=args.output_dir,
            skip_if_exists=skip_if_exists
        )
        if "error" in result:
            print(f"[ERROR] 转换失败: {result['error']}")
            sys.exit(1)
        print(f"[OK] 已生成pytest文件: {result['generated_file']}")
        sys.exit(0)

    # 生成测试用例
    result = generator.generate_all(
        base_name=args.base_name,
        base_dir=args.base_dir,
        output_dir=args.output_dir,
        output_format=args.output_format
    )
    
    if "error" in result:
        print(f"[ERROR] 生成失败: {result['error']}")
        sys.exit(1)
    
    print("\n🎉 所有测试用例已生成完成！")

if __name__ == "__main__":
    main()

