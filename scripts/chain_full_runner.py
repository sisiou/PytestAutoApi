#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
串行执行整条链路：
1) 解析 relation_* 计算执行顺序（拓扑）
2) 按顺序调用 message_ai_prompt 生成 pytest 用例
3) 运行 pytest，自动把响应字段写入 Redis
4) 下一个接口运行前，从 Redis 读取依赖字段作为 external_params 注入

前置：
- 需准备 relation_*.json 与 openapi_*.yaml
- 需配置 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_BASE_URL（请求时使用）
- 若需依赖注入，提供 Redis 地址（可本地）：
  CHAIN_REDIS_URL=redis://127.0.0.1:6379/0

运行示例：
python scripts/chain_full_runner.py \
  --api-dir multiuploads/split_openapi/openapi_API/related_group_4 \
  --relation-dir uploads/relation \
  --redis-url redis://127.0.0.1:6379/0 \
  --api-key $DASHSCOPE_API_KEY \
  --model deepseek-v3.2 \
  --tmp-dir .chain_out
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from utils.other_tools.config.model_config import (
    DEFAULT_API_KEY,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 复用已有解析能力
from scripts.chain_relation_runner import build_graph, topo_sort  # noqa: E402
from utils.aiMakecase.message_ai_prompt import (  # noqa: E402
    generate_case_with_llm,
    generate_pytest_from_cases,
    _extract_json,
    _parse_openapi_head_text,
)


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"读取文件失败: {path} -> {exc}")


def build_chain_field_map(source_file: str, relations: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    为当前 source_file 生成写入 Redis 的字段映射。
    key: target_param
    value: {"path": "data.xxx", "target_param": "<target_param>"}
    """
    fmap: Dict[str, Dict[str, str]] = {}
    for pair in relations:
        if pair.get("source_openapi_file") != source_file:
            continue
        for rp in pair.get("relation_params", []):
            target_param = rp.get("target_param") or rp.get("source_param")
            source_param = rp.get("source_param") or target_param
            if not target_param or not source_param:
                continue
            # 默认从 data.<source_param> 取值，若模型响应结构不同，可在 relation 中改为带点路径
            if "." in source_param:
                path = source_param  # 已包含路径
            else:
                path = f"data.{source_param}"
            fmap[target_param] = {"path": path, "target_param": target_param}
    return fmap


def _get_by_path(obj: Any, path: str) -> Any:
    """支持点路径取值，若不存在返回 None。"""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                idx = int(part)
                cur = cur[idx]
            except Exception:
                return None
        else:
            return None
        if cur is None:
            return None
    return cur


def _decode(val: Any) -> Any:
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except Exception:
            return val
    return val


def fetch_external_params(redis_client, target_file: str, rel_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    针对 target_file，读取它依赖的参数，返回 external_params。
    当前存储：key 为 pytest 文件名（例如 test_chain_x.py），value 为接口响应 JSON 字符串。
    为兼容旧配置，依旧尝试多种 key 形式。
    """
    external: Dict[str, Any] = {}
    if not redis_client:
        return external

    pairs = rel_map.get(target_file, [])
    for pair in pairs:
        src = pair.get("source_openapi_file")
        if not src:
            continue
        stem = Path(src).stem
        candidate_keys = [
            f"test_chain_{stem}.py",
            f"{stem}.py",
            src,
        ]
        raw_val = None
        for k in candidate_keys:
            raw_val = redis_client.get(k)
            if raw_val is not None:
                break
        if raw_val is None:
            print(f"[WARN] 未找到依赖响应，Redis keys 尝试: {candidate_keys}")
            continue

        raw_val = _decode(raw_val)
        try:
            resp_json = json.loads(raw_val)
        except Exception:
            print(f"[WARN] Redis 响应不可解析为 JSON，key候选={candidate_keys}, 片段={str(raw_val)[:200]}")
            continue

        for rp in pair.get("relation_params", []):
            target_param = rp.get("target_param") or rp.get("source_param")
            source_param = rp.get("source_param") or target_param
            if not target_param or not source_param:
                continue
            # 支持 relation 中自定义路径，否则默认 data.<source_param>
            path = rp.get("source_param_path")
            if not path:
                path = source_param if "." in source_param else f"data.{source_param}"
            val = _get_by_path(resp_json, path)
            if val is None:
                print(f"[WARN] 依赖字段缺失 path={path} key候选={candidate_keys}")
                continue
            external[target_param] = val
    return external


def run_pytest(py_path: Path, env: Dict[str, str]):
    cmd = [sys.executable, "-m", "pytest", str(py_path)]
    print(f"[RUN] {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=ROOT, env=env)
    if res.returncode != 0:
        raise RuntimeError(f"pytest 失败: {py_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", required=True, help="openapi_*.yaml 所在目录")
    parser.add_argument("--relation-dir", required=True, help="relation_*.json 所在目录")
    parser.add_argument("--tmp-dir", default=".chain_out", help="生成 pytest 的临时目录")
    parser.add_argument("--redis-url", help="Redis 连接串，若不提供则尝试环境变量 CHAIN_REDIS_URL，否则不做依赖注入")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="大模型 API Key，默认取环境变量 DASHSCOPE_API_KEY/DEFAULT_API_KEY")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"大模型名称，默认 {DEFAULT_MODEL}")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="大模型网关 base_url，默认兼容 dashscope")
    parser.add_argument("--stream", action="store_true", help="是否流式输出模型（默认关闭以便解析 JSON）")
    parser.add_argument("--only-file", help="只处理特定 openapi 文件，逗号分隔文件名，如 openapi_x.yaml,openapi_y.yaml")
    parser.add_argument("--skip-pytest", action="store_true", help="仅生成用例，不执行 pytest（用于调试生成逻辑）")
    args = parser.parse_args()

    # 兜底从环境变量再尝试一次，避免默认值在调用时为空
    if not args.api_key:
        fallback_key = (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("DEFAULT_API_KEY")
            or DEFAULT_API_KEY
        )
        if not fallback_key:
            raise SystemExit("缺少 API Key，请传入 --api-key 或设置环境变量 DASHSCOPE_API_KEY")
        args.api_key = fallback_key

    # Redis URL 环境兜底
    if not args.redis_url:
        args.redis_url = os.getenv("REDIS_URL")

    api_dir = Path(args.api_dir)
    rel_dir = Path(args.relation_dir)
    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    nodes, edges, rel_map = build_graph(rel_dir, api_dir)
    order = topo_sort(nodes, edges)
    if args.only_file:
        wanted = {x.strip() for x in args.only_file.split(",") if x.strip()}
        order = [f for f in order if f in wanted]
        if not order:
            raise SystemExit(f"未匹配到指定文件: {args.only_file}")
    print("执行顺序:", " -> ".join(order))

    # 反查表：source_file -> relations where it is source
    outgoing: Dict[str, List[Dict[str, Any]]] = {}
    for tgt, pairs in rel_map.items():
        for pair in pairs:
            src = pair.get("source_openapi_file")
            if not src:
                continue
            outgoing.setdefault(src, []).append(pair)

    redis_client = None
    if args.redis_url:
        try:
            import redis
            redis_client = redis.from_url(args.redis_url)
        except Exception as exc:
            raise SystemExit(f"连接 Redis 失败: {exc}")

    for fname in order:
        openapi_path = api_dir / fname
        if not openapi_path.exists():
            print(f"[WARN] 找不到 OpenAPI 文件，跳过: {openapi_path}")
            continue

        print(f"\n=== 处理 {fname} ===")
        print(f"openapi_path: {openapi_path}")
        print(f"fname: {fname}")
        print(f"rel_map: {rel_map}")
        openapi_text = load_text(openapi_path)

        # 读取依赖注入参数
        external_params = fetch_external_params(redis_client, fname, rel_map)
        print(f"external_params: {external_params}")
        if external_params:
            print(f"[INFO] external_params: {external_params}")

        # 调用模型生成用例
        resp = generate_case_with_llm(
            openapi_path=str(openapi_path),
            api_key=args.api_key,
            model=args.model,
            base_url=args.base_url,
            stream=args.stream,
            external_params=external_params or None,
        )

        cases_json = _extract_json(resp)
        if not cases_json:
            raise RuntimeError(f"模型返回无法解析为 JSON: {fname}")
        cases = cases_json if isinstance(cases_json, list) else [cases_json]

        api_info = _parse_openapi_head_text(openapi_text)
        out_py = tmp_dir / f"test_chain_{openapi_path.stem}.py"

        # 配置写入 Redis 的环境变量
        env = os.environ.copy()
        if redis_client:
            fmap = build_chain_field_map(fname, outgoing.get(fname, []))
            if fmap:
                env["CHAIN_REDIS_URL"] = args.redis_url
                env["CHAIN_TARGET_FILE"] = fname
                env["CHAIN_FIELD_MAP"] = json.dumps(fmap, ensure_ascii=False)
                print(f"[INFO] 将写入 Redis 字段: {list(fmap.keys())}")

        # 生成 pytest 并执行
        generate_pytest_from_cases(cases, api_info, out_py)
        if args.skip_pytest:
            print(f"[SKIP] 已生成 pytest 文件，调试模式跳过执行: {out_py}")
        else:
            run_pytest(out_py, env)

    print("\n[OK] 链路执行完成")


if __name__ == "__main__":
    main()

