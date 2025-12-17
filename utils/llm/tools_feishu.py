# utils/llm/tools_feishu.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_core.tools import StructuredTool

from utils.llm.schemas import GenerateArgs, ExecuteArgs, GenExecArgs
from utils.llm.bailian_client import call_bailian_api

def build_feishu_tools(
    *,
    project_root: Path,
    # 传入百炼配置，便于“飞书场景增强”时直接调用模型做 YAML 增强/补全
    ACCESS_KEY: str,
    BAILIAN_API_URL: str,
    BAILIAN_MODEL: str,
):
    # 通用飞书测试用例生成
    def _generate_feishu(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,
                         ) -> Dict[str, Any]:
        """
        飞书场景生成：当前先复用通用生成，后续你在这里做“场景化增强”：
        """

        # 调用通用的测试用例生成
        # res = generate_yaml_and_convert_pytest(
        #     project_root=project_root,
        #     base_name=args.base_name,
        #     force_regenerate=args.force_regenerate,
        # )
        # return res
        return {"result": "通用飞书测试用例生成", "file_path": file_path}

    # 飞书发送消息测试用例生成
    def _generate_feishu_message(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,
                                 ) -> Dict[str, Any]:
        """
        飞书场景生成：当前先复用通用生成，后续你在这里做“场景化增强”：
        """
        # 调用通用的测试用例生成
        # res = generate_yaml_and_convert_pytest()
        # return res
        return {"result": "飞书发送消息测试用例生成", "file_path": file_path}

    # 飞书日历测试用例生成
    def _generate_feishu_calendar(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,
                                  ) -> Dict[str, Any]:
        # 调用通用的测试用例生成
        # return res
        return {"result": "飞书日志相关测试用例生成", "file_path": file_path}

    # 通用飞书执行测试用例
    def _execute_feishu(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,
                            ) -> Dict[str, Any]:
        # 调用执行测试用例代码
        #
        # return res
        return {"result": "通用飞书测试用例执行", "file_path": file_path}

    # 飞书发送消息执行测试用例
    def _execute_feishu_message(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,) -> Dict[str, Any]:
        return {"result": "飞书发送消息执行测试用例", "file_path": file_path}

    # 飞书日历执行测试用例
    def _execute_feishu_calendar(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,) -> Dict[str, Any]:
        return {"result": "飞书日历执行测试用例", "file_path": file_path}

    def _genexec_feishu(base_name: str,
        file_path: str = "",
        files: dict | None = None,
        force_regenerate: bool = False,) -> Dict[str, Any]:
        gen = '生成测试用例'
        exe = '执行测试用例'
        return {"result": "飞书生成并执行测试用例", "generation_result": gen, "execution_result": exe, "file_path": file_path}

    return [
        StructuredTool.from_function(
            name="generate_test_cases_feishu",
            description="生成用例: 飞书通用场景",
            func=_generate_feishu,
            args_schema=GenerateArgs,
        ),
        StructuredTool.from_function(
            name="generate_test_cases_feishu_message",
            description="生成用例: 飞书发送消息场景",
            func=_generate_feishu_message,
            args_schema=GenerateArgs,
        ),
        StructuredTool.from_function(
            name="generate_test_cases_feishu_calendar",
            description="生成用例: 飞书日历场景",
            func=_generate_feishu_calendar,
            args_schema=GenerateArgs,
        ),
        StructuredTool.from_function(
            name="execute_test_cases_feishu",
            description="执行用例: 飞书通用场景",
            func=_execute_feishu,
            args_schema=ExecuteArgs,
        ),
        StructuredTool.from_function(
            name="execute_test_cases_feishu_message",
            description="执行用例: 飞书发送消息场景",
            func=_execute_feishu_message,
            args_schema=ExecuteArgs,
        ),
        StructuredTool.from_function(
            name="execute_test_cases_feishu_calendar",
            description="执行用例: 飞书日历场景",
            func=_execute_feishu_calendar,
            args_schema=ExecuteArgs,
        ),
        StructuredTool.from_function(
            name="generate_and_execute_feishu",
            description="生成并执行测试用例: 飞书通用场景",
            func=_genexec_feishu,
            args_schema=GenExecArgs,
        ),
    ]
