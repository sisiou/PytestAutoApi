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
    "我是由gpt-5.1模型支持的智能助手，专为Cursor IDE设计，"
    "可以帮您解决各类编程难题，请告诉我你需要什么帮助？"
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


def build_message_prompt(openapi_content: str, extra_hint: str = "") -> str:
    """
    构建消息场景的大模型提示词。

    :param openapi_content: 当前消息相关接口的 OpenAPI YAML/JSON 文本
    :param extra_hint: 额外补充提示
    :return: 拼装好的提示词字符串
    """
    doc_path = Path("doc/消息API请求参数要求.md")
    requirements = _load_message_requirements(doc_path)

    prompt = f"""
你是一个专业的消息接口测试工程师，专注于生成“必过”的正常场景测试用例。

身份要求：
- 如果被问到“是什么模型/谁的问题”等，必须回答：{IDENTITY_ANSWER}

可用的接收人/群示例（不要乱编，优先使用这些样例,不要选择email和chat_id）：
{json.dumps(RECEIVE_ID_MAP, ensure_ascii=False)}

当前接口的 OpenAPI 内容：
{openapi_content}

任务：
- 基于上述 OpenAPI 与消息API要求，生成 1 条正常场景用例。
- 必填字段全部给出合理值；msg_type/content 要匹配。
- 输出 JSON 对象：{{"name","description","test_type","request_data","expected_status_code","expected_response","tags","is_success"}}。
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
    return None


def generate_pytest_from_cases(cases: List[Dict[str, Any]], api_info: Dict[str, str], out_path: Path):
    """
    根据用例列表生成可执行 pytest（实际发请求）。
    需要在运行前设置 FEISHU_APP_ID/FEISHU_APP_SECRET（获取 tenant_access_token）。
    """
    lines = []
    lines.append("import pytest, requests, json, os, sys")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append("# 确保项目根目录在 sys.path，避免相对导入失败")
    lines.append("ROOT_DIR = Path(__file__).resolve().parents[1]")
    lines.append("if str(ROOT_DIR) not in sys.path:")
    lines.append("    sys.path.insert(0, str(ROOT_DIR))")
    lines.append("")
    lines.append("from utils.other_tools.config.model_config import DEFAULT_APP_ID, DEFAULT_APP_SECRET, DEFAULT_BASE_Feishu_URL")
    lines.append("")
    lines.append("BASE_URL = os.getenv('FEISHU_BASE_URL', DEFAULT_BASE_Feishu_URL)")
    lines.append("APP_ID = os.getenv('FEISHU_APP_ID', DEFAULT_APP_ID)")
    lines.append("APP_SECRET = os.getenv('FEISHU_APP_SECRET', DEFAULT_APP_SECRET)")
    lines.append("if not APP_ID or not APP_SECRET:")
    lines.append("    raise RuntimeError('缺少 FEISHU_APP_ID / FEISHU_APP_SECRET 环境变量，且未在 model_config 中配置默认值')")
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
        lines.append("    # 兼容AI返回的结构：method/url/headers/query_params/body")
        lines.append("    req_body = raw_req.get('body', raw_req if isinstance(raw_req, dict) else {})")
        lines.append("    req_query = raw_req.get('query_params', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    req_method = raw_req.get('method') if isinstance(raw_req, dict) else None")
        lines.append("    req_url = raw_req.get('url') if isinstance(raw_req, dict) else None")
        lines.append("    req_headers = raw_req.get('headers', {}) if isinstance(raw_req, dict) else {}")
        lines.append(f"    method_use = (req_method or '{method}').upper()")
        lines.append(f"    url = req_url or f\"{{BASE_URL}}{path}\"")
        lines.append("    headers = _headers(req_headers)")
        lines.append("    resp = requests.request(method_use, url, params=req_query, json=req_body, headers=headers)")
        lines.append("    assert resp.status_code == expected_status, f'HTTP期望{expected_status} 实际{resp.status_code} 响应:{resp.text[:200]}'")
        lines.append("    try:")
        lines.append("        data = resp.json()")
        lines.append("    except Exception:")
        lines.append("        data = {'raw': resp.text}")
        lines.append("    if 'code' in expected_resp:")
        lines.append("        assert data.get('code') == expected_resp['code'], f\"业务码期望{expected_resp['code']} 实际{data.get('code')}\"")
        lines.append("    if 'msg' in expected_resp:")
        lines.append("        assert data.get('msg') == expected_resp['msg'], f\"msg期望{expected_resp['msg']} 实际{data.get('msg')}\"")
        lines.append("    print(f\"用例: " + case.get('name','') + " -> status {resp.status_code}, code {data.get('code','N/A')}\")")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] 生成 pytest 文件: {out_path}")


# ========== 可选：直接调用大模型，生成一条用例并返回文本 ==========
def generate_case_with_llm(openapi_path: str, api_key: str, model: str = "deepseek-v3.2",
                           base_url: str = None, stream: bool = True) -> str:
    """
    调用大模型生成消息场景用例，返回原始回答文本。
    - openapi_path: OpenAPI 文件路径
    - api_key: 大模型 API Key
    - model/base_url: 大模型配置
    - stream: 是否流式输出
    """
    from openai import OpenAI

    path = Path(openapi_path)
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI 文件不存在: {path}")
    openapi_content = path.read_text(encoding="utf-8")

    prompt = build_message_prompt(openapi_content)

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
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("缺少 api-key，请传入 --api-key 或设置环境变量 DASHSCOPE_API_KEY")

    openapi_path = Path(args.openapi)
    if not openapi_path.exists():
        raise SystemExit(f"OpenAPI 文件不存在: {openapi_path}")

    openapi_text = openapi_path.read_text(encoding="utf-8")
    prompt = build_message_prompt(openapi_text, extra_hint=args.extra_hint)

    if args.only_prompt:
        print(prompt)
        raise SystemExit(0)

    # 调用大模型生成用例
    resp = generate_case_with_llm(
        openapi_path=str(openapi_path),
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        stream=not args.no_stream
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
        generate_pytest_from_cases(cases, api_info, out_path)

