import json
import os
from pathlib import Path

from utils.aiMakecase.model_config import DEFAULT_APP_ID, DEFAULT_APP_SECRET, DEFAULT_BASE_URL

# 把大模型的 JSON 回复粘到这里（必须是合法 JSON 对象或数组）
AI_REPLY = []

# API 默认配置（可按需修改）
BASE_URL = DEFAULT_BASE_URL  # 仅用于 token 获取，真实请求用 AI 给出的 url 或 fallback
DEFAULT_PATH = "/im/v1/messages"

OUT_FILE = Path("tests/test_ai_message_generated.py")


def main():
    if not AI_REPLY:
        raise SystemExit("请先在 AI_REPLY 中粘入大模型返回的用例 JSON")

    lines = [
        "import pytest, requests, json, os",
        "from utils.aiMakecase.model_config import DEFAULT_APP_ID, DEFAULT_APP_SECRET, DEFAULT_BASE_URL",
        "",
        "BASE_URL = os.getenv('FEISHU_BASE_URL', DEFAULT_BASE_URL)",
        "APP_ID = os.getenv('FEISHU_APP_ID', DEFAULT_APP_ID)",
        "APP_SECRET = os.getenv('FEISHU_APP_SECRET', DEFAULT_APP_SECRET)",
        "if not APP_ID or not APP_SECRET:",
        "    raise RuntimeError('缺少 FEISHU_APP_ID / FEISHU_APP_SECRET 环境变量，且未在 model_config 中配置默认值')",
        "",
        "def _get_token():",
        "    url = f\"{BASE_URL}/auth/v3/tenant_access_token/internal\"",
        "    headers = {'Content-Type': 'application/json; charset=utf-8'}",
        "    payload = {'app_id': APP_ID, 'app_secret': APP_SECRET}",
        "    resp = requests.post(url, json=payload, headers=headers, timeout=10)",
        "    resp.raise_for_status()",
        "    data = resp.json()",
        "    if data.get('code') != 0:",
        "        raise RuntimeError(f\"get token failed: {data}\")",
        "    return data.get('tenant_access_token')",
        "",
        "TOKEN = None",
        "",
        "def _headers(extra=None):",
        "    global TOKEN",
        "    if not TOKEN:",
        "        TOKEN = _get_token()",
        "    base = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json; charset=utf-8'}",
        "    if extra:",
        "        base.update(extra)",
        "    return base",
        "",
        f"DEFAULT_PATH = '{DEFAULT_PATH}'",
    ]

    for idx, case in enumerate(AI_REPLY, 1):
        tn = f"test_ai_case_{idx}"
        lines.append(f\"\n\ndef {tn}():\")
        lines.append(f\"    \\\"\\\"\\\"{case.get('name','')} - {case.get('description','')}\\\"\\\"\\\"\")
        req_json = json.dumps(case.get('request_data', {}), ensure_ascii=False)
        req_json = req_json.replace("true", "True").replace("false", "False").replace("null", "None")
        exp_json = json.dumps(case.get('expected_response', {}), ensure_ascii=False)
        exp_json = exp_json.replace("true", "True").replace("false", "False").replace("null", "None")
        lines.append(f"    raw_req = {req_json}")
        lines.append(f"    expected_status = {case.get('expected_status_code', 200)}")
        lines.append(f"    expected_resp = {exp_json}")
        lines.append("    req_body = raw_req.get('body', raw_req if isinstance(raw_req, dict) else {})")
        lines.append("    req_query = raw_req.get('query_params', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    req_method = raw_req.get('method') if isinstance(raw_req, dict) else None")
        lines.append("    req_url = raw_req.get('url') if isinstance(raw_req, dict) else None")
        lines.append("    req_headers = raw_req.get('headers', {}) if isinstance(raw_req, dict) else {}")
        lines.append("    method_use = (req_method or 'POST').upper()")
        lines.append("    url = req_url or f\"{BASE_URL}{DEFAULT_PATH}\"")
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

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] 生成 {OUT_FILE}, 用例数: {len(AI_REPLY)}")


if __name__ == '__main__':
    main()