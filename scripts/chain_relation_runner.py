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
from typing import Dict, List, Any, Tuple, Optional

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

    def find_create_file_for_target(target_file: str, api_files: List[str]) -> str:
        """
        为目标接口查找对应的 create 接口文件。
        
        策略：
        1. 通过文件名替换（reply -> create, forward -> create, update -> create）
        2. 如果替换失败，搜索包含 create 和相同业务模块的文件
        """
        # 策略1: 文件名替换
        replacements = [
            ("reply", "create"),
            ("forward", "create"),
            ("update", "create"),
        ]
        for old, new in replacements:
            if old in target_file:
                candidate = target_file.replace(old, new)
                if candidate in api_files:
                    return candidate
        
        # 策略2: 提取业务模块前缀，搜索 create 文件
        # 例如: openapi_feishu_server-docs_im-v1_message_reply.yaml
        # 提取: feishu_server-docs_im-v1_message
        parts = target_file.replace("openapi_", "").replace(".yaml", "").split("_")
        if len(parts) >= 2:
            # 找到最后一个包含操作类型的部分（reply/forward/update）
            module_parts = []
            for part in parts:
                if part in ["reply", "forward", "update", "create"]:
                    break
                module_parts.append(part)
            if module_parts:
                module_prefix = "_".join(module_parts)
                create_files = [f for f in api_files if module_prefix in f and "create" in f]
                if create_files:
                    return create_files[0]
        
        # 策略3: 通用搜索（包含 create 和 message 的文件）
        create_files = [f for f in api_files if "create" in f and "message" in f]
        if create_files:
            return create_files[0]
        
        return None

    def infer_dependency_from_self_loop(src_file: str, tgt_file: str, pair: Dict[str, Any], 
                                       rf: Path, api_files: List[str], api_dir: Path) -> Tuple[Optional[str], bool]:
        """
        从自环推断正确的依赖关系。
        
        返回: (corrected_source_file, success)
        - corrected_source_file: 修正后的源文件（如果推断成功）
        - success: 是否成功推断
        """
        # 获取 relation 描述和 API 路径，用于推断依赖关系
        relation_desc = pair.get("relation_desc", "")
        target_api_path = pair.get("target_api_path", "").lower()
        
        # 检查是否提到"发送消息"接口（create）
        mentions_create = "发送消息" in relation_desc or "create" in relation_desc.lower()
        
        # 检查 target 是否是 reply/forward/update，这些通常依赖 create
        is_reply = "reply" in tgt_file.lower() or "/reply" in target_api_path
        is_forward = "forward" in tgt_file.lower() or "/forward" in target_api_path
        is_update = "update" in tgt_file.lower() or "/update" in target_api_path or "(put)" in target_api_path
        
        # 如果满足条件，尝试将 source 设置为 create
        if (is_reply or is_forward or is_update) and mentions_create:
            create_candidate = find_create_file_for_target(tgt_file, api_files)
            
            if create_candidate and (api_dir / create_candidate).exists():
                print(f"[INFO] 自动推断依赖关系: {create_candidate} -> {tgt_file} (基于 relation 描述)")
                return create_candidate, True
            else:
                # 无法推断，跳过自环依赖
                print(f"[WARN] 跳过自环依赖: {src_file} -> {tgt_file} (relation文件: {rf.name})")
                print(f"      提示: 应该依赖 create 接口，但未找到对应的 create 文件")
                return None, False
        else:
            # 无法推断，跳过自环依赖（接口不应该依赖自己）
            print(f"[WARN] 跳过自环依赖: {src_file} -> {tgt_file} (relation文件: {rf.name})")
            if not mentions_create:
                print(f"      提示: relation 描述中未提到'发送消息'接口，无法推断依赖关系")
            else:
                print(f"      提示: 请检查 relation 文件配置，确保 source_openapi_file 和 target_openapi_file 指向不同的接口")
            return None, False

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
                    # 只匹配到一个文件时，先设置为自环，后续在自环检测阶段尝试推断正确的依赖关系
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

            # 如果是自环，尝试应用启发式规则推断正确的依赖关系
            if src_file == tgt_file:
                corrected_source, success = infer_dependency_from_self_loop(
                    src_file, tgt_file, pair, rf, api_files, api_dir
                )
                if success:
                    src_file = corrected_source
                    pair["source_openapi_file"] = src_file
                else:
                # 推断失败，跳过自环依赖
                    continue

            # 判断是否是有效的依赖关系：必须同时有 source_param（输出参数）和 target_param（输入参数）
            relation_params = pair.get("relation_params", [])
            has_valid_params = False
            if relation_params:
                for rp in relation_params:
                    source_param = rp.get("source_param")
                    target_param = rp.get("target_param")
                    # source_param 是输出参数（从 source 接口响应中获取）
                    # target_param 是输入参数（作为 target 接口的输入）
                    if source_param and target_param:
                        has_valid_params = True
                        break
            
            if not has_valid_params:
                # 没有有效的参数映射，跳过这条依赖关系
                print(f"[WARN] 跳过无效依赖关系: {src_file} -> {tgt_file} (relation文件: {rf.name})")
                print(f"      提示: relation_params 中缺少有效的 source_param（输出参数）或 target_param（输入参数）")
                continue

            nodes.add(src_file)
            nodes.add(tgt_file)
            edges[src_file].append(tgt_file)
            rel_map[tgt_file].append(pair)
            printed_relations.append((src_file, tgt_file, relation_params))

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

