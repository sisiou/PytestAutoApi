# utils/llm/agent_router.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import BaseTool

from utils.llm.prompts import ROUTER_SYSTEM_PROMPT


def _safe_json_loads_maybe(x: Any) -> Any:
    if isinstance(x, dict):
        return x
    if not isinstance(x, str):
        return x
    s = x.strip()
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            return x
    return x


def _tool_map(tools: List[BaseTool]) -> Dict[str, BaseTool]:
    return {t.name: t for t in tools}


def run_router_with_tools(
    llm,
    tools: List[BaseTool],
    payload: dict,
    *,
    max_iterations: int = 4,
    verbose: bool = False,
) -> dict:
    tool_by_name = _tool_map(tools)
    req = payload.get("request", {})

    # 绑定工具：让模型以 tool_calls 的形式返回调用意图
    llm_with_tools = llm.bind_tools(tools)

    messages: List[Any] = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]

    last_ai: Optional[AIMessage] = None

    for step in range(max_iterations):
        ai: AIMessage = llm_with_tools.invoke(messages)
        last_ai = ai
        messages.append(ai)

        tool_calls = getattr(ai, "tool_calls", None)

        if verbose:
            print("[router] ai.content=", repr(ai.content))
            print("[router] tool_calls=", tool_calls)

        # 没有工具调用：视为最终输出
        if not tool_calls:
            content = (ai.content or "").strip()
            parsed = _safe_json_loads_maybe(content)
            if isinstance(parsed, dict):
                return parsed
            return {"output": content}

        # 执行所有工具调用，并把结果回灌
        for tc in tool_calls:
            name = tc.get("name")
            args = tc.get("args", {})
            call_id = tc.get("id") or f"{name}_{step}"

            if name not in tool_by_name:
                tool_result = {
                    "error": "tool_not_found",
                    "tool_name": name,
                    "available_tools": list(tool_by_name.keys()),
                }
            else:
                tool = tool_by_name[name]
                args = _safe_json_loads_maybe(args)
                try:
                    # 参数注入
                    args.setdefault("base_name", req.get("base_name"))
                    args.setdefault("force_regenerate", req.get("force_regenerate", False))
                    args.setdefault("file_path", req.get("file_path", ""))
                    tool_result = tool.invoke(args)  # StructuredTool 会自动校验 schema
                except Exception as e:
                    tool_result = {"error": "tool_execute_failed", "tool_name": name, "message": str(e)}

            messages.append(
                ToolMessage(
                    tool_call_id=call_id,
                    content=json.dumps(tool_result, ensure_ascii=False),
                )
            )

    # 超出迭代次数仍未收敛
    if last_ai is None:
        return {"error": "no_response"}
    return {"error": "max_iterations_reached", "output": (last_ai.content or "").strip()}
