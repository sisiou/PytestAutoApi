输出示例：

输入发送消息的openai文档，action选择generate输入要生成、执行还是生成并执行，tools_call能够找到注册的七个工具中的飞书发送消息测试用例生成，并能够获取传递的参数：

请求示例：

```SQL
run_ai_test_router(
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
```

## 业务请求参数（来自前端）

- `project_root = project_root`
  - 项目地址，之前是为了执行本地脚本，脚本执行函数，现在修改完废弃，暂时保留
- `action: str`
  - `"generate" | "execute" | "genexec"`
  - 决定本次要生成、执行、还是生成并执行。
- `base_name: str`
  - 业务标识，用于生成文件名、定位测试文件、以及场景初判，可以直接将文件名放入
- `force_regenerate: bool`（可选）
  - 生成时是否强制覆盖，可传递给工具函数。
- `timeout_sec: int`（可选）
  - pytest / 子进程执行超时。
- `file_path: Optional[str]`（可选，execute 时建议支持）
  - 如果前端明确给了路径，应该传给工具。
- `files: Dict[str, str]`（强烈建议）
  - **文件内容**，用于：
    - Router 更准确地判别场景选择工具；（现在用于这步）
    - 也可把解析出的信息（例如接口路径、method、鉴权头示例）传给工具执行。
- ACCESS_KEY=ACCESS_KEY 
- BAILIAN_API_URL=BAILIAN_API_URL
- BAILIAN_MODEL=BAILIAN_MODEL
- verbose=True, 调试信息是否输出

工具注册

![img](https://jcnfwg1zejb4.feishu.cn/space/api/box/stream/download/asynccode/?code=MDljY2MzZTczOTQ2ZTVkMDJlZmRkOGZhODQ2MGU3NDJfSUUzS0JDb0Q4Tm5VMnBnUnpONWtKNk5DYmJIQzlGMlhfVG9rZW46WHNRbmI0dUxkb2IxUHF4Rk9uUWNBZVZHbjdkXzE3NjU5NDEzMjE6MTc2NTk0NDkyMV9WNA)

结果输出

![img](https://jcnfwg1zejb4.feishu.cn/space/api/box/stream/download/asynccode/?code=YWE5M2ExMmMzMzgwNjgxOGE2OGQ0MDVkMTBiZWQ2OWVfS2ZNeFZINk5PUmkzbklraWZJa3NGT1h3YXNEVXN4bXdfVG9rZW46RVd5ZGJ4dGhqb3hxWmt4Z3VCS2M5S2NzbnRlXzE3NjU5NDE0NjQ6MTc2NTk0NTA2NF9WNA)

![img](https://jcnfwg1zejb4.feishu.cn/space/api/box/stream/download/asynccode/?code=MTA0N2MzZDliMmQ3NDMzYjE3YzlkZWNhNjgyYjNlOGJfNXN1VWtBWDJTVmdzbktXT2xTUVJnMDJQVVVqWThENEZfVG9rZW46T1hBWWJtOEJ4b3J1elh4c2RRdWNNNzlkbkFlXzE3NjU5NDEzMjE6MTc2NTk0NDkyMV9WNA)

1. ### `router_service.py`

全局调用通过router_service中的run_ai_test_router函数，负责把一次前端请求组织成可执行的“路由任务”：

- 读取百炼配置、构建 LLM 客户端；
- 注册所有可用工具（`build_feishu_tools` 等）；
- 组装 `payload`（包含 request 参数和 files 内容）；
- 调用 `run_router_with_tools(...)` 执行“模型选工具 → 调用工具 → 返回结果”。

**“****Flask** **路由/本地测试”调用这里即可。**

然后

1. ### `agent_router.py`

**路由执行器（Router Runtime）**。负责执行工具调用循环（tool-calling loop）：

- `llm.bind_tools(tools)`：把工具注册给模型，让模型能返回 `tool_calls`；
- `invoke(messages)`：让模型判断该调用哪个工具；
- 解析 `tool_calls` 并执行 `tool.invoke(args)`；
- 把工具结果以 `ToolMessage` 回灌给模型（允许模型二次调整/收敛）；
- 最终返回模型输出或工具执行结果。

1. ### `tools_feishu.py`

**飞书****场景工具集合（Tool Registry - Feishu domain）**。负责把“飞书场景化函数”封装成工具：

- 每个工具代表一种业务场景能力（例如：飞书发送消息生成用例、日历生成用例、执行用例等）；
- 使用 `StructuredTool.from_function` 注册，提供：
  - `name`（模型选择用）
  - `description`（让模型知道什么时候用）
  - `args_schema`（参数结构化、可校验）
  - `func`（真实执行逻辑）

1. ### `schemas.py`

**工具参数（Schemas / DTO）**。用 Pydantic 定义工具入参结构，用于：

- 限定模型传参字段（如 `base_name/file_path/files/timeout_sec`）；
- `StructuredTool` 在 `invoke()` 时自动校验参数类型、缺失字段等；
- 让工具调用稳定可控，避免模型乱传参数导致不确定性。

1. ### `prompts.py`

**路由提示词（****Router** **Prompt）**。用来指导模型怎么选工具：

- 明确：根据 `action`（generate/execute/genexec）选择哪类工具；
- 明确：根据 `files/base_name` 判断是“飞书发送消息”还是“飞书通用”；
- 明确输出格式：要求模型输出 `tool_calls` 而不是随意文本。

1. ### `bailian_client.py`

**百炼模型适配层（****LLM** **Adapter****）**。负责把你自定义的 `call_bailian_api(...)` 或 LangChain LLM 封装起来：

- 提供 `build_bailian_chat_llm(...)`（用于 LangChain 的 `.invoke()` / `.bind_tools()`）；
- 统一处理：API key、base_url、model、temperature、max_tokens 等配置；
- 也可提供工具内的“二次增强调用”（例如飞书场景用 LLM 增强 YAML）。

## `router_service`中的run_ai_test_router典型函数签名：

- `project_root: Path`：项目根目录，用于定位脚本、输出目录、pytest 执行位置
- `action: str`：`"generate" | "execute" | "genexec"`
- `base_name: str`：接口/用例标识（用于命名、场景判断）
- `force_regenerate: bool`：是否强制覆盖生成
- `timeout_sec: int`：pytest/subprocess 超时
- `files: Dict[str, str]`：文件名 → 文件文本内容，如

```Python
with open('../../uploads/openapi/openapi_feishu_server-docs_im-v1_message_create.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
files = {
    "openapi.yaml": data,
}
```

- `ACCESS_KEY / BAILIAN_API_URL / BAILIAN_MODEL`：百炼配置
- `verbose: bool`：调试开关（打印 tool_calls / 执行步骤）

## `run_ai_test_router` 调用流程

下面是链路“从输入到输出”的完整流程，按顺序执行：

### Step 0：构建 LLM（百炼）

`router_service.py` 内：

1. 读取环境变量/配置：`ACCESS_KEY/BAILIAN_API_URL/BAILIAN_MODEL`
2. `build_bailian_chat_llm(...)` 得到可 `invoke()` 的 LLM 对象 目的：后续让模型完成“选工具 + 生成 tool_calls”。

### Step 1：注册工具（Tool Registry）

`router_service.py` 内：

1. 调用 `build_feishu_tools(...)` 返回飞书工具列表（多个 `StructuredTool`）
2. （可选）再追加 `build_generic_tools(...)` 返回通用工具列表
3. 拼成 `tools = [...所有工具...]`

### Step 2：组装 payload（把请求参数和文件一起交给模型）

`router_service.py` 内：

```
payload = {"request": {"action": action,"base_name": base_name,"force_regenerate": force_regenerate,"file_path": file_path,        # 可选：原始文件路径或标识 ``    "timeout_sec": timeout_sec, ``  },"files": files or {} ``}
```

- `request` 用于告诉模型“要干什么”
- `files` 用于告诉模型“这是哪个场景”

### Step 3：绑定工具 + 发起模型调用（产生 tool_calls）

`agent_router.py` 内：

1. `llm_with_tools = llm.bind_tools(tools)`
   1. 把工具 schema 注入模型上下文
2. 构造 messages：
   1. `SystemMessage(ROUTER_SYSTEM_PROMPT)`
   2. `HumanMessage(json.dumps(payload))`
3. `ai = llm_with_tools.invoke(messages)`

此时模型决定调用工具，会看到：

- `ai.content == ""`
- `ai.tool_calls != []`
- `finish_reason == "tool_calls"`

### Step 4：执行工具（tool.invoke）并参数注入/校验

`agent_router.py` 内：

1. 取出每个 tool_call：
   1. `name`（工具名）
   2. `args`（模型生成的参数字典）
2. （可选）做“参数兜底注入”：
   1. 如果模型没传 `files/file_path/base_name`，就从 `payload` 补齐
3. `tool.invoke(args)`
   1. `StructuredTool` 会用 `args_schema`（schemas.py）做参数校验
   2. 然后按 kwargs 调用你在 tools_feishu.py 注册的本地函数

### Step 5：回灌工具结果并收敛（可选多轮）

`agent_router.py` 内：

- 把工具执行结果包装成 `ToolMessage` 再追加到 messages
- 如果还在 `max_iterations` 内，会继续 `invoke()`，让模型决定是否需要下一次工具调用或直接输出最终结果

### Step 6：返回最终结果

- 如果工具调用成功：返回工具结果 dict
- 如果工具不存在/执行失败：返回 `tool_not_found/tool_execute_failed` 等结构化错误
- 如果模型没产生工具调用：返回 `{"output": ai.content}`（可能为空字符串）

### 其中参数注入部分：

![img](https://jcnfwg1zejb4.feishu.cn/space/api/box/stream/download/asynccode/?code=ODNlNDFkZmQxZGE5YjkzNmMwZThlMTdmNmY5NmNmNTNfcDlCaGFNWkhRTmpNSkVNZTBtVGlaWWJBMHVJMTdkMWlfVG9rZW46Rm10QWJFc1llb3BYQkt4eHE4OGNvekVobjRjXzE3NjU5NDEzMjE6MTc2NTk0NDkyMV9WNA)

## 如何将函数注册为工具：

在tools_feishu.py文件中，首先定义函数：（注意结果以dict格式封装）

```Python
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
    return {"result": "飞书发送消息测试用例生成", "file_path": file_path}
```

然后在return中使用StructuredTool封装即可，注意description要描写详细，那么是为了模型进行初步区分：

```Plain
return [
    StructuredTool.from_function(
        name="generate_test_cases_feishu",
        description="生成用例: 飞书通用场景",
        func=_generate_feishu,
        args_schema=GenerateArgs,
    ),
```

name的名称在prompts中进行了约定：generate_test_cases_*，或者execute_test_cases_*，以及generate_and_execute_*

```Python
ROUTER_SYSTEM_PROMPT = """你是自动化测试编排助手。你的任务是：
- 根据 request.action 选择并调用最合适的一个工具（只调用一次即可）。
- 最终只返回工具输出的JSON，不要输出解释。

工具选择规则：
1) 先判断场景：
   - 根据 base_name 或 files 对应的测试场景，如飞书通用场景，飞书发送消息场景，飞书日历场景
2) 再根据选择工具：
   - action == "generate"  -> 选择对应场景的 “generate_test_cases_*” 工具
   - action == "execute"   -> 选择对应场景的 “execute_test_cases_*” 工具
   - action == "genexec"   -> 选择对应场景的 “generate_and_execute_*” 工具

注意：
- 必须调用工具，不要直接编造返回内容。
- 传参必须严格匹配工具 schema（base_name/force_regenerate/timeout_sec/files/file_path）。
"""
```