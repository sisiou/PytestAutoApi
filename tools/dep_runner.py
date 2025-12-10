import json, yaml, requests
from pathlib import Path
from collections import defaultdict, deque

REL_PATH = Path("multiuploads/split_openapi/relation.json")
API_DIR = Path("multiuploads/split_openapi/openapi_API/related_group_1")
OUT_FILE = Path("tests/test_dep_related_group_1.py")
BASE_URL = "https://open.feishu.cn/open-apis"  # 可按需修改

class Edge:
    def __init__(self, src, dst, src_param, dst_param, loc):
        self.src, self.dst = src, dst
        self.src_param, self.dst_param, self.loc = src_param, dst_param, loc

def load_relations():
    data = json.loads(REL_PATH.read_text(encoding="utf-8"))
    edges = []
    for pair in data.get("related_pairs", []):
        src = pair["source_openapi_file"]
        dst = pair["target_openapi_file"]
        for r in pair.get("relation_params", []):
            edges.append(Edge(src, dst, r["source_param"], r["target_param"], r.get("param_location", "path")))
    return edges

def topo(edges):
    g = defaultdict(list); indeg = defaultdict(int); nodes=set()
    for e in edges:
        g[e.src].append(e.dst); indeg[e.dst]+=1; nodes|={e.src,e.dst}
    q=deque([n for n in nodes if indeg[n]==0]); order=[]
    while q:
        n=q.popleft(); order.append(n)
        for v in g[n]:
            indeg[v]-=1
            if indeg[v]==0: q.append(v)
    if len(order)!=len(nodes):
        raise RuntimeError("循环依赖")
    return order

def load_api_yaml(fname):
    y = yaml.safe_load((API_DIR/fname).read_text(encoding="utf-8"))
    # 取第一个 path+method
    paths = y.get("paths", {})
    for p, pdat in paths.items():
        for m, odat in pdat.items():
            if m.lower() in ["get","post","put","delete","patch"]:
                return {
                    "path": p,
                    "method": m.upper(),
                    "reqBody": odat.get("requestBody"),
                    "params": odat.get("parameters", []),
                    "opId": odat.get("operationId", fname.replace('.yaml',''))
                }
    raise RuntimeError(f"未找到路径: {fname}")

def gen_pytest(order, edges):
    binds = defaultdict(list)
    for e in edges:
        binds[e.dst].append(e)
    lines = []
    lines.append("import pytest, requests, json")
    lines.append(f'BASE_URL = "{BASE_URL}"')
    lines.append("ctx = {}  # 存放上游响应")

    def render_call(api):
        p = api["path"]; method = api["method"]
        op = api["opId"]
        # path 参数/查询体分离简单处理：全部放 body，path 做替换，query None
        body_var = f"body_{op}"
        lines_local = []
        lines_local.append(f"\n    # {op}")
        lines_local.append(f"    path = '{p}'")
        # 注入绑定
        for b in binds.get(fname, []):
            src_ctx_key = b.src.replace('.yaml','')
            # 简单从 ctx[src]['data'] 深取
            src_field = b.src_param.split('.')
            getter = f"val = ctx.get('{src_ctx_key}', {{}})\n"
            getter += "    try:\n"
            getter += "        obj = val\n"
            for f in src_field:
                getter += f"        obj = obj.get('{f}', None)\n"
            getter += "    except Exception:\n        obj = None\n"
            getter += "    "
            lines_local.append(getter + f"if obj is None: raise AssertionError('缺少上游字段 {b.src_param}')")
            if b.loc == "path":
                lines_local.append(f"    path = path.replace('{{{{{b.dst_param}}}}}', str(obj))")
            else:
                lines_local.append(f"    {body_var}['{b.dst_param}'] = obj")

        lines_local.append(f"    url = BASE_URL + path")
        lines_local.append(f"    resp = requests.{method.lower()}(url, json={body_var} if {body_var} else None)")
        lines_local.append(f"    data = resp.json() if resp.content else {{}}")
        lines_local.append(f"    ctx['{op}'] = data")
        lines_local.append(f"    assert resp.status_code == 200, f'status {{}}, resp {{}}'.format(resp.status_code, data)")
        return lines_local

    for fname in order:
        path = API_DIR / fname
        if not path.exists():
            print(f"[WARN] skip missing openapi: {path}")
            continue
        api = load_api_yaml(fname)
        # 初始化 body 空 dict
        lines.append(f"\n\ndef test_{api['opId']}():")
        lines.append(f"    { 'body_'+api['opId'] } = {{}}")
        lines.extend(render_call(api))

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] 生成测试文件: {OUT_FILE}")

if __name__ == "__main__":
    edges = load_relations()
    order = topo(edges)  # e.g. ['createCalendar.yaml', 'getCalendar.yaml', 'deleteCalendar.yaml']
    gen_pytest(order, edges)