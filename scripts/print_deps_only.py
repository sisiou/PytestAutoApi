#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
仅查看依赖关系与 external_params（不调用模型、不跑 pytest）。
运行方式与 chain_full_runner 相同的流程段：解析 relation -> 过滤 only-file -> 遍历文件打印 external_params。
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.chain_relation_runner import build_graph, topo_sort  # noqa: E402
from scripts.chain_full_runner import fetch_external_params, build_chain_field_map  # noqa: E402


# ======= 可按需修改的默认参数 =======
API_DIR = "multiuploads/split_openapi/openapi_API/related_group_4"
RELATION_DIR = "uploads/relation"
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CHAIN_REDIS_URL") or "redis://127.0.0.1:6379/0"  # 如不需要 Redis 注入，设为 None 或空字符串
# 逗号分隔的文件列表，留空则全量
ONLY_FILE = ""
# ==================================


def main():
    api_dir = Path(API_DIR)
    rel_dir = Path(RELATION_DIR)

    nodes, edges, rel_map = build_graph(rel_dir, api_dir)
    order = topo_sort(nodes, edges)
    print(f"order: {order}")
    print(f"rel_map: {rel_map}")
    if ONLY_FILE:
        wanted = {x.strip() for x in ONLY_FILE.split(",") if x.strip()}
        order = [f for f in order if f in wanted]
        if not order:
            raise SystemExit(f"未匹配到指定文件: {ONLY_FILE}")

    print("[ORDER]", " -> ".join(order))
    print("[REL_MAP]")
    for tgt, pairs in rel_map.items():
        for pair in pairs:
            for rp in pair.get("relation_params", []):
                print(
                    f"  {pair.get('source_openapi_file')} -> {pair.get('target_openapi_file')}: "
                    f"{rp.get('source_param')} -> {rp.get('target_param')} (loc: {rp.get('param_location')})"
                )

    redis_client = None
    if REDIS_URL:
        try:
            import redis
            redis_client = redis.from_url(REDIS_URL)
        except Exception as exc:
            raise SystemExit(f"连接 Redis 失败: {exc}")

    print("\n[EXTERNAL_PARAMS]")
    for fname in order:
        if not (api_dir / fname).exists():
            print(f"  {fname}: (文件不存在，跳过)")
            continue
        external_params = fetch_external_params(redis_client, fname, rel_map)
        print(f"  {fname}: {external_params}")
        # 额外打印将写入 Redis 的字段映射，便于对照
        fmap = build_chain_field_map(fname, rel_map.get(fname, []))
        if fmap:
            print(f"    write_map: {json.dumps(fmap, ensure_ascii=False)}")


if __name__ == "__main__":
    main()

