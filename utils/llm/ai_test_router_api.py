# routes/ai_test_router_api.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

from utils.llm.router_service import run_ai_test_router

bp_ai_router = Blueprint("bp_ai_router", __name__)


def _get_project_root() -> Path:
    """
    返回项目根目录（按你项目结构：routes/ 在根目录下，或根据实际调整 parents 层级）。
    更稳的方式：使用你之前的 _resolve_project_root() 向上探测。
    """
    return Path(__file__).resolve().parents[2]


def _read_uploaded_files_as_text() -> Dict[str, str]:
    """
    从 multipart/form-data 读取上传的文件，返回 {filename: text_content}。
    """
    files_map: Dict[str, str] = {}
    for f in request.files.getlist("files"):
        filename = f.filename or "uploaded_file"
        content = f.read().decode("utf-8", errors="replace")
        files_map[filename] = content
    return files_map


@bp_ai_router.route("/api/feishu/ai-test-router", methods=["POST"])
def ai_test_router_api():
    """
    一个统一入口：前端传 action/base_name/files 等，后端调用 run_ai_test_router 完成路由与执行。
    支持 JSON 和 multipart/form-data 两种方式。
    """
    try:
        load_dotenv()
        ACCESS_KEY = os.getenv("DASHSCOPE_API_KEY", "")
        BAILIAN_API_URL = os.getenv("BAILIAN_API_URL", "")
        BAILIAN_MODEL = os.getenv("BAILIAN_MODEL", "")

        project_root = _get_project_root()

        # ========== 1) 解析入参 ==========
        action = ""
        base_name = ""
        force_regenerate = False
        timeout_sec = 600
        file_path = ""          # 可选：原始文件路径标识（前端可不传）
        verbose = False
        files: Dict[str, str] = {}

        # ---- A. JSON 方式 ----
        if request.is_json:
            data = request.get_json(silent=True) or {}
            action = (data.get("action") or "").strip()
            base_name = (data.get("base_name") or "").strip()
            force_regenerate = bool(data.get("force_regenerate", False))
            timeout_sec = int(data.get("timeout_sec", 600))
            file_path = (data.get("file_path") or "").strip()
            verbose = bool(data.get("verbose", False))

            # 关键：files 必须是 “文件名 -> 文件文本内容”
            files = data.get("files") or {}
            if not isinstance(files, dict):
                return jsonify({"error": "invalid_files", "message": "files 必须是对象: {filename: content}"}), 400

        # ---- B. multipart/form-data 方式 ----
        else:
            form = request.form or {}
            action = (form.get("action") or "").strip()
            base_name = (form.get("base_name") or "").strip()
            force_regenerate = (form.get("force_regenerate", "false").lower() == "true")
            timeout_sec = int(form.get("timeout_sec", "600"))
            file_path = (form.get("file_path") or "").strip()
            verbose = (form.get("verbose", "false").lower() == "true")

            files = _read_uploaded_files_as_text()

        # ========== 2) 基础校验 ==========
        if action not in {"generate", "execute", "genexec"}:
            return jsonify({"error": "invalid_action", "message": "action 必须是 generate/execute/genexec"}), 400
        if not base_name:
            return jsonify({"error": "missing_base_name", "message": "缺少 base_name"}), 400

        # ========== 3) 调用 router ==========
        result = run_ai_test_router(
            project_root=project_root,
            action=action,
            base_name=base_name,
            force_regenerate=force_regenerate,
            timeout_sec=timeout_sec,
            # 你如果在 run_ai_test_router 内部使用 file_path，可传进去（否则可忽略）
            # test_file_path=... (execute 时可加)
            files=files,

            ACCESS_KEY=ACCESS_KEY,
            BAILIAN_API_URL=BAILIAN_API_URL,
            BAILIAN_MODEL=BAILIAN_MODEL,
            verbose=verbose,
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "ai_test_router_failed", "message": str(e)}), 500
