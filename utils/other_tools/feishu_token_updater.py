#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据飞书 OAuth 接口使用授权码 code 获取 user_access_token。

期望流程（自动，无需手动复制 URL）：
1. 你在浏览器中访问授权链接并完成授权；
2. 飞书会把浏览器重定向到本地回调地址，例如：
      http://localhost:8000/feishu_callback.html?code=XXX&state=YYY
3. 本脚本作为本地 HTTP 服务监听该回调地址：
   - 打印监听到的完整 URL；
   - 解析 URL 中的 code；
   - 使用 code 自动调用飞书接口换取 user_access_token。
"""

from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

import requests

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"

# ======= 请根据你自己的应用信息修改下面两个常量 =======
FEISHU_CLIENT_ID = "cli_a9ac1b6a23b99bc2"          # 必填：替换为你的 App ID
FEISHU_CLIENT_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"  # 必填：替换为你的 App Secret

# 本地回调服务监听地址，需要和重定向 URL 对应起来
REDIRECT_HOST = "localhost"
REDIRECT_PORT = 8000
REDIRECT_PATH = "/feishu_callback.html"
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}"


def parse_code_from_redirect_url(redirect_url: str) -> Optional[str]:
    """
    从浏览器回调完整 URL 中解析出 code 参数
    例如:
        https://example.com/api/oauth/callback?code=XXX&state=YYY
    """
    parsed = urlparse(redirect_url)
    query = parse_qs(parsed.query)
    codes = query.get("code")
    if not codes:
        return None
    return codes[0]


def get_user_access_token(
    grant_type: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: Optional[str] = None,
    code_verifier: Optional[str] = None,
    scope: Optional[str] = None,
) -> Dict[str, Any]:
    """
    调用飞书获取 user_access_token 接口

    返回完整响应 JSON，包含 user_access_token / refresh_token / expires_in 等字段
    """
    payload: Dict[str, str] = {
        "grant_type": grant_type,
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }
    if redirect_uri:
        payload["redirect_uri"] = redirect_uri
    if code_verifier:
        payload["code_verifier"] = code_verifier
    if scope:
        payload["scope"] = scope

    headers = {"Content-Type": "application/json; charset=utf-8"}

    resp = requests.post(FEISHU_TOKEN_URL, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()

    # 一般会有 access_token 或 user_access_token 字段
    token = data.get("access_token") or data.get("user_access_token")
    if not token:
        raise RuntimeError(f"获取飞书 user_access_token 失败，返回数据中未找到 token 字段: {data}")

    return data


def update_user_info_yaml_with_token(user_access_token: str) -> None:
    """
    将获取到的 user_access_token 写入 data/open-apis/authen/v1/user_info.yaml 的 headers.Authorization 中。

    目标结构示例：
      01_open-apis_authen_v1_user_info:
        headers:
          Authorization: Bearer <user_access_token>
    """
    yaml_path = Path("data/open-apis/authen/v1/user_info.yaml")
    if not yaml_path.exists():
        print(f"[warn] 未找到 YAML 文件: {yaml_path.resolve()}，跳过写入。")
        return

    try:
        import ruamel.yaml  # type: ignore[import]
    except ImportError:
        print("[warn] 未安装 ruamel.yaml，无法自动写入 user_info.yaml，仅在控制台打印 token。")
        return

    yaml = ruamel.yaml.YAML()
    data = yaml.load(yaml_path.read_text(encoding="utf-8")) or {}

    case_key = "01_open-apis_authen_v1_user_info"
    case_conf = data.get(case_key) or {}
    headers = case_conf.get("headers") or {}

    headers["Authorization"] = f"Bearer {user_access_token}"
    case_conf["headers"] = headers
    data[case_key] = case_conf

    # 将更新后的数据写回 YAML 文件
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    print(f"[info] 已将最新 user_access_token 写入 {yaml_path}")


class FeishuOAuthCallbackHandler(BaseHTTPRequestHandler):
    """本地 HTTP 回调处理器：打印监听到的 URL，解析 code，并自动换取 user_access_token。"""

    def do_GET(self) -> None:  # noqa: N802
        # 打印监听到的完整 URL（含路径和查询参数）
        print("=== 收到飞书回调请求 ===")
        print(f"raw path: {self.path}")

        parsed = urlparse(self.path)
        if parsed.path != REDIRECT_PATH:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        # 解析 URL 中的 code / error / state
        query = parse_qs(parsed.query)
        code_list = query.get("code") or []
        error_list = query.get("error") or []
        state_list = query.get("state") or []

        code = code_list[0] if code_list else None
        error = error_list[0] if error_list else None
        state = state_list[0] if state_list else None

        print(f"code:  {code}")
        print(f"error: {error}")
        print(f"state: {state}")

        # 浏览器展示基础信息
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if error:
            html = f"<h1>授权失败</h1><p>error = {error}</p>"
            if state is not None:
                html += f"<p>state = {state}</p>"
            self.wfile.write(html.encode("utf-8"))
            return

        if not code:
            self.wfile.write(
                "<h1>未解析到 code</h1><p>请确认授权是否成功。</p>".encode("utf-8")
            )
            return

        # 使用解析出的 code 调用飞书接口换取 user_access_token
        try:
            token_data = get_user_access_token(
                grant_type="authorization_code",
                client_id=FEISHU_CLIENT_ID,
                client_secret=FEISHU_CLIENT_SECRET,
                code=code,
                redirect_uri=REDIRECT_URI,
            )
        except Exception as e:  # noqa: BLE001
            print(f"获取 user_access_token 失败: {e}", file=sys.stderr)
            self.wfile.write(
                f"<h1>获取 user_access_token 失败</h1><pre>{e}</pre>".encode("utf-8")
            )
            return

        # 在控制台打印完整响应
        print("=== 成功获取 user_access_token 响应 ===")
        print(json.dumps(token_data, ensure_ascii=False, indent=2))

        # 解析 user_access_token，并写入 YAML
        user_access_token = token_data.get("user_access_token") or token_data.get("access_token")
        if user_access_token:
            update_user_info_yaml_with_token(user_access_token)

        # 页面提示成功（不直接把 token 打在页面上，避免泄露）
        expires_in = token_data.get("expires_in")

        html = "<h1>授权成功</h1>"
        if user_access_token:
            html += "<p>user_access_token 已在本地控制台输出。</p>"
            if expires_in is not None:
                html += f"<p>过期时间（秒）：{expires_in}</p>"
        else:
            html += "<p>已收到响应，但未找到 user_access_token 字段，请查看控制台输出。</p>"

        self.wfile.write(html.encode("utf-8"))


def run_callback_server() -> None:
    """启动本地 HTTP 回调服务。"""
    server_addr = (REDIRECT_HOST, REDIRECT_PORT)
    httpd = HTTPServer(server_addr, FeishuOAuthCallbackHandler)

    print("=== 飞书 OAuth 本地回调服务已启动 ===")
    print(f"监听地址: {REDIRECT_URI}")
    print("请确保：")
    print(f"1. 飞书应用『重定向 URL』中已配置：{REDIRECT_URI}")
    print(f"2. 授权链接中的 redirect_uri 与上述地址一致。\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭服务器...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_callback_server()