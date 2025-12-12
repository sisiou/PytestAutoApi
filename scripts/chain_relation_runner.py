#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
解析 relation 文件，自动计算执行顺序，仅输出依赖关系（不写入 Redis）。

使用示例：
python scripts/chain_relation_runner.py \
  --api-dir multiuploads/split_openapi/openapi_API/related_group_4 \
  --relation-dir uploads/relation \
说明：
- 通过 relation 文件自动推导顺序（拓扑排序），不写死 create/reply 先后。
- 只解析并打印依赖，不做请求，也不写入 Redis。
"""
import argparse
import json
import os
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Any, Tuple

def load_relation_file(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"无法读取 relation 文件 {path}: {exc}")


def json_get(data: Dict[str, Any], path: str):
    """支持用 dot 路径访问，如 data.calendar.calendar_id"""
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def build_graph(rel_dir: Path, api_dir: Path):
    """
    从 relation 目录构建依赖图：
    节点：OpenAPI 文件名（不含路径）
    边：source -> target
    """
    rel_files = list(rel_dir.glob("relation_*.json"))
    if not rel_files:
        raise RuntimeError(f"未在 {rel_dir} 找到 relation_*.json")

    nodes = set()
    edges = defaultdict(list)
    rel_map = defaultdict(list)  # target_file -> list of relations needing it

    # 收集关系，便于打印
    printed_relations = []

    api_files = [p.name for p in api_dir.glob("openapi_*.yaml")]

    def match_by_relation_filename(rf: Path):
        """
        relation_xxx.json -> 尝试匹配同名 openapi 文件
        例如 relation_feishu_server-docs_im-v1_message_create.json
        对应 openapi_feishu_server-docs_im-v1_message_create.yaml
        """
        stem_mid = rf.name.replace("relation_", "").replace(".json", "")
        candidates = [f for f in api_files if stem_mid in f]
        return candidates

    for rf in rel_files:
        data = load_relation_file(rf)
        for pair in data.get("related_pairs", []):
            src = pair.get("source_openapi_file")
            tgt = pair.get("target_openapi_file")
            if not src or not tgt:
                continue
            # relation 文件里有时用 data.json 占位，这里放宽：
            # 1) 若 api_dir 存在同名文件，精确匹配
            if (api_dir / src).exists() and (api_dir / tgt).exists():
                src_file, tgt_file = src, tgt
            else:
                # 2) 尝试根据 relation 文件名匹配 openapi 文件
                candidates = match_by_relation_filename(rf)
                if len(candidates) == 1:
                    # 只匹配到一个文件时，如果 source 和 target 都是 data.json，说明可能是自环
                    # 这种情况下，如果 relation 描述中提到需要从其他接口获取参数，应该跳过
                    if src == "data.json" and tgt == "data.json":
                        print(f"[WARN] 跳过可能的自环依赖: relation文件 {rf.name} 中 source 和 target 都是 data.json")
                        print(f"      匹配到的文件: {candidates[0]}")
                        print(f"      提示: 请检查 relation 文件配置，确保 source_openapi_file 和 target_openapi_file 指向不同的接口")
                        continue
                    src_file = tgt_file = candidates[0]
                elif len(candidates) == 2:
                    # 若存在 create + reply 的组合，则默认 create -> reply
                    create_files = [c for c in candidates if "create" in c]
                    reply_files = [c for c in candidates if "reply" in c]
                    if create_files and reply_files:
                        src_file = create_files[0]
                        tgt_file = reply_files[0]
                    else:
                        # 否则取首两个
                        src_file, tgt_file = candidates[0], candidates[1]
                else:
                    # 匹配不到则跳过本条关系
                    continue

            # 用匹配结果回写到 pair，便于后续使用正确的 openapi 文件名
            pair["source_openapi_file"] = src_file
            pair["target_openapi_file"] = tgt_file

            # 如果是自环，尝试应用启发式：reply 默认依赖 create
            if src_file == tgt_file:
                if "reply" in tgt_file:
                    create_candidate = tgt_file.replace("reply", "create")
                    if (api_dir / create_candidate).exists():
                        src_file = create_candidate  # rewrite edge create -> reply
                        # tgt_file remains reply
                        pair["source_openapi_file"] = src_file
                    else:
                        # 无法推断，跳过自环依赖（接口不应该依赖自己）
                        print(f"[WARN] 跳过自环依赖: {src_file} -> {tgt_file} (relation文件: {rf.name})")
                        print(f"      提示: reply 接口应该依赖 create 接口获取 message_id")
                        continue
                else:
                    # 非 reply 的自环，直接跳过（接口不应该依赖自己）
                    print(f"[WARN] 跳过自环依赖: {src_file} -> {tgt_file} (relation文件: {rf.name})")
                    print(f"      提示: 请检查 relation 文件配置，确保 source_openapi_file 和 target_openapi_file 指向不同的接口")
                    continue

            nodes.add(src_file)
            nodes.add(tgt_file)
            edges[src_file].append(tgt_file)
            rel_map[tgt_file].append(pair)
            printed_relations.append((src_file, tgt_file, pair.get("relation_params", [])))

    # 将 api_dir 下所有 openapi_*.yaml 加入节点（仅为保证节点完整性，不再添加兜底边）
    for n in api_files:
        nodes.add(n)

    # 打印依赖参数映射
    if printed_relations:
        print("检测到的依赖映射：")
        for src, tgt, params in printed_relations:
            for rp in params:
                sp = rp.get("source_param")
                tp = rp.get("target_param")
                loc = rp.get("param_location")
                print(f"  {src} -> {tgt}: {sp} -> {tp} (loc: {loc})")
    else:
        print("未检测到依赖映射（将使用兜底顺序）")

    return nodes, edges, rel_map


def topo_sort(nodes: set, edges: Dict[str, List[str]]) -> List[str]:
    indeg = {n: 0 for n in nodes}
    for src, tgts in edges.items():
        for t in tgts:
            indeg[t] = indeg.get(t, 0) + 1
    q = deque(sorted([n for n, d in indeg.items() if d == 0]))
    order = []
    while q:
        n = q.popleft()
        order.append(n)
        for t in edges.get(n, []):
            indeg[t] -= 1
            if indeg[t] == 0:
                q.append(t)
    if len(order) != len(nodes):
        raise RuntimeError("检测到循环依赖或缺失节点，无法拓扑排序")
    return order


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-dir", required=True, help="OpenAPI 文件所在目录，如 multiuploads/split_openapi/openapi_API/related_group_4")
    parser.add_argument("--relation-dir", required=True, help="relation 文件目录，如 uploads/relation")
    args = parser.parse_args()

    api_dir = Path(args.api_dir)
    rel_dir = Path(args.relation_dir)

    nodes, edges, rel_map = build_graph(rel_dir, api_dir)
    order = topo_sort(nodes, edges)

    # 只输出执行顺序和依赖参数名
    summary = {"order": order, "dependencies": []}
    for tgt, pairs in rel_map.items():
        for pair in pairs:
            for rp in pair.get("relation_params", []):
                summary["dependencies"].append({
                    "source_file": pair.get("source_openapi_file"),
                    "target_file": pair.get("target_openapi_file"),
                    "source_param": rp.get("source_param"),
                    "target_param": rp.get("target_param")
                })

    # 执行顺序
    print(" -> ".join(order))
    # 依赖参数列表
    print(json.dumps(summary["dependencies"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

