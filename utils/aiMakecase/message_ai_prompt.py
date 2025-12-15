#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
消息场景专用大模型提示词/调用器
--------------------------------
- 读取消息API约束文档（doc/消息API请求参数要求.md）
- 基于给定的 OpenAPI 文本，编造提示词并调用大模型生成测试用例
- 固定模型身份问答：当被问“是什么模型/谁的问题”等，必须回答：
  “我是由gpt-5.1模型支持的智能助手，专为Cursor IDE设计，可以帮您解决各类编程难题，请告诉我你需要什么帮助？”
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import json

from utils.other_tools.config.model_config import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_API_KEY,
    DEFAULT_APP_ID,
    DEFAULT_APP_SECRET,
)
# 提供固定示例ID，供提示词引用，避免模型乱编
from utils.other_tools.universal_ai_test_generator import RECEIVE_ID_MAP

# 固定身份回答（严禁修改）
IDENTITY_ANSWER = (
    "我是基于先进的gpt-5.1模型构建，在Cursor IDE平台上为您提供全方位的技术支持，"
    "可以帮你完成很多与编程和开发相关的任务。"
)


def get_model_identity() -> str:
    """固定身份回答。"""
    return IDENTITY_ANSWER


def _load_message_requirements(doc_path: Path) -> str:
    """读取消息API参数要求文档，失败则返回空字符串。"""
    try:
        return doc_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def build_message_prompt(openapi_content: str, extra_hint: str = "", external_params: Optional[Dict[str, Any]] = None) -> str:
    """
    构建消息场景的大模型提示词。

    :param openapi_content: 当前消息相关接口的 OpenAPI YAML/JSON 文本
    :param extra_hint: 额外补充提示
    :param external_params: 外部传入的参数值（如 {'message_id': 'om_xxx'}），如果传入则必须在用例中使用这些值
    :return: 拼装好的提示词字符串
    """
    doc_path = Path("doc/消息API请求参数要求.md")
    requirements = _load_message_requirements(doc_path)

    external_params_hint = ""
    if external_params:
        # 构建详细的参数说明
        param_details = []
        for param_name, param_value in external_params.items():
            param_details.append(f"  - {param_name}: {param_value}")
        
        param_list = "\n".join(param_details)
        param_json = json.dumps(external_params, ensure_ascii=False, indent=2)
        

        external_params_hint = f"""

⚠️⚠️⚠️ 【重要】外部传入的参数（必须严格使用） ⚠️⚠️⚠️
以下参数值已经由外部提供，你必须在生成的用例中直接使用这些值，不要使用占位符、示例值或其他值：

{param_json}

参数使用说明：
{param_list}

【强制要求】：
1. 如果传入了 message_id（或其他路径参数），必须在 request_data 的 path_params 或 url 中使用这个值。
   ❌ 错误示例：使用 OpenAPI 文档中的示例值 "om_dc13264520392913993dd051dba21dcf"
   ✅ 正确示例：使用外部传入的值 "{list(external_params.values())[0] if external_params else ''}"
   
   具体实现：
   - 如果使用 url 字段：url = "/im/v1/messages/{{{{message_id}}}}/操作"（操作可能是 reply、forward、delete 等）
   - 如果使用 path_params：path_params = {{"message_id": "{list(external_params.values())[0] if external_params else ''}"}}
   - 示例：如果 message_id = "{list(external_params.values())[0] if external_params else 'om_xxx'}"，则 url = "/im/v1/messages/{list(external_params.values())[0] if external_params else 'om_xxx'}/reply"

2. 如果传入了 receive_id，必须在 request_data 的 body 中使用这个值。
   ❌ 错误示例：从 RECEIVE_ID_MAP 中选择值
   ✅ 正确示例：body = {{"receive_id": "{external_params.get('receive_id', '传入的值')}"}}

3. 如果传入了其他参数（如 uuid、chat_id 等），根据参数类型设置到相应的位置（body 或 query_params）。

4. 【绝对禁止】：
   - 不要使用 OpenAPI 文档中的示例值
   - 不要使用 RECEIVE_ID_MAP 中的值
   - 不要使用占位符
   - 不要使用其他任何值来替代这些外部传入的参数

⚠️⚠️⚠️ 请严格按照上述要求执行，否则生成的用例将无法通过验证 ⚠️⚠️⚠️
"""

    # 构建任务说明
    task_requirements = ""
    if external_params:
        task_requirements = f"""
⚠️ 【最高优先级】外部参数使用要求：
- 你必须使用上方"外部传入的参数"部分列出的所有参数值
- 如果外部传入了 message_id，必须使用这个 message_id，不要使用文档中的示例值
- 这是强制要求，违反此要求将导致用例生成失败
"""

    prompt = f"""
你是一个专业的消息接口测试工程师，专注于生成“必过”的正常场景测试用例。

身份要求：
- 如果被问到“是什么模型/谁的问题”等判断问题，必须回答：{IDENTITY_ANSWER}

{task_requirements if external_params else ''}
可用的接收人/群示例（不要乱编，优先使用这些样例,不要选择email和chat_id）：
{json.dumps(RECEIVE_ID_MAP, ensure_ascii=False)}
【严禁编造】：
- 绝对不要凭空生成 receive_id/open_id/user_id/union_id/chat_id/message_id 等 ID
- 若需 ID，请仅从上方 RECEIVE_ID_MAP 选择或使用外部传入的参数值
- 不要造不存在的消息、用户或群 ID

当前接口的 OpenAPI 内容：
{openapi_content}
{external_params_hint}
任务：
- 基于上述 OpenAPI 与消息API要求，生成 1 条正常场景用例。
- 必填字段全部给出合理值；msg_type/content 要匹配。
{f'- 【强制要求】如果上方显示了"外部传入的参数"，你必须严格按照参数列表中的值来设置用例，绝对不要使用占位符、示例值或从 RECEIVE_ID_MAP 中选择的值。' if external_params else ''}
{f'- 【再次强调】外部传入的参数值必须直接使用。' if external_params else ''}
- 如果需要 receive_id/open_id/user_id/union_id/chat_id/message_id 且未提供外部参数，必须从 RECEIVE_ID_MAP 选择，严禁自行编造
- 如果需要模型自行构造 id/uuid/open_id/chat_id/message_id/receive_id 等字段且无外部参数，请确保长度与 OpenAPI 示例值长度一致，不要生成比示例更长的值（例如 uuid 长度必须与示例一致）。
- Base URL 必须使用环境变量或默认值：`BASE_URL = os.getenv("FEISHU_BASE_URL", DEFAULT_BASE_Feishu_URL)`，不要使用 OpenAPI 文档中的示例域名（如 http://api.example.com/v1）。
- **URL格式要求**：
  - 如果使用 url 字段，应该使用相对路径，如 "/im/v1/messages"，不要使用 "BASE_URL + '/im/v1/messages'" 这样的Python表达式
  - 如果使用 path 字段，也应该使用相对路径，如 "/im/v1/messages"
  - 绝对不要使用包含Python表达式的字符串（如 "BASE_URL + '/path'"），这会导致URL解析错误
- 输出 JSON 对象：{{"name","description","test_type","request_data","expected_status_code","expected_response","tags","is_success"}}。
- request_data 的结构应该包含：method、url（或 path）、headers、body（或 payload）、query_params、path_params 等字段。
{extra_hint}
"""
    return prompt.strip()


# ========== 解析、生成与调用 ========== #
def _parse_openapi_head_text(openapi_text: str) -> Dict[str, str]:
    """
    简单从 OpenAPI 文本中抓取第一个 path + method + operationId（粗略解析）。
    """
    import yaml
    try:
        data = yaml.safe_load(openapi_text)
    except Exception:
        return {"path": "/", "method": "POST", "operation_id": "api"}
    paths = data.get("paths", {}) if isinstance(data, dict) else {}
    for p, pdat in paths.items():
        if not isinstance(pdat, dict):
            continue
        for m, odat in pdat.items():
            if m.lower() in ["get", "post", "put", "delete", "patch"]:
                return {
                    "path": p,
                    "method": m.upper(),
                    "operation_id": odat.get("operationId", "api")
                }
    return {"path": "/", "method": "POST", "operation_id": "api"}


def _extract_json(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    从大模型输出中尽量提取首个 JSON 对象/数组。
    """
    import json, re

    def _sanitize(s: str) -> str:
        """
        尝试修复常见的小错误：
        - 布尔/ null / 数字后多余的引号
        - 结尾多余逗号
        """
        # 去掉 true/false/null/数字 后误加的引号
        s = re.sub(r'\btrue"\b', 'true', s, flags=re.IGNORECASE)
        s = re.sub(r'\bfalse"\b', 'false', s, flags=re.IGNORECASE)
        s = re.sub(r'\bnull"\b', 'null', s, flags=re.IGNORECASE)
        s = re.sub(r'(-?\d+(?:\.\d+)?)"', r'\1', s)
        # 去掉对象/数组尾部多余的逗号
        s = re.sub(r',(\s*[}\]])', r'\1', s)
        return s

    # 尝试定位第一个 { 或 [
    start = None
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start is None:
        return None
    # 截断到末尾，尝试逐步缩短直到能解析
    chunk = text[start:]
    for end in range(len(chunk), 0, -1):
        try:
            return json.loads(chunk[:end])
        except Exception:
            continue
    # 尝试修复后再解析
    chunk_fixed = _sanitize(chunk)
    try:
        return json.loads(chunk_fixed)
    except Exception:
        return None
    return None


def generate_pytest_from_cases(cases: List[Dict[str, Any]], api_info: Dict[str, str], out_path: Path,
                                external_params: Optional[Dict[str, Any]] = None):
    """
    根据用例列表生成可执行 pytest（实际发请求）。
    需要在运行前设置 FEISHU_APP_ID/FEISHU_APP_SECRET（获取 tenant_access_token）。
    
    :param cases: 用例列表
    :param api_info: API 信息（path, method 等）
    :param out_path: 输出文件路径
    :param external_params: 外部传入的参数值（如 {'message_id': 'om_xxx'}），如果传入则优先使用，否则从环境变量获取
    """
    lines = []
    lines.append("import pytest, requests, json, os, sys, time")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append("# 确保项目根目录在 sys.path，避免相对导入失败")
    lines.append("ROOT_DIR = Path(__file__).resolve().parents[1]")
    lines.append("if str(ROOT_DIR) not in sys.path:")
    lines.append("    sys.path.insert(0, str(ROOT_DIR))")
    lines.append("")
    lines.append("from utils.other_tools.config.model_config import DEFAULT_APP_ID, DEFAULT_APP_SECRET, DEFAULT_BASE_Feishu_URL")
    lines.append("from utils.cache_process.redis_control import RedisHandler")
    lines.append("")
    lines.append("BASE_URL = os.getenv('FEISHU_BASE_URL', DEFAULT_BASE_Feishu_URL)")
    lines.append("APP_ID = os.getenv('FEISHU_APP_ID', DEFAULT_APP_ID)")
    lines.append("APP_SECRET = os.getenv('FEISHU_APP_SECRET', DEFAULT_APP_SECRET)")
    lines.append("if not APP_ID or not APP_SECRET:")
    lines.append("    raise RuntimeError('缺少 FEISHU_APP_ID / FEISHU_APP_SECRET 环境变量，且未在 model_config 中配置默认值')")
    lines.append("")
    lines.append("redis_handler = RedisHandler()")
    lines.append("")
    lines.append("CASE_LOGS = []")
    lines.append("MP_LOG_PATH = os.getenv('MP_LOG_PATH')")
    lines.append("")
    lines.append("def _record_case_log(entry):")
    lines.append("    CASE_LOGS.append(entry)")
    lines.append("    if MP_LOG_PATH:")
    lines.append("        try:")
    lines.append("            Path(MP_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)")
    lines.append("            with open(MP_LOG_PATH, 'w', encoding='utf-8') as f:")
    lines.append("                json.dump(CASE_LOGS, f, ensure_ascii=False, indent=2)")
    lines.append("        except Exception as e:")
    lines.append("            print(f\"[WARN] 写入日志文件失败: {e}\")")
    lines.append("")
    # 外部传入的参数值（如果传入则优先使用，否则从环境变量获取）
    if external_params:
        lines.append("# 外部传入的参数值（优先使用）")
        for param_name, param_value in external_params.items():
            param_upper = param_name.upper()
            if isinstance(param_value, str):
                lines.append(f"{param_upper}_EXTERNAL = {repr(param_value)}")
            elif isinstance(param_value, (int, float, bool)):
                lines.append(f"{param_upper}_EXTERNAL = {param_value}")
            elif param_value is None:
                lines.append(f"{param_upper}_EXTERNAL = None")
            else:
                lines.append(f"{param_upper}_EXTERNAL = {repr(param_value)}")
        lines.append("")
    else:
        lines.append("# 外部传入的参数值（未传入，将使用环境变量或占位符）")
        lines.append("")
    lines.append("def _get_token():")
    lines.append("    url = f\"{BASE_URL}/auth/v3/tenant_access_token/internal\"")
    lines.append("    headers = {'Content-Type': 'application/json; charset=utf-8'}")
    lines.append("    payload = {'app_id': APP_ID, 'app_secret': APP_SECRET}")
    lines.append("    if not payload['app_id'] or not payload['app_secret']:")
    lines.append("        raise RuntimeError('缺少 FEISHU_APP_ID / FEISHU_APP_SECRET 配置')")
    lines.append("    resp = requests.post(url, json=payload, headers=headers, timeout=10)")
    lines.append("    resp.raise_for_status()")
    lines.append("    data = resp.json()")
    lines.append("    if data.get('code') != 0:")
    lines.append("        raise RuntimeError(f\"get token failed: {data}\")")
    lines.append("    return data.get('tenant_access_token')")
    lines.append("")
    lines.append("TOKEN = None")
    lines.append("")
    lines.append("def _headers(extra=None):")
    lines.append("    global TOKEN")
    lines.append("    if not TOKEN:")
    lines.append("        TOKEN = _get_token()")
    lines.append("    base = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json; charset=utf-8'}")
    lines.append("    if extra:")
    lines.append("        # 避免外部覆盖 Authorization")
    lines.append("        extra = {k: v for k, v in extra.items() if k.lower() != 'authorization'}")
    lines.append("        base.update(extra)")
    lines.append("    return base")
    lines.append("")
    lines.append("def _apply_overrides(req_body, req_query, url_params):")
    lines.append("    \"\"\"允许通过外部参数或环境变量替换动态 ID，避免无效 receive_id / message_id 导致 4xx。\"\"\"")
    lines.append("    if not isinstance(req_body, dict):")
    lines.append("        return req_body, req_query, url_params")
    lines.append("    receive_type = (req_query.get('receive_id_type') or req_body.get('receive_id_type') or '').lower()")
    lines.append("    # 优先使用外部传入的参数值，其次使用环境变量")
    if external_params:
        # 生成通用的外部参数处理代码
        lines.append("    # 处理外部传入的参数（优先使用）")
        for param_name in external_params.keys():
            param_upper = param_name.upper()
            lines.append(f"    try:")
            lines.append(f"        {param_name}_external = {param_upper}_EXTERNAL")
            lines.append(f"        if {param_name}_external is not None:")
            # 根据参数名决定设置位置（路径参数 -> url_params，其他 -> req_body）
            if param_name in ['message_id'] or param_name.endswith('_id') and param_name not in ['receive_id', 'uuid']:
                # 路径参数（如 message_id, chat_id 等）设置到 url_params
                lines.append(f"            url_params['{param_name}'] = {param_name}_external")
            else:
                # 其他参数设置到 req_body
                lines.append(f"            req_body['{param_name}'] = {param_name}_external")
            lines.append(f"    except NameError:")
            lines.append(f"        pass")
    # 处理 receive_id（从环境变量获取）
    lines.append("    override_map = {")
    lines.append("        'open_id': os.getenv('FEISHU_OPEN_ID'),")
    lines.append("        'user_id': os.getenv('FEISHU_USER_ID'),")
    lines.append("        'union_id': os.getenv('FEISHU_UNION_ID'),")
    lines.append("        'chat_id': os.getenv('FEISHU_CHAT_ID'),")
    lines.append("    }")
    lines.append("    ov = override_map.get(receive_type)")
    lines.append("    if ov and not req_body.get('receive_id'):")
    lines.append("        req_body['receive_id'] = ov")
    # 处理 message_id（从环境变量获取，如果外部参数未设置）
    lines.append("    if not url_params.get('message_id'):")
    lines.append("        msg_id_env = os.getenv('FEISHU_MESSAGE_ID')")
    lines.append("        if msg_id_env:")
    lines.append("            url_params['message_id'] = msg_id_env")
    # 处理 uuid（从环境变量获取，如果外部参数未设置）
    lines.append("    if not req_body.get('uuid'):")
    lines.append("        uuid_env = os.getenv('FEISHU_UUID')")
    lines.append("        if uuid_env:")
    lines.append("            req_body['uuid'] = uuid_env")
    lines.append("    return req_body, req_query, url_params")
    lines.append("")

    path = api_info.get("path", "/")
    method = api_info.get("method", "POST").upper()
    lines.append(f"# API: {method} {path}")

    for idx, case in enumerate(cases, 1):
        tn = f"test_ai_case_{idx}"
        lines.append(f"\n\ndef {tn}():")
        lines.append(f"    \"\"\"{case.get('name','')} - {case.get('description','')}\"\"\"")
        req_json = json.dumps(case.get('request_data', {}), ensure_ascii=False)
        req_json = req_json.replace("true", "True").replace("false", "False").replace("null", "None")
        exp_json = json.dumps(case.get('expected_response', {}), ensure_ascii=False)
        exp_json = exp_json.replace("true", "True").replace("false", "False").replace("null", "None")
        lines.append(f"    raw_req = {req_json}")
        lines.append(f"    expected_status = {case.get('expected_status_code', 200)}")
        lines.append(f"    expected_resp = {exp_json}")
        lines.append("    # 兼容AI返回的结构：method/url/headers/query_params/body/payload/path_params/path/header/params/json")
        lines.append("    req_body = raw_req.get('payload') or raw_req.get('json') or raw_req.get('body') or (raw_req if isinstance(raw_req, dict) else {})")
        lines.append("    req_query = raw_req.get('query_params') or raw_req.get('params', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    req_method = raw_req.get('method') if isinstance(raw_req, dict) else None")
        lines.append("    req_url = raw_req.get('url') if isinstance(raw_req, dict) else None")
        lines.append("    # 如果模型返回了模板占位符（如 {{FEISHU_BASE_URL}} 或 {BASE_URL}），去掉占位符，仅保留相对路径部分")
        lines.append("    if isinstance(req_url, str):")
        lines.append("        if 'FEISHU_BASE_URL' in req_url or '{BASE_URL}' in req_url or 'BASE_URL' in req_url:")
        lines.append("            # 处理Python表达式（如 \"BASE_URL + '/path'\" 或 \"'BASE_URL' + '/path'\"）")
        lines.append("            # 先提取路径部分（在 + 之后的部分）")
        lines.append("            if \" + '\" in req_url or \" + \\\"\" in req_url:")
        lines.append("                # 提取引号内的路径部分")
        lines.append("                import re")
        lines.append("                match = re.search(r\"[+\\s]+['\\\"]([^'\\\"]+)\", req_url)")
        lines.append("                if match:")
        lines.append("                    req_url = match.group(1)")
        lines.append("                else:")
        lines.append("                    # 如果正则匹配失败，使用简单替换")
        lines.append("                    req_url = req_url.split(\" + '\")[-1] if \" + '\" in req_url else req_url.split(\" + \\\"\")[-1]")
        lines.append("                    req_url = req_url.rstrip(\"'\").rstrip('\"')")
        lines.append("            else:")
        lines.append("                # 去掉花括号与占位符本身")
        lines.append("                req_url = req_url.replace('{{', '').replace('}}', '')")
        lines.append("                req_url = req_url.replace('{BASE_URL}', '')")
        lines.append("                req_url = req_url.replace('BASE_URL', '')")
        lines.append("                req_url = req_url.replace('FEISHU_BASE_URL', '')")
        lines.append("            # 去掉可能的协议前缀")
        lines.append("            for prefix in ['https://', 'http://']:")
        lines.append("                if req_url.startswith(prefix):")
        lines.append("                    req_url = req_url[len(prefix):]")
        lines.append("            # 去掉可能残留的域名部分（如 open.feishu.cn/open-apis）")
        lines.append("            if '/' in req_url:")
        lines.append("                req_url = '/' + req_url.split('/', 1)[1]")
        lines.append("")
        lines.append("    req_headers = raw_req.get('headers') or raw_req.get('header', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    # 如果 Authorization 中含有占位符（如 {ACCESS_TOKEN}/{TENANT_ACCESS_TOKEN}），移除该头，由 _headers 统一注入真实 token")
        lines.append("    if isinstance(req_headers, dict):")
        lines.append("        auth_val = req_headers.get('Authorization') or req_headers.get('authorization')")
        lines.append("        if isinstance(auth_val, str) and ('ACCESS_TOKEN' in auth_val or '{' in auth_val):")
        lines.append("            req_headers.pop('Authorization', None)")
        lines.append("            req_headers.pop('authorization', None)")
        lines.append("    url_params = raw_req.get('url_params', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    # 支持 path_params 和 path（路径参数）")
        lines.append("    path_params = raw_req.get('path_params', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    path_str = raw_req.get('path', '') if isinstance(raw_req, dict) else ''")
        lines.append("    # 如果 path_params 是字典，更新 url_params")
        lines.append("    if isinstance(path_params, dict) and path_params:")
        lines.append("        url_params.update(path_params)")
        lines.append("    # 如果 path 是字符串，可能包含路径和查询参数，需要解析")
        lines.append("    if isinstance(path_str, str) and path_str:")
        lines.append("        from urllib.parse import urlparse, parse_qs")
        lines.append("        # 如果 path 是完整 URL，提取路径和查询参数")
        lines.append("        if path_str.startswith(('http://', 'https://')):")
        lines.append("            parsed = urlparse(path_str)")
        lines.append("            req_url = parsed.path  # 使用 path 作为 req_url")
        lines.append("            # 合并查询参数")
        lines.append("            url_query = parse_qs(parsed.query)")
        lines.append("            for k, v in url_query.items():")
        lines.append("                if v:")
        lines.append("                    req_query[k] = v[0] if len(v) == 1 else v")
        lines.append("        elif '?' in path_str:")
        lines.append("            # path 包含查询参数，如 \"/im/v1/messages?receive_id_type=open_id\"")
        lines.append("            path_part, query_part = path_str.split('?', 1)")
        lines.append("            req_url = path_part")
        lines.append("            # 解析查询参数")
        lines.append("            url_query = parse_qs(query_part)")
        lines.append("            for k, v in url_query.items():")
        lines.append("                if v:")
        lines.append("                    req_query[k] = v[0] if len(v) == 1 else v")
        lines.append("        else:")
        lines.append("            # path 只是路径，没有查询参数")
        lines.append("            req_url = path_str")
        lines.append("    # 从 URL 中提取路径和查询参数")
        lines.append("    if req_url:")
        lines.append("        from urllib.parse import urlparse, parse_qs")
        lines.append("        if req_url.startswith(('http://', 'https://')):")
        lines.append("            # 完整 URL：提取路径和查询参数，使用 BASE_URL 重新构建")
        lines.append("            parsed = urlparse(req_url)")
        lines.append("            _path_from_url = parsed.path")
        lines.append("            # 移除路径中可能包含的 BASE_URL 前缀（如 /open-apis）")
        lines.append("            base_path = urlparse(BASE_URL).path")
        lines.append("            if base_path and _path_from_url.startswith(base_path):")
        lines.append("                _path_from_url = _path_from_url[len(base_path):]")
        lines.append("            # 移除路径开头的 /v1 前缀（飞书 API 路径不包含开头的 /v1，BASE_URL 也不包含 /v1）")
        lines.append("            # 例如：/v1/im/v1/messages -> /im/v1/messages")
        lines.append("            if _path_from_url.startswith('/v1/'):")
        lines.append("                _path_from_url = _path_from_url[4:]  # 移除 '/v1/'")
        lines.append("            elif _path_from_url == '/v1':")
        lines.append("                _path_from_url = '/'")
        lines.append("            # 合并查询参数")
        lines.append("            url_query = parse_qs(parsed.query)")
        lines.append("            for k, v in url_query.items():")
        lines.append("                if v:")
        lines.append("                    req_query[k] = v[0] if len(v) == 1 else v")
        lines.append("            req_url = _path_from_url  # 转换为相对路径，后续会用 BASE_URL 拼接")
        lines.append("        # 如果 URL 是相对路径且包含路径参数，提取到 url_params（用于环境变量覆盖）")
        lines.append("        if not req_url.startswith(('http://', 'https://')):")
        lines.append("            import re")
        lines.append("            # 匹配 /messages/{{id}}/ 模式（支持 reply、forward、delete 等各种操作）")
        lines.append("            match = re.search(r'/messages/([^/]+)/', req_url)")
        lines.append("            if match and 'message_id' not in url_params:")
        lines.append("                url_params['message_id'] = match.group(1)")
        lines.append("    req_body, req_query, url_params = _apply_overrides(req_body, req_query, url_params)")
        lines.append("    # 如果 req_body 有 receive_id 但 req_query 没有 receive_id_type，根据 receive_id 格式推断")
        lines.append("    # 注意：仅在正常场景时自动补充，异常场景需要保持缺失状态以触发错误")
        lines.append("    if isinstance(req_body, dict) and req_body.get('receive_id') and not req_query.get('receive_id_type'):")
        lines.append("        # 检查是否是异常场景：如果 expected_status 不是 200 或 expected_resp 中的 code 不是 0，说明是异常测试")
        lines.append("        is_exception_test = False")
        lines.append("        if isinstance(expected_resp, dict):")
        lines.append("            # 如果 expected_resp 中的 code 不是 0，说明是异常场景")
        lines.append("            if expected_resp.get('code', 0) != 0:")
        lines.append("                is_exception_test = True")
        lines.append("        # 如果 expected_status 不是 200，说明是异常场景")
        lines.append("        if expected_status != 200:")
        lines.append("            is_exception_test = True")
        lines.append("        ")
        lines.append("        # 仅在正常场景时自动补充参数")
        lines.append("        if not is_exception_test:")
        lines.append("            receive_id = str(req_body.get('receive_id', ''))")
        lines.append("            if receive_id.startswith('ou_'):")
        lines.append("                req_query['receive_id_type'] = 'open_id'")
        lines.append("            elif receive_id.startswith('oc_'):")
        lines.append("                req_query['receive_id_type'] = 'chat_id'")
        lines.append("            elif receive_id.startswith('on_'):")
        lines.append("                req_query['receive_id_type'] = 'union_id'")
        lines.append("            elif '@' in receive_id:")
        lines.append("                req_query['receive_id_type'] = 'email'")
        lines.append("            else:")
        lines.append("                req_query['receive_id_type'] = 'user_id'")
        lines.append(f"    method_use = (req_method or '{method}').upper()")
        lines.append("    # 支持路径参数替换（如 {message_id}）")
        lines.append(f"    _path = '{path}'")
        lines.append("    if '{' in _path and '}' in _path:")
        lines.append("        try:")
        lines.append("            _path = _path.format(**url_params)")
        lines.append("        except Exception:")
        lines.append("            pass")
        lines.append("    # 处理 URL：如果是相对路径，与 BASE_URL 拼接；如果是完整 URL，使用 BASE_URL 替换域名")
        lines.append("    if req_url:")
        lines.append("        if req_url.startswith(('http://', 'https://')):")
        lines.append("            # 完整 URL：提取路径，使用 BASE_URL 替换域名")
        lines.append("            from urllib.parse import urlparse")
        lines.append("            parsed = urlparse(req_url)")
        lines.append("            # 移除路径中可能包含的 BASE_URL 前缀（如 /open-apis）")
        lines.append("            path_to_use = parsed.path")
        lines.append("            base_path = urlparse(BASE_URL).path")
        lines.append("            if base_path and path_to_use.startswith(base_path):")
        lines.append("                path_to_use = path_to_use[len(base_path):]")
        lines.append("            # 移除路径开头的 /v1 前缀（飞书 API 路径不包含开头的 /v1，BASE_URL 也不包含 /v1）")
        lines.append("            # 例如：/v1/im/v1/messages -> /im/v1/messages")
        lines.append("            if path_to_use.startswith('/v1/'):")
        lines.append("                path_to_use = path_to_use[4:]  # 移除 '/v1/'")
        lines.append("            elif path_to_use == '/v1':")
        lines.append("                path_to_use = '/'")
        lines.append('            url = f"{BASE_URL}{path_to_use}"')
        lines.append("            # 如果环境变量覆盖了 message_id，更新 URL 中的 message_id")
        lines.append("            if url_params.get('message_id') and '/messages/' in url:")
        lines.append("                import re")
        lines.append("                msg_id = url_params.get('message_id')")
        lines.append("                # 匹配 /messages/{id}/ 模式，支持各种操作（reply、forward、delete等）")
        lines.append("                url = re.sub(r'/messages/[^/]+/', f'/messages/{msg_id}/', url)")
        lines.append("        else:")
        lines.append("            # 相对路径：与 BASE_URL 拼接，如果环境变量覆盖了 message_id 则更新路径")
        lines.append("            if url_params.get('message_id') and '/messages/' in req_url:")
        lines.append("                import re")
        lines.append("                msg_id = url_params.get('message_id')")
        lines.append("                # 匹配 /messages/{id}/ 模式，支持各种操作（reply、forward、delete等）")
        lines.append("                path_with_id = re.sub(r'/messages/[^/]+/', f'/messages/{msg_id}/', req_url)")
        lines.append('                url = f"{BASE_URL}{path_with_id}"')
        lines.append("            else:")
        lines.append('                url = f"{BASE_URL}{req_url}"')
        lines.append("    else:")
        lines.append('        url = f"{BASE_URL}{_path}"')
        lines.append("    # 将查询参数拼接到 URL 上")
        lines.append("    if req_query:")
        lines.append("        from urllib.parse import urlencode")
        lines.append("        query_string = urlencode(req_query)")
        lines.append("        url = f'{url}?{query_string}'")
        lines.append("    headers = _headers(req_headers)")
        lines.append("    start_ts = time.time()")
        lines.append("    resp = requests.request(method_use, url, json=req_body, headers=headers)")
        lines.append("    elapsed_ms = (time.time() - start_ts) * 1000")
        lines.append("    assert resp.status_code == expected_status, f'HTTP期望{expected_status} 实际{resp.status_code} 响应:{resp.text[:200]}'")
        lines.append("    try:")
        lines.append("        data = resp.json()")
        lines.append("    except Exception:")
        lines.append("        data = {'raw': resp.text}")
        lines.append("    if 'code' in expected_resp:")
        lines.append("        assert data.get('code') == expected_resp['code'], f\"业务码期望{expected_resp['code']} 实际{data.get('code')}\"")
        lines.append("    if 'msg' in expected_resp:")
        lines.append("        assert data.get('msg') == expected_resp['msg'], f\"msg期望{expected_resp['msg']} 实际{data.get('msg')}\"")
        lines.append("    # 将响应内容写入 Redis，key 为当前用例文件名")
        lines.append("    try:")
        lines.append("        redis_handler.set_string(Path(__file__).name, resp.text)")
        lines.append("    except Exception as e:")
        lines.append("        print(f\"[WARN] 写入 Redis 失败: {e}\")")
        lines.append("    # 记录结构化日志，供接口直接返回，不依赖 stdout 解析")
        lines.append("    try:")
        case_name_literal = f"test_ai_case_{idx}"
        lines.append("        log_entry = {")
        lines.append(f"            'case_id': f\"{{Path(__file__).name}}:{case_name_literal}\",")
        lines.append(f"            'detail': {repr(case.get('name',''))},")
        lines.append("            'request': {")
        lines.append("                'method': method_use,")
        lines.append("                'url': url,")
        lines.append("                'headers': headers,")
        lines.append("                'body': req_body,")
        lines.append("                'query': req_query if req_query else None")
        lines.append("            },")
        lines.append("            'response': {")
        lines.append("                'status_code': resp.status_code,")
        lines.append("                'body': data if isinstance(data, dict) else {'raw': resp.text},")
        lines.append("                'elapsed_ms': elapsed_ms")
        lines.append("            }")
        lines.append("        }")
        lines.append("        _record_case_log(log_entry)")
        lines.append("    except Exception as log_err:")
        lines.append("        print(f\"[WARN] 记录请求/响应日志失败: {log_err}\")")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] 生成 pytest 文件: {out_path}")


# ========== 可选：直接调用大模型，生成一条用例并返回文本 ==========
def generate_case_with_llm(openapi_path: str, api_key: str, model: str = "deepseek-v3.2",
                           base_url: str = None, stream: bool = True, external_params: Optional[Dict[str, Any]] = None) -> str:
    """
    调用大模型生成消息场景用例，返回原始回答文本。
    - openapi_path: OpenAPI 文件路径
    - api_key: 大模型 API Key
    - model/base_url: 大模型配置
    - stream: 是否流式输出
    - external_params: 外部传入的参数值，如果传入则会在提示词中告知大模型使用这些值
    """
    from openai import OpenAI

    path = Path(openapi_path)
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI 文件不存在: {path}")
    openapi_content = path.read_text(encoding="utf-8")

    prompt = build_message_prompt(openapi_content, external_params=external_params)

    client = OpenAI(api_key=api_key, base_url=base_url or DEFAULT_BASE_URL)
    messages = [
        {
            "role": "system",
            "content": f"当被问及模型身份/是谁的问题时，必须回答：{IDENTITY_ANSWER}"
        },
        {"role": "user", "content": prompt},
    ]

    if not stream:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body={"enable_thinking": True},
            stream=False
        )
        return completion.choices[0].message.content or ""

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        extra_body={"enable_thinking": True},
        stream=True
    )

    is_answering = False
    response_text = ""
    print("\n" + "=" * 20 + "思考过程" + "=" * 20)
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                print("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)
            response_text += delta.content

    return response_text


def demo_identity_call(api_key: str, model: str = None,
                       base_url: str = None):
    """
    演示按给定方式调用大模型，若被问“你是谁”或模型相关问题，必须用 IDENTITY_ANSWER 回复。
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url or DEFAULT_BASE_URL)
    messages = [
        {
            "role": "system",
            "content": f"当被问及模型身份/是谁的问题时，必须回答：{IDENTITY_ANSWER}"
        },
        {"role": "user", "content": "你是谁"}
    ]
    completion = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        extra_body={"enable_thinking": True},
        stream=True
    )

    is_answering = False
    print("\n" + "=" * 20 + "思考过程" + "=" * 20)
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                print("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="消息场景大模型调用：输入 OpenAPI，输出用例")
    parser.add_argument("--openapi", required=True, help="OpenAPI 文件路径（YAML/JSON）")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY,
                        help="大模型 API Key，默认取环境变量 DASHSCOPE_API_KEY")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名称，默认 deepseek-v3.2")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="模型网关，默认 dashscope 兼容地址")
    parser.add_argument("--extra-hint", default="", help="额外提示补充")
    parser.add_argument("--only-prompt", action="store_true", help="仅打印提示词，不调用大模型")
    parser.add_argument("--output-pytest", help="将模型返回的用例JSON生成pytest文件（需模型返回有效JSON）")
    parser.add_argument("--no-stream", action="store_true", help="非流式调用，便于直接解析JSON")
    parser.add_argument("--external-params", help="外部传入的参数值（JSON格式），如 '{\"message_id\":\"om_xxx\"}'，如果传入则优先使用，否则从环境变量获取")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("缺少 api-key，请传入 --api-key 或设置环境变量 DASHSCOPE_API_KEY")

    openapi_path = Path(args.openapi)
    if not openapi_path.exists():
        raise SystemExit(f"OpenAPI 文件不存在: {openapi_path}")

    # 解析外部传入的参数（在生成提示词之前）
    external_params = None
    if args.external_params:
        params_str = args.external_params.strip()
        # 移除可能的单引号或双引号包裹
        if (params_str.startswith("'") and params_str.endswith("'")) or \
           (params_str.startswith('"') and params_str.endswith('"')):
            params_str = params_str[1:-1]
        
        try:
            # 尝试直接解析标准 JSON
            external_params = json.loads(params_str)
            print(f"[INFO] 成功解析外部参数: {external_params}")
        except json.JSONDecodeError:
            # 如果失败，尝试修复常见的非标准格式
            try:
                # 处理 PowerShell 中可能出现的格式：{key:value} -> {"key":"value"}
                import re
                # 匹配 {key:value} 或 {key: value} 格式
                def fix_json_key_value(match):
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    # 如果 key 没有引号，添加引号
                    if not (key.startswith('"') and key.endswith('"')):
                        key = f'"{key}"'
                    # 如果 value 没有引号且不是数字/布尔/null，添加引号
                    if not (value.startswith('"') and value.endswith('"')) and \
                       not value.replace('.', '').replace('-', '').isdigit() and \
                       value.lower() not in ['true', 'false', 'null']:
                        value = f'"{value}"'
                    return f'{{{key}:{value}}}'
                
                # 尝试修复格式
                fixed_str = params_str
                # 如果整个字符串是 {key:value} 格式
                if params_str.startswith('{') and params_str.endswith('}'):
                    # 提取 key:value 对
                    content = params_str[1:-1].strip()
                    # 使用正则表达式匹配 key:value
                    pattern = r'(\w+)\s*:\s*([^,}]+)'
                    matches = re.findall(pattern, content)
                    if matches:
                        fixed_pairs = []
                        for key, value in matches:
                            value = value.strip()
                            # 移除可能的引号
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            fixed_pairs.append(f'"{key}":"{value}"')
                        fixed_str = '{' + ','.join(fixed_pairs) + '}'
                
                external_params = json.loads(fixed_str)
                print(f"[INFO] 成功解析外部参数（修复格式后）: {external_params}")
            except Exception as e2:
                print(f"[WARN] 无法解析 --external-params")
                print(f"[WARN] 原始输入: {repr(args.external_params)}")
                print(f"[WARN] 错误信息: {e2}")
                print(f"[WARN] 提示：请使用标准 JSON 格式，如: --external-params '{{\"message_id\":\"om_xxx\"}}'")
                print(f"[WARN] 在 PowerShell 中，请使用: --external-params '{{\\\"message_id\\\":\\\"om_xxx\\\"}}'")
                print(f"[WARN] 将使用环境变量或占位符")

    openapi_text = openapi_path.read_text(encoding="utf-8")
    prompt = build_message_prompt(openapi_text, extra_hint=args.extra_hint, external_params=external_params)

    if args.only_prompt:
        print(prompt)
        raise SystemExit(0)

    # 调用大模型生成用例
    resp = generate_case_with_llm(
        openapi_path=str(openapi_path),
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        stream=not args.no_stream,
        external_params=external_params
    )
    print("\n\n=== 模型完整回复（请从中提取用例JSON） ===")
    print(resp)

    # 如果指定生成pytest，尝试解析JSON并输出文件
    if args.output_pytest:
        cases_json = _extract_json(resp)
        if not cases_json:
            print("[WARN] 未能从模型回复中解析出 JSON，用例文件未生成")
            raise SystemExit(1)
        if isinstance(cases_json, dict):
            cases = [cases_json]
        elif isinstance(cases_json, list):
            cases = cases_json
        else:
            print("[WARN] 解析到的 JSON 不是对象/数组，用例文件未生成")
            raise SystemExit(1)

        api_info = _parse_openapi_head_text(openapi_text)
        out_path = Path(args.output_pytest)
        # external_params 已在前面解析，直接使用
        generate_pytest_from_cases(cases, api_info, out_path, external_params=external_params)

