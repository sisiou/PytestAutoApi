#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书授权码 (code) 获取工具。

运行脚本后会直接输出带有必填三项参数（client_id、response_type=code、redirect_uri）的授权链接，
无需任何额外输入，可立即复制到浏览器中打开，完成授权并获取 code。
"""

from urllib.parse import urlencode, quote
from typing import Optional

FEISHU_AUTH_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"

# 必填参数写死在代码中，请根据实际情况修改这两个常量
FEISHU_CLIENT_ID = "cli_a9ac1b6a23b99bc2"  # 示例 App ID，请替换为你自己的 App ID
FEISHU_REDIRECT_URI = "http://localhost:8000/feishu_callback.html"  # 示例 redirect_uri，请替换为你自己的回调地址


def build_feishu_authorize_url(
    client_id: str,
    redirect_uri: str,
    scope: Optional[str] = None,
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
) -> str:
    """
    构造飞书授权页 URL。

    用户在浏览器中访问该 URL 并同意授权后，浏览器会跳转到：
        redirect_uri?code=xxx&state=xxx
    或当用户拒绝授权时：
        redirect_uri?error=access_denied&state=xxx

    参数说明与飞书官方文档保持一致：
    - client_id: 应用的 App ID。
    - redirect_uri: 需要在飞书开放平台「安全设置」中配置过的回调地址（需 URL 编码）。
    - scope: 空格分隔的权限 scope 字符串，例如 "bitable:app:readonly contact:contact"。
    - state: 用于防 CSRF 的随机字符串，会原样回传。
    - code_challenge / code_challenge_method: PKCE 模式相关参数。
    """
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
    }
    if scope:
        params["scope"] = scope
    if state:
        params["state"] = state
    if code_challenge:
        params["code_challenge"] = code_challenge
        if code_challenge_method:
            params["code_challenge_method"] = code_challenge_method

    query = urlencode(params, quote_via=quote)
    return f"{FEISHU_AUTH_URL}?{query}"


def main() -> None:
    """直接输出使用必填三项生成的授权链接。"""
    url = build_feishu_authorize_url(
        client_id=FEISHU_CLIENT_ID,
        redirect_uri=FEISHU_REDIRECT_URI,
    )

    print("=== 飞书授权页 URL（仅包含必填参数）===")
    print(url)
    print("\n请将上述链接复制到浏览器中打开，完成授权后即可在回调地址中获取 code。")


if __name__ == "__main__":
    main()
