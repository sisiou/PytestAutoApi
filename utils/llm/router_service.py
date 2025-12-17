# utils/llm/router_service.py
from __future__ import annotations

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from utils.llm.bailian_client import build_bailian_chat_llm
from utils.llm.agent_router import run_router_with_tools
from utils.llm.tools_feishu import build_feishu_tools

from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()
ACCESS_KEY = os.getenv("DASHSCOPE_API_KEY")
BAILIAN_API_URL = os.getenv("BAILIAN_API_URL")
BAILIAN_MODEL = os.getenv("BAILIAN_MODEL")

def run_ai_test_router(
    *,
    project_root: Path,
    action: str,  # "generate" | "execute" | "genexec"
    base_name: str,
    force_regenerate: bool = False,
    timeout_sec: int = 600,
    files: Optional[Dict[str, str]] = None,
    # 百炼配置
    ACCESS_KEY: str = "",
    BAILIAN_API_URL: str = "",
    BAILIAN_MODEL: str = "",
    file_path: str = "",
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    单一职责：构建 llm+tools，触发 router_agent，返回工具最终结果。
    """
    llm = build_bailian_chat_llm(
        ACCESS_KEY=ACCESS_KEY,
        BAILIAN_API_URL=BAILIAN_API_URL,
        BAILIAN_MODEL=BAILIAN_MODEL,
    )

    # 注册工具
    tools = []
    tools += build_feishu_tools(
        project_root=project_root,
        ACCESS_KEY=ACCESS_KEY,
        BAILIAN_API_URL=BAILIAN_API_URL,
        BAILIAN_MODEL=BAILIAN_MODEL,
    )

    # 测试
    payload = {
        "request": {
            "action": action,
            "base_name": base_name,
            "force_regenerate": force_regenerate,
            "file_path": file_path,
            "timeout_sec": timeout_sec,
        },
        "files": files or {},
    }

    # 触发 router_agent → 工具流程（tool-calling loop）
    return run_router_with_tools(llm, tools, payload, max_iterations=5, verbose=verbose)

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    with open('../../uploads/openapi/openapi_feishu_server-docs_im-v1_message_create.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    files = {
        "openapi.yaml": data,
    }
    print(files)

    result = run_ai_test_router(
        project_root = project_root,
        # "generate" | "execute" | "genexec"
        action="generate",
        base_name="飞书发送消息测试",
        force_regenerate=False,
        timeout_sec=600,
        files = files,
        file_path = '/test/path',
        ACCESS_KEY=ACCESS_KEY,
        BAILIAN_API_URL=BAILIAN_API_URL,
        BAILIAN_MODEL=BAILIAN_MODEL,
        verbose=True,
    )

    print(result)