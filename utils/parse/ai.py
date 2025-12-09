import os
import json
import yaml
import requests
import tempfile
import hashlib
import threading
from datetime import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse
import urllib3
from .feishu_parse import transform_feishu_url, is_file_exist, download_json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional

# 加载环境变量
load_dotenv()
ACCESS_KEY = os.getenv("DASHSCOPE_API_KEY")
BAILIAN_API_URL = os.getenv("BAILIAN_API_URL")
BAILIAN_MODEL = os.getenv("BAILIAN_MODEL")


def read_json_files(json_paths):
    """读取一个或多个接口JSON文件，返回合并后的接口数据"""
    api_data = []
    for path in json_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"JSON文件不存在：{path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            api_data.append({
                "file_name": path,
                "content": data
            })
    return api_data


def generate_file_fingerprint(json_paths):
    """
    根据JSON文件路径列表生成唯一指纹
    1. 先排序确保顺序一致性
    2. 用分隔符拼接路径
    3. 计算MD5哈希并取前8位
    """
    filenames = [os.path.basename(path) for path in json_paths]
    sorted_filenames = sorted(filenames)
    paths_str = "|".join(sorted_filenames)
    fingerprint = hashlib.md5(paths_str.encode()).hexdigest()[:8]
    print(f"输入文件指纹: {fingerprint} (基于 {len(json_paths)} 个文件)")
    return fingerprint


def get_output_path(json_paths, fingerprint, output_dir='../../openApi', file_type='openapi'):
    """
    生成输出文件路径
    - file_type: openapi/relation/scene 区分不同类型文件
    """
    base_filename = ""
    if len(json_paths) == 1:
        json_file = json_paths[0]
        base_name = os.path.basename(json_file)
        name_without_ext = os.path.splitext(base_name)[0]
        base_filename = f"{file_type}_{name_without_ext}_{fingerprint}"
    else:
        base_filename = f"{file_type}_bailian_{fingerprint}"

    # 不同文件类型对应不同后缀
    ext = "yaml" if file_type == "openapi" else "json"
    output_filename = f"{base_filename}.{ext}"
    output_path = os.path.join(output_dir, output_filename)
    print(f"{file_type}文件输出路径: {output_path}")
    return output_path


def should_regenerate(json_paths, output_path):
    """智能判断是否需要重新生成文件"""
    if not os.path.exists(output_path):
        print("输出文件不存在，需要生成")
        return True

    filename = os.path.basename(output_path)
    match = re.search(r'([a-f0-9]{8})\.(yaml|json)$', filename)
    if not match:
        print("无法从文件名提取指纹，需要重新生成")
        return True

    existing_fingerprint = match.group(1)
    current_fingerprint = generate_file_fingerprint(json_paths)

    if existing_fingerprint == current_fingerprint:
        print(f"指纹匹配（{existing_fingerprint}），跳过生成")
        return False
    else:
        print(f"指纹不匹配（现有: {existing_fingerprint}，当前: {current_fingerprint}），需要重新生成")
        return True


def call_bailian_api(prompt, system_prompt=None):
    """调用阿里云百炼API，通用封装"""
    try:
        client = OpenAI(
            api_key=ACCESS_KEY,
            base_url=BAILIAN_API_URL,
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model=BAILIAN_MODEL,
            messages=messages,
            temperature=0.1,  # 低温度保证输出稳定
            max_tokens=4096
        )

        content = completion.choices[0].message.content.strip()
        # 清洗多余标记
        content = content.replace("```json", "").replace("```yaml", "").replace("```", "").strip()
        return content

    except Exception as e:
        print(f"调用百炼API错误：{e}")
        print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
        return None


# def generate_openapi_yaml(json_paths, output_yaml_path):
#     """生成OpenAPI 3.0 YAML文件"""
#     api_json_data = read_json_files(json_paths)

#     prompt = f"""请将以下所有接口JSON数据转换为一个标准的OpenAPI 3.0 YAML文件，聚合所有接口到paths节点：
# {json.dumps(api_json_data, ensure_ascii=False, indent=2)}

# 额外要求：
# 1. info.title需基于接口内容命名（如“即时通讯+联系人+日历+认证服务API”），version设为1.0.0，description简要说明接口用途；
# 2. servers需包含至少一个示例（如http://api.example.com/v1，描述为“测试环境服务器”）；
# 3. 若多个接口复用同一数据结构（如用户信息、分页参数），必须提取到components/schemas中，通过$ref引用；
# 4. 路径参数（如/user/{{id}}）需在parameters中明确required: true，响应需包含200/400/500等常见状态码。"""

#     system_prompt = """你是精通OpenAPI 3.0规范（https://spec.openapis.org/oas/v3.0.3）的工程师，需将输入的接口JSON数据转换为标准OpenAPI 3.0 YAML文件。
# 严格遵循以下要求：
# 1. 必须包含info（title、version、description）、servers、paths、components（schemas）核心字段；
# 2. paths需完整映射所有接口的路径、HTTP方法、参数、请求体、响应结构；
# 3. components/schemas提取所有复用的JSON Schema，避免重复；
# 4. YAML语法必须合法（缩进一致、无语法错误），可直接被Swagger UI/Postman解析；
# 5. 仅返回YAML内容，不包含任何额外解释、说明文字或代码块标记。"""

#     yaml_content = call_bailian_api(prompt, system_prompt)
#     if not yaml_content:
#         raise Exception("未能从百炼API获取有效的YAML内容")

#     # 验证YAML合法性
#     try:
#         yaml.safe_load(yaml_content)
#     except yaml.YAMLError as e:
#         raise Exception(f"生成的YAML格式非法：{str(e)}\nYAML内容：{yaml_content}")

#     # 写入文件
#     output_dir = os.path.dirname(output_yaml_path)
#     os.makedirs(output_dir, exist_ok=True)
#     with open(output_yaml_path, "w", encoding="utf-8") as f:
#         f.write(yaml_content)

#     print(f"OpenAPI 3.0 YAML文件已生成：{output_yaml_path}")
#     return yaml_content

def generate_openapi_yaml(json_paths, output_yaml_path):
    """生成OpenAPI 3.0 YAML文件，重点优化发送消息接口的requestBody"""
    api_json_data = read_json_files(json_paths)

    # 构建针对发送消息接口的提示
    send_message_specific = """
    特别注意发送消息接口（路径通常为/im/v1/messages的POST方法）的requestBody处理：
    1. 必须完整保留所有msg_type类型（包括但不限于text、image、file、audio、media、sticker、interactive、share_chat、share_user等）
    2. 每种msg_type需在schema中明确对应的content字段结构：
       - text类型：{"text":"xxx"}
       - image类型：{"image_key":"xxx"}（需说明图片需先上传获取key）
       - file/audio/media类型：{"file_key":"xxx"}（需说明文件需先上传获取key）
       - 其他类型需按JSON中描述补充对应content格式
    3. 在examples中为每个msg_type添加至少一个示例，展示完整请求体（包含receive_id、msg_type、content等）
    4. 确保msg_type的enum值包含所有支持的消息类型，不遗漏任何在JSON中出现的类型
    """

    prompt = f"""请将以下所有接口JSON数据转换为一个标准的OpenAPI 3.0 YAML文件，聚合所有接口到paths节点：
{json.dumps(api_json_data, ensure_ascii=False, indent=2)}

额外要求：
1. info.title需基于接口内容命名（如“即时通讯+联系人+日历+认证服务API”），version设为1.0.0，description简要说明接口用途；
2. servers需包含至少一个示例（如http://api.example.com/v1，描述为“测试环境服务器”）；
3. 若多个接口复用同一数据结构（如用户信息、分页参数），必须提取到components/schemas中，通过$ref引用；
4. 路径参数（如/user/{{id}}）需在parameters中明确required: true，响应需包含200/400/500等常见状态码；
{send_message_specific}"""

    system_prompt = """你是精通OpenAPI 3.0规范（https://spec.openapis.org/oas/v3.0.3）的工程师，需将输入的接口JSON数据转换为标准OpenAPI 3.0 YAML文件。
严格遵循以下要求：
1. 必须包含info（title、version、description）、servers、paths、components（schemas）核心字段；
2. paths需完整映射所有接口的路径、HTTP方法、参数、请求体、响应结构；
3. components/schemas提取所有复用的JSON Schema，避免重复；
4. YAML语法必须合法（缩进一致、无语法错误），可直接被Swagger UI/Postman解析；
5. 对于发送消息接口，必须按照用户要求完整保留所有消息类型及其对应的content结构，不遗漏任何类型；
6. 仅返回YAML内容，不包含任何额外解释、说明文字或代码块标记。"""

    yaml_content = call_bailian_api(prompt, system_prompt)
    if not yaml_content:
        raise Exception("未能从百炼API获取有效的YAML内容")

    # 验证YAML合法性
    try:
        yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise Exception(f"生成的YAML格式非法：{str(e)}\nYAML内容：{yaml_content}")

    # 写入文件
    output_dir = os.path.dirname(output_yaml_path)
    os.makedirs(output_dir, exist_ok=True)
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"OpenAPI 3.0 YAML文件已生成：{output_yaml_path}")
    return yaml_content


# def generate_api_relation_file(json_paths, output_relation_path):
#     """
#     生成接口关联关系文件（JSON格式）
#     包含：接口依赖关系、数据流转、权限关联、上下游接口
#     """
#     api_json_data = read_json_files(json_paths)

#     prompt = f"""请分析以下接口JSON数据，生成接口关联关系文件（仅返回JSON内容，无其他解释）：
# {json.dumps(api_json_data, ensure_ascii=False, indent=2)}

# 输出JSON格式要求：
# {{
#   "relation_info": {{
#     "title": "接口关联关系总览",
#     "description": "所有接口的依赖、数据流转、权限关联关系",
#     "total_apis": N,
#     "relations": [
#       {{
#         "api_path": "接口路径",
#         "api_name": "接口名称",
#         "dependent_apis": ["依赖的接口路径1", "依赖的接口路径2"],
#         "dependent_reason": "依赖原因（如：需要先登录获取token、需要先创建用户）",
#         "data_flow": "该接口的数据来源和输出去向（如：从登录接口获取token，数据存储到用户表）",
#         "permission_relation": "权限关联（如：需要管理员权限、需要用户已登录）",
#         "upstream_apis": ["上游接口路径"],
#         "downstream_apis": ["下游接口路径"]
#       }}
#     ],
#     "key_relation_scenarios": [
#       {{
#         "scenario_name": "核心业务流程名称",
#         "api_sequence": ["接口路径1", "接口路径2", "接口路径3"],
#         "description": "该流程的业务意义和接口调用顺序说明"
#       }}
#     ]
#   }}
# }}"""

#     system_prompt = """你是资深的API架构师，擅长分析接口之间的关联关系。
# 要求：
# 1. 准确识别接口之间的依赖关系（如认证接口是其他接口的前置）；
# 2. 清晰描述数据流转方向和权限关联规则；
# 3. 总结核心业务流程的接口调用顺序；
# 4. 仅返回标准JSON格式，无任何额外文字、注释或标记；
# 5. 确保JSON语法合法，可直接被JSON.parse解析。"""

#     # 调用API生成关联关系
#     relation_content = call_bailian_api(prompt, system_prompt)
#     if not relation_content:
#         raise Exception("未能生成接口关联关系内容")

#     # 验证JSON合法性
#     try:
#         relation_json = json.loads(relation_content)
#     except json.JSONDecodeError as e:
#         raise Exception(f"生成的关联关系JSON格式非法：{str(e)}\n内容：{relation_content}")

#     # 写入文件
#     output_dir = os.path.dirname(output_relation_path)
#     os.makedirs(output_dir, exist_ok=True)
#     with open(output_relation_path, "w", encoding="utf-8") as f:
#         json.dump(relation_json, f, ensure_ascii=False, indent=2)

#     print(f"接口关联关系文件已生成：{output_relation_path}")
#     return relation_json

# def generate_api_relation_file(json_paths, output_relation_path):
#     """
#     生成接口关联关系文件（JSON格式）
#     增强：支持场景化条件依赖（如发送消息仅在图片场景下需要调用上传图片接口）
#     """
#     api_json_data = read_json_files(json_paths)
#
#     prompt = f"""请分析以下接口数据，生成接口关联关系文件（仅返回JSON内容，无其他解释）：
# {json.dumps(api_json_data, ensure_ascii=False, indent=2)}
#
# 输出JSON格式要求：
# {{
#   "relation_info": {{
#     "title": "接口关联关系总览",
#     "description": "所有接口的依赖、数据流转、权限关联关系，包含场景化条件依赖和参数级入参/出参传递",
#     "total_apis": N,
#     "relations": [
#       {{
#         "api_path": "接口路径",
#         "api_name": "接口名称",
#         "global_dependent_apis": ["全局必调的接口路径（如登录接口）"],
#         "conditional_dependent_apis": [
#           {{
#             "dependent_api_path": "条件依赖的接口路径（如上传图片接口）",
#             "trigger_scenarios": ["触发依赖的场景（如发送图片消息、发送富媒体消息）"],
#             "trigger_conditions": [
#               {{
#                 "param_name": "触发条件的参数名称（如message_type）",
#                 "param_location": "参数位置（body/query）",
#                 "match_rule": "匹配规则（如等于image、in [image, video]）",
#                 "description": "条件描述（如消息类型为图片时触发）"
#               }}
#             ],
#             "dependent_reason": "依赖原因（如：需要先上传图片获取image_id才能发送图片消息）",
#             "param_mapping": [
#               {{
#                 "source_param": "依赖接口的出参名称（如image_id、token）",
#                 "source_param_type": "参数类型（string/int/object）",
#                 "target_param": "当前接口的入参名称",
#                 "target_param_location": "参数位置（query/path/body/header）",
#                 "mapping_rule": "参数传递规则（如：直接传递、base64编码后传递、拼接后传递）"
#               }}
#             ],
#             "call_timing": "调用时机（如：调用当前接口前、调用当前接口时）",
#             "optional": true/false // 即使满足条件，是否可选调用（如部分场景可使用已有image_id）
#           }}
#         ],
#         "data_flow": {{
#           "global_input": [
#             {{
#               "api_path": "全局数据来源接口路径",
#               "params": ["来源参数1", "来源参数2"]
#             }}
#           ],
#           "conditional_input": [
#             {{
#               "trigger_scenarios": ["触发场景"],
#               "api_path": "条件数据来源接口路径",
#               "params": ["来源参数1"]
#             }}
#           ],
#           "output_data_dest": [
#             {{
#               "api_path": "数据输出目标接口路径",
#               "params": ["输出参数1", "输出参数2"]
#             }}
#           ],
#           "storage_location": "数据存储位置（如：IM消息表、用户表、图片存储服务）"
#         }},
#         "permission_relation": {{
#           "required_permission": "需要的权限（如管理员权限、普通用户权限）",
#           "auth_param": "认证参数名称（如token）",
#           "auth_param_location": "参数位置（header/query）",
#           "auth_api_path": "获取认证参数的接口路径（如登录接口）"
#         }},
#         "upstream_apis": ["上游接口路径"],
#         "downstream_apis": ["下游接口路径"]
#       }}
#     ],
#     "key_relation_scenarios": [
#       {{
#         "scenario_name": "核心业务流程名称（如发送图片消息/发送文本消息）",
#         "api_sequence": ["接口路径1（登录）", "接口路径2（上传图片）", "接口路径3（发送消息）"],
#         "sequence_detail": [
#           {{
#             "api_path": "接口路径",
#             "call_order": 1,
#             "is_necessary": true/false, // 该步骤在当前场景是否必须
#             "output_params": ["该接口输出的关键参数（如image_id）"],
#             "next_api_mapping": [
#               {{
#                 "next_api_path": "下一个调用的接口路径",
#                 "param_mapping": [
#                   {{
#                     "source_param": "当前接口输出参数",
#                     "target_param": "下一个接口入参",
#                     "target_param_location": "参数位置"
#                   }}
#                 ]
#               }}
#             ]
#           }}
#         ],
#         "description": "该流程的业务意义和接口调用顺序说明，包含参数传递细节"
#       }}
#     ]
#   }}
# }}
#
# 关键要求：
# 1. 严格区分“全局必调依赖”和“场景化条件依赖”：
#    - 全局必调：如登录接口（所有发送消息场景都需要token）
#    - 条件依赖：如上传图片接口（仅发送图片消息时需要）
# 2. 明确条件依赖的触发场景、触发条件（如message_type=image）；
# 3. 详细描述参数级映射关系，例如：
#    - 上传图片接口（/im/v1/image/create）返回image_id（string类型）
#    - 发送图片消息时，将image_id作为body中的image_id参数传入
#    - 发送文本消息时，无需调用上传图片接口
# 4. 若接口无依赖关系，对应字段为空数组，不要省略；
# 5. 核心业务场景要区分不同子场景（如发送文本/图片消息）的接口调用差异。"""
#
#     system_prompt = """你是资深的API架构师和测试专家，擅长分析接口之间的关联关系，尤其是场景化条件依赖和参数级的入参/出参传递。
# 要求：
# 1. 精准区分“全局必调依赖”（如登录接口）和“场景化条件依赖”（如上传图片仅在发送图片消息时需要）；
# 2. 明确条件依赖的触发场景、触发条件（如message_type=image）、参数映射关系；
# 3. 核心业务场景要拆分不同子场景（如发送文本消息/发送图片消息），体现接口调用差异；
# 4. 仅返回标准JSON格式，无任何额外文字、注释或标记；
# 5. 确保JSON语法合法，可直接被JSON.parse解析；
# 6. 若接口无依赖关系，对应字段为空数组，不要省略。"""
#
#     # 调用API生成关联关系
#     relation_content = call_bailian_api(prompt, system_prompt)
#     if not relation_content:
#         raise Exception("未能生成接口关联关系内容")
#
#     # 验证JSON合法性
#     try:
#         relation_json = json.loads(relation_content)
#     except json.JSONDecodeError as e:
#         raise Exception(f"生成的关联关系JSON格式非法：{str(e)}\n内容：{relation_content}")
#
#     # 写入文件
#     output_dir = os.path.dirname(output_relation_path)
#     os.makedirs(output_dir, exist_ok=True)
#     with open(output_relation_path, "w", encoding="utf-8") as f:
#         json.dump(relation_json, f, ensure_ascii=False, indent=2)
#
#     print(f"接口关联关系文件已生成：{output_relation_path}")
#     return relation_json

def generate_api_relation_file(openapi_file_paths, output_relation_path):
    """
    生成简化版接口关联关系文件
    仅输出：关联的OpenAPI文件（仅保留文件名）、接口路径、关联参数
    """
    # 读取所有OpenAPI文件内容，并仅保留文件名
    openapi_data = []
    for openapi_path in openapi_file_paths:
        if not os.path.exists(openapi_path):
            raise FileNotFoundError(f"OpenAPI文件不存在：{openapi_path}")
        # 仅保留文件名（去除目录前缀）
        openapi_filename = os.path.basename(openapi_path)
        with open(openapi_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                openapi_data.append({
                    "openapi_file": openapi_filename,  # 仅保留文件名
                    "api_paths": list(data.get("paths", {}).keys()) if data else [],
                    "content": data
                })
            except yaml.YAMLError as e:
                print(f"读取OpenAPI文件 {openapi_path} 失败：{e}")
                continue

    # 构建关联分析提示，强调仅保留文件名
    prompt = f"""请分析以下OpenAPI文件列表，找出其中存在关联的接口，并输出简化的关联关系：
{json.dumps(openapi_data, ensure_ascii=False, indent=2)}

输出JSON格式要求（仅保留核心关联信息，不要多余字段）：
{{
  "relation_summary": "接口关联关系汇总",
  "total_related_pairs": N,
  "related_pairs": [
    {{
      "source_openapi_file": "源OpenAPI文件名（仅保留文件名，如openapi_server-docs_im-v1_image_create_4293d832.yaml）",
      "source_api_path": "源接口路径",
      "target_openapi_file": "目标OpenAPI文件名（仅保留文件名）",
      "target_api_path": "目标接口路径",
      "relation_params": [
        {{
          "source_param": "源接口输出参数（如image_id）",
          "target_param": "目标接口输入参数（如image_id）",
          "param_location": "参数位置（body/query/header）",
          "relation_type": "依赖类型（全局/条件）"
        }}
      ],
      "relation_desc": "简要关联描述（如：上传图片接口返回的image_id作为发送消息接口的入参）"
    }}
  ],
  "unrelated_files": ["无关联的OpenAPI文件名列表（仅保留文件名）"]
}}

关键要求：
1. 仅输出存在关联的接口对，无关联的放入unrelated_files；
2. relation_params仅保留核心关联参数，不要冗余；
3. relation_type仅区分"全局"（必须依赖）和"条件"（特定场景依赖）；
4. source_openapi_file/target_openapi_file/unrelated_files 仅保留文件名，不要任何目录路径（如../../openApi\\）；
5. 仅返回标准JSON，无任何额外文字、注释。"""

    system_prompt = """你是API关联分析专家，需简化分析接口间的关联关系，仅保留：
1. 关联的OpenAPI文件名（仅保留文件名，去除所有目录路径）
2. 关联的接口路径
3. 核心关联参数（输入输出映射）
4. 依赖类型（全局/条件）
要求输出极简，仅保留上述核心信息，不要多余描述，且文件名必须仅保留纯文件名（无目录前缀）。"""

    # 调用API生成简化关联关系
    relation_content = call_bailian_api(prompt, system_prompt)
    if not relation_content:
        raise Exception("未能生成简化版接口关联关系内容")

    # 二次兜底处理：确保返回的JSON中所有文件名都仅保留纯文件名（防止AI未遵守要求）
    try:
        relation_json = json.loads(relation_content)

        # 处理related_pairs中的文件名
        if "related_pairs" in relation_json:
            for pair in relation_json["related_pairs"]:
                if "source_openapi_file" in pair:
                    pair["source_openapi_file"] = os.path.basename(pair["source_openapi_file"])
                if "target_openapi_file" in pair:
                    pair["target_openapi_file"] = os.path.basename(pair["target_openapi_file"])

        # 处理unrelated_files中的文件名
        if "unrelated_files" in relation_json:
            relation_json["unrelated_files"] = [
                os.path.basename(file) for file in relation_json["unrelated_files"]
            ]

    except json.JSONDecodeError as e:
        raise Exception(f"生成的关联关系JSON格式非法：{str(e)}\n内容：{relation_content}")

    # 写入文件
    output_dir = os.path.dirname(output_relation_path)
    os.makedirs(output_dir, exist_ok=True)
    with open(output_relation_path, "w", encoding="utf-8") as f:
        json.dump(relation_json, f, ensure_ascii=False, indent=2)

    print(f"接口关联关系文件已生成：{output_relation_path}")
    return relation_json

def generate_business_scene_file(json_paths, output_scene_path):
    """
    生成业务场景文件（JSON格式）
    包含：核心业务场景、场景描述、接口调用组合、测试关注点
    """
    api_json_data = read_json_files(json_paths)

    prompt = f"""请分析以下接口JSON数据，生成业务场景文件（仅返回JSON内容，无其他解释）：
{json.dumps(api_json_data, ensure_ascii=False, indent=2)}

输出JSON格式要求：
{{
  "business_scenes": {{
    "title": "业务场景总览",
    "description": "基于接口功能的核心业务场景汇总",
    "scenes": [
      {{
        "scene_id": "场景唯一标识（如SCENE_IM_CREATE_MESSAGE）",
        "scene_name": "场景名称（如：创建即时通讯消息）",
        "scene_description": "场景的详细业务描述，包括使用场景、用户群体、业务价值",
        "related_apis": ["关联的接口路径1", "关联的接口路径2"],
        "api_call_combo": [
          {{
            "api_path": "接口路径",
            "call_order": 1,
            "call_condition": "调用条件（如：用户已登录、参数满足XX条件）",
            "expected_result": "预期结果（如：返回200、创建成功、返回token）"
          }}
        ],
        "test_focus": [
          "该场景的测试关注点（如：参数合法性、权限控制、数据一致性、并发处理）"
        ],
        "exception_scenarios": [
          "该场景下的异常情况（如：未登录调用、参数缺失、权限不足、网络超时）"
        ],
        "priority": "优先级（P0/P1/P2，P0为核心场景）"
      }}
    ]
  }}
}}"""

    system_prompt = """你是资深的业务分析师和测试专家，擅长从接口定义推导业务场景。
要求：
1. 基于接口功能提炼真实的业务场景（而非单纯的接口调用）；
2. 每个场景明确接口调用组合、顺序和条件；
3. 标注测试关注点和异常场景，便于生成测试用例；
4. 按业务重要性划分优先级（P0核心、P1次要、P2边缘）；
5. 仅返回标准JSON格式，无任何额外文字、注释或标记；
6. 确保JSON语法合法，可直接被JSON.parse解析。"""

    # 调用API生成业务场景
    scene_content = call_bailian_api(prompt, system_prompt)
    if not scene_content:
        raise Exception("未能生成业务场景内容")

    # 验证JSON合法性
    try:
        scene_json = json.loads(scene_content)
    except json.JSONDecodeError as e:
        raise Exception(f"生成的业务场景JSON格式非法：{str(e)}\n内容：{scene_content}")

    # 写入文件
    output_dir = os.path.dirname(output_scene_path)
    os.makedirs(output_dir, exist_ok=True)
    with open(output_scene_path, "w", encoding="utf-8") as f:
        json.dump(scene_json, f, ensure_ascii=False, indent=2)

    print(f"业务场景文件已生成：{output_scene_path}")
    return scene_json



def process_url_with_ai(url, output_dir, force_regenerate=False):
    """
    使用AI处理URL并生成OpenAPI、关联关系和业务场景文件
    
    Args:
        url (str): 要处理的飞书URL
        output_dir (str): 输出目录
        force_regenerate (bool): 是否强制重新生成所有文件，即使已存在
    
    Returns:
        dict: 包含生成文件内容和路径的字典
    """
    try:
        # 标准化URL（去除查询参数和片段）
        normalized_url = _normalize_url(url)
        
        # 创建安全的文件名
        file_key = _create_file_key_from_url(normalized_url)
        
        # 定义输出目录
        json_dir = os.path.join(output_dir, 'json')
        openapi_dir = os.path.join(output_dir, 'openapi')
        relation_dir = os.path.join(output_dir, 'relation')
        scene_dir = os.path.join(output_dir, 'scene')
        
        # 确保输出目录存在
        for directory in [json_dir, openapi_dir, relation_dir, scene_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # 定义输出文件路径
        json_output_path = os.path.join(output_dir, 'json', f"json_{file_key}.json")
        openapi_output_path = os.path.join(openapi_dir, f"openapi_{file_key}.yaml")
        relation_output_path = os.path.join(relation_dir, f"relation_{file_key}.json")
        scene_output_path = os.path.join(scene_dir, f"scene_{file_key}.json")
        
        # 检查文件是否已存在且不需要强制重新生成
        files_exist = all([
            os.path.exists(json_output_path),
            os.path.exists(openapi_output_path),
            os.path.exists(relation_output_path),
            os.path.exists(scene_output_path)
        ])
        
        # 如果有缓存且不需要强制重新生成，直接读取缓存
        if files_exist and not force_regenerate:
            print(f"使用缓存文件: {file_key}")
            return _read_existing_files(openapi_output_path, relation_output_path, 
                                       scene_output_path, url, file_key)
        
        print(f"开始处理: {url}")
        
        # 获取JSON数据
        json_data = _fetch_json_data(normalized_url, json_output_path)
        
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_filepath = os.path.join(temp_dir, "data.json")
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            json_paths = [temp_filepath]
            
            # 并行生成文件
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                
                # 提交生成任务
                futures['openapi'] = executor.submit(
                    generate_openapi_yaml, json_paths, openapi_output_path
                )
                futures['relation'] = executor.submit(
                    generate_api_relation_file, json_paths, relation_output_path
                )
                futures['scene'] = executor.submit(
                    generate_business_scene_file, json_paths, scene_output_path
                )
                
                # 等待所有任务完成并收集结果
                results = {}
                for name, future in futures.items():
                    try:
                        results[name] = future.result()
                        print(f"生成 {name} 文件完成")
                    except Exception as e:
                        print(f"生成 {name} 文件失败: {str(e)}")
                        # 如果一个文件生成失败，删除所有已生成的文件
                        _cleanup_partial_files(
                            openapi_output_path, 
                            relation_output_path, 
                            scene_output_path
                        )
                        raise Exception(f"生成 {name} 文件失败: {str(e)}")
        
        # 读取生成的文件内容
        return _read_existing_files(openapi_output_path, relation_output_path, 
                                   scene_output_path, url, file_key)
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'AI解析失败',
            'url': url,
            'timestamp': datetime.datetime.now().isoformat()
        }


def _normalize_url(url):
    """标准化URL，去除查询参数和片段，保留主要路径"""
    parsed = urlparse(url)
    
    # 移除查询参数和片段
    normalized = parsed._replace(query='', fragment='')
    
    # 对于飞书文档，特殊处理
    if 'feishu.cn' in parsed.netloc:
        # 飞书文档：保留文档ID部分
        path_parts = parsed.path.split('/')
        # 处理 /document/ 格式的飞书文档
        if 'document' in path_parts:
            # 格式类似：/document/server-docs/im-v1/message/create
            # 保留整个document路径
            document_path = '/'.join(path_parts[path_parts.index('document'):])
            return urlunparse(normalized._replace(path=f'/{document_path}'))
    
    return urlunparse(normalized)


def _create_file_key_from_url(normalized_url):
    """从标准化URL创建文件标识键"""
    parsed = urlparse(normalized_url)
    
    # 提取域名和路径
    domain = parsed.netloc.replace('.', '_')
    path = parsed.path.strip('/')
    
    # 如果路径为空，使用域名
    if not path:
        return domain
    
    # 分割路径，取最后一部分作为主要标识
    path_parts = path.split('/')
    
    # 对于常见API文档路径，提取关键部分
    if 'swagger' in path.lower() or 'openapi' in path.lower():
        # 对于Swagger/OpenAPI文档，使用版本号或文档名
        for i, part in enumerate(path_parts):
            if 'v' in part.lower() and (part[1:].isdigit() or part.lower().startswith('v')):
                return f"{domain}_{part}"
    
    # 对于飞书文档
    if 'feishu.cn' in parsed.netloc:
        # 处理 /document/ 格式的飞书文档
        if 'document' in path:
            # 提取document后的路径，使用所有部分作为标识
            if 'document' in path_parts:
                doc_index = path_parts.index('document')
                if doc_index + 1 < len(path_parts):
                    # 使用document后的所有路径部分，用下划线连接
                    remaining_parts = path_parts[doc_index + 1:]
                    return f"feishu_{'_'.join(remaining_parts)}"
    
    # 通用处理：使用路径的最后一部分，限制长度
    last_part = path_parts[-1] if path_parts else 'api'
    
    # 清理文件名（移除特殊字符）
    safe_name = ''.join(c for c in last_part if c.isalnum() or c in ('-', '_'))
    
    # 如果清理后为空，使用时间戳
    if not safe_name:
        safe_name = f"api_{int(time.time())}"
    
    # 限制长度
    safe_name = safe_name[:50]
    
    return f"{domain}_{safe_name}"


def _fetch_json_data(normalized_url, json_path):
    """从标准化URL获取JSON数据"""
    parsed_url = urlparse(normalized_url)
    
    # 处理飞书文档URL
    if 'feishu.cn' in parsed_url.netloc:
        return _fetch_feishu_data(normalized_url, json_path)
    
    # 处理本地文件
    if normalized_url.startswith('file://'):
        return _fetch_local_file_data(normalized_url, json_path)
    
    # 处理远程URL
    return _fetch_remote_url_data(normalized_url, json_path)


def _fetch_feishu_data(normalized_url, json_path):
    """获取飞书文档数据"""
    try:
        # 转换飞书URL为可下载的URL
        download_url, path = transform_feishu_url(normalized_url)
        
        # 下载JSON文件
        data = download_json(download_url, json_path)
        return data

    except Exception as e:
        raise Exception(f"无法下载飞书文档: {url}, 错误: {str(e)}")


def _fetch_local_file_data(url, json_path):
    """获取本地文件数据并写入JSON文件
    
    Args:
        url: 本地文件URL，以'file://'开头
        json_path: JSON文件输出路径
    
    Returns:
        解析后的JSON数据
    """
    file_path = url[7:]  # 移除 'file://' 前缀
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"本地文件不存在: {file_path}")
    
    print(f"读取本地文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 尝试解析为JSON或YAML
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            raise ValueError("本地文件不是有效的JSON或YAML格式")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(json_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 写入JSON文件
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"JSON数据已写入文件: {json_path}")
    
    return data


def _fetch_remote_url_data(url, json_path):
    """获取远程URL数据并写入JSON文件
    
    Args:
        url: 远程URL
        json_path: JSON文件输出路径
    
    Returns:
        解析后的JSON数据
    """
    print(f"下载远程文件: {url}")
    
    # 禁用SSL警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    session = requests.Session()
    session.verify = False  # 禁用SSL验证
    
    # 设置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, application/yaml, */*'
    }
    
    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"无法访问URL: {url}, 错误: {str(e)}")
    
    content_type = response.headers.get('Content-Type', '')
    
    # 根据Content-Type处理内容
    if 'application/json' in content_type:
        data = response.json()
    elif 'application/yaml' in content_type or 'text/yaml' in content_type:
        data = yaml.safe_load(response.text)
    else:
        # 尝试自动检测格式
        try:
            data = response.json()
        except ValueError:
            try:
                data = yaml.safe_load(response.text)
            except yaml.YAMLError:
                # 尝试从响应头或内容中推断
                content = response.text
                if content.strip().startswith('{') or content.strip().startswith('['):
                    # 可能是JSON但没有正确的Content-Type
                    data = json.loads(content)
                elif 'openapi' in content.lower() or 'swagger' in content.lower():
                    # 尝试解析为YAML
                    data = yaml.safe_load(content)
                else:
                    raise ValueError(f"无法解析URL内容，不支持格式。Content-Type: {content_type}")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(json_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 写入JSON文件
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"远程数据已写入文件: {json_path}")
    
    return data


def _read_existing_files(openapi_path, relation_path, scene_path, url, file_key):
    """读取已存在的文件"""
    try:
        # 检查文件是否存在
        if not all(os.path.exists(p) for p in [openapi_path, relation_path, scene_path]):
            raise FileNotFoundError("部分输出文件不存在")
        
        # 读取YAML文件并转换为JSON
        with open(openapi_path, 'r', encoding='utf-8') as f:
            openapi_data = yaml.safe_load(f)
        
        # 读取关联关系文件
        with open(relation_path, 'r', encoding='utf-8') as f:
            relation_json = json.load(f)
        
        # 读取业务场景文件
        with open(scene_path, 'r', encoding='utf-8') as f:
            scene_json = json.load(f)
        
        # 获取文件修改时间
        openapi_mtime = datetime.fromtimestamp(os.path.getmtime(openapi_path))
        
        return {
            'success': True,
            'url': url,
            'file_key': file_key,
            'openapi_data': openapi_data,
            'relation_data': relation_json,
            'scene_data': scene_json,
            'openapi_file': openapi_path,
            'relation_file': relation_path,
            'scene_file': scene_path,
            'generated_at': openapi_mtime.isoformat(),
            'message': '从缓存读取成功' if file_key else 'AI解析成功'
        }
    except Exception as e:
        raise Exception(f"读取生成文件失败: {str(e)}")


def _cleanup_partial_files(*filepaths):
    """清理部分生成的文件"""
    for filepath in filepaths:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"清理文件: {filepath}")
            except Exception as e:
                print(f"清理文件失败 {filepath}: {str(e)}")


# 缓存管理函数
def get_cached_urls(output_dir):
    """获取所有已缓存的URL"""
    cache_info = []
    
    for dir_type in ['openapi', 'relation', 'scene']:
        dir_path = os.path.join(output_dir, dir_type)
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.endswith('.yaml') or filename.endswith('.json'):
                    # 提取file_key
                    parts = filename.split('_', 1)
                    if len(parts) > 1:
                        file_key = parts[1].rsplit('.', 1)[0]
                        filepath = os.path.join(dir_path, filename)
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        
                        cache_info.append({
                            'file_key': file_key,
                            'type': dir_type,
                            'filename': filename,
                            'path': filepath,
                            'modified': mtime.isoformat()
                        })
    
    return cache_info


def clear_cache_for_url(output_dir, file_key):
    """清除特定URL的缓存"""
    files_removed = []
    
    for dir_type in ['openapi', 'relation', 'scene']:
        dir_path = os.path.join(output_dir, dir_type)
        if os.path.exists(dir_path):
            # 查找匹配的文件
            pattern = f"*_{file_key}.*"
            import glob
            matching_files = glob.glob(os.path.join(dir_path, pattern))
            
            for filepath in matching_files:
                try:
                    os.remove(filepath)
                    files_removed.append(filepath)
                    print(f"已删除缓存文件: {filepath}")
                except Exception as e:
                    print(f"删除文件失败 {filepath}: {str(e)}")
    
    return files_removed


def clear_all_cache(output_dir):
    """清除所有缓存"""
    files_removed = []
    
    for dir_type in ['openapi', 'relation', 'scene']:
        dir_path = os.path.join(output_dir, dir_type)
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                filepath = os.path.join(dir_path, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                        files_removed.append(filepath)
                    except Exception as e:
                        print(f"删除文件失败 {filepath}: {str(e)}")
    
    return files_removed


# ==================== 主执行逻辑 ====================
if __name__ == "__main__":
    # 待转换的接口JSON文件路径
    json_file_paths = [
        "../../api/server-docs_im-v1_message_create.json",
        "../../api/server-docs_contact-v3_user_create.json",
        "../../api/server-docs_calendar-v4_calendar_create.json",
        "../../api/server-docs_authentication-management_login-state-management_get.json"
    ]

    # 1. 生成指纹
    fingerprint = generate_file_fingerprint(json_file_paths)

    # 2. 定义输出目录
    output_dir = "../../openApi"

    # 3. 生成OpenAPI YAML文件
    openapi_output_path = get_output_path(json_file_paths, fingerprint, output_dir, "openapi")
    if should_regenerate(json_file_paths, openapi_output_path):
        try:
            generate_openapi_yaml(json_file_paths, openapi_output_path)
        except Exception as e:
            print(f"生成OpenAPI文件失败：{str(e)}")
    else:
        print("跳过OpenAPI文件生成，使用现有文件")

    # 4. 生成接口关联关系文件
    relation_output_path = get_output_path(json_file_paths, fingerprint, output_dir, "api_relation")
    if should_regenerate(json_file_paths, relation_output_path):
        try:
            generate_api_relation_file(json_file_paths, relation_output_path)
        except Exception as e:
            print(f"生成接口关联关系文件失败：{str(e)}")
    else:
        print("跳过接口关联关系文件生成，使用现有文件")

    # 5. 生成业务场景文件
    scene_output_path = get_output_path(json_file_paths, fingerprint, output_dir, "business_scene")
    if should_regenerate(json_file_paths, scene_output_path):
        try:
            generate_business_scene_file(json_file_paths, scene_output_path)
        except Exception as e:
            print(f"生成业务场景文件失败：{str(e)}")
    else:
        print("跳业务场景文件生成，使用现有文件")

    print("\n=== 生成完成 ===")
    print(f"OpenAPI文件：{openapi_output_path}")
    print(f"接口关联关系文件：{relation_output_path}")

    print(f"业务场景文件：{scene_output_path}")