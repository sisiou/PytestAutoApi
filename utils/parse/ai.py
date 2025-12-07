import os
import json
import yaml
import hashlib
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional
from feishu_parse import download_json, transform_feishu_url
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def generate_openapi_yaml(json_paths, output_yaml_path):
    """生成OpenAPI 3.0 YAML文件"""
    api_json_data = read_json_files(json_paths)

    prompt = f"""请将以下所有接口JSON数据转换为一个标准的OpenAPI 3.0 YAML文件，聚合所有接口到paths节点：
{json.dumps(api_json_data, ensure_ascii=False, indent=2)}

额外要求：
1. info.title需基于接口内容命名（如“即时通讯+联系人+日历+认证服务API”），version设为1.0.0，description简要说明接口用途；
2. servers需包含至少一个示例（如http://api.example.com/v1，描述为“测试环境服务器”）；
3. 若多个接口复用同一数据结构（如用户信息、分页参数），必须提取到components/schemas中，通过$ref引用；
4. 路径参数（如/user/{{id}}）需在parameters中明确required: true，响应需包含200/400/500等常见状态码。"""

    system_prompt = """你是精通OpenAPI 3.0规范（https://spec.openapis.org/oas/v3.0.3）的工程师，需将输入的接口JSON数据转换为标准OpenAPI 3.0 YAML文件。
严格遵循以下要求：
1. 必须包含info（title、version、description）、servers、paths、components（schemas）核心字段；
2. paths需完整映射所有接口的路径、HTTP方法、参数、请求体、响应结构；
3. components/schemas提取所有复用的JSON Schema，避免重复；
4. YAML语法必须合法（缩进一致、无语法错误），可直接被Swagger UI/Postman解析；
5. 仅返回YAML内容，不包含任何额外解释、说明文字或代码块标记。"""

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


def generate_api_relation_file(json_paths, output_relation_path):
    """
    生成接口关联关系文件（JSON格式）
    包含：接口依赖关系、数据流转、权限关联、上下游接口
    """
    api_json_data = read_json_files(json_paths)

    prompt = f"""请分析以下接口JSON数据，生成接口关联关系文件（仅返回JSON内容，无其他解释）：
{json.dumps(api_json_data, ensure_ascii=False, indent=2)}

输出JSON格式要求：
{{
  "relation_info": {{
    "title": "接口关联关系总览",
    "description": "所有接口的依赖、数据流转、权限关联关系",
    "total_apis": N,
    "relations": [
      {{
        "api_path": "接口路径",
        "api_name": "接口名称",
        "dependent_apis": ["依赖的接口路径1", "依赖的接口路径2"],
        "dependent_reason": "依赖原因（如：需要先登录获取token、需要先创建用户）",
        "data_flow": "该接口的数据来源和输出去向（如：从登录接口获取token，数据存储到用户表）",
        "permission_relation": "权限关联（如：需要管理员权限、需要用户已登录）",
        "upstream_apis": ["上游接口路径"],
        "downstream_apis": ["下游接口路径"]
      }}
    ],
    "key_relation_scenarios": [
      {{
        "scenario_name": "核心业务流程名称",
        "api_sequence": ["接口路径1", "接口路径2", "接口路径3"],
        "description": "该流程的业务意义和接口调用顺序说明"
      }}
    ]
  }}
}}"""

    system_prompt = """你是资深的API架构师，擅长分析接口之间的关联关系。
要求：
1. 准确识别接口之间的依赖关系（如认证接口是其他接口的前置）；
2. 清晰描述数据流转方向和权限关联规则；
3. 总结核心业务流程的接口调用顺序；
4. 仅返回标准JSON格式，无任何额外文字、注释或标记；
5. 确保JSON语法合法，可直接被JSON.parse解析。"""

    # 调用API生成关联关系
    relation_content = call_bailian_api(prompt, system_prompt)
    if not relation_content:
        raise Exception("未能生成接口关联关系内容")

    # 验证JSON合法性
    try:
        relation_json = json.loads(relation_content)
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


def process_url_with_ai(url, output_dir=None):
    """
    处理URL并生成OpenAPI、关联关系和业务场景文件
    返回JSON格式的结果，便于通过API调用
    
    Args:
        url: 要处理的URL
        output_dir: 输出目录，如果为None则使用默认目录
        
    Returns:
        dict: 包含生成的文件内容和元数据的字典
    """
    try:
        import hashlib
        
        # 设置默认输出目录
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '../../openApi')
        
        # 创建临时目录存储下载的JSON文件
        temp_dir = os.path.join(output_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 转换飞书URL为API格式
        api_url, path = transform_feishu_url(url)
        
        # 生成URL的哈希值作为UUID
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # 创建三种类型文档的子目录
        openapi_dir = os.path.join(output_dir, 'openapi')
        relation_dir = os.path.join(output_dir, 'relation')
        scene_dir = os.path.join(output_dir, 'scene')
        
        os.makedirs(openapi_dir, exist_ok=True)
        os.makedirs(relation_dir, exist_ok=True)
        os.makedirs(scene_dir, exist_ok=True)
        
        # 生成临时文件名
        temp_filename = f"ai_parse_{int(time.time())}.json"
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        # 下载JSON文件
        download_json(api_url, temp_filepath)
        
        # 检查文件是否存在
        if not os.path.exists(temp_filepath):
            raise Exception(f"无法下载或解析URL内容: {url}")
        
        # 使用ai.py中的函数生成文件
        json_paths = [temp_filepath]
        
        # 定义输出路径，使用URL哈希作为文件名的一部分
        openapi_output_path = os.path.join(openapi_dir, f"openapi_{url_hash}.yaml")
        relation_output_path = os.path.join(relation_dir, f"relation_{url_hash}.json")
        scene_output_path = os.path.join(scene_dir, f"scene_{url_hash}.json")
        
        # 检查文件是否已存在，如果存在则直接读取
        openapi_exists = os.path.exists(openapi_output_path)
        relation_exists = os.path.exists(relation_output_path)
        scene_exists = os.path.exists(scene_output_path)
        
        # 并行生成三个文件
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交三个任务
            futures = {}
            
            # 生成OpenAPI YAML文件
            if not openapi_exists:
                futures['openapi'] = executor.submit(generate_openapi_yaml, json_paths, openapi_output_path)
            else:
                # 如果文件已存在，不需要执行任何操作
                futures['openapi'] = None
            
            # 生成接口关联关系文件
            if not relation_exists:
                futures['relation'] = executor.submit(generate_api_relation_file, json_paths, relation_output_path)
            else:
                # 如果文件已存在，不需要执行任何操作
                futures['relation'] = None
            
            # 生成业务场景文件
            if not scene_exists:
                futures['scene'] = executor.submit(generate_business_scene_file, json_paths, scene_output_path)
            else:
                # 如果文件已存在，不需要执行任何操作
                futures['scene'] = None
            
            # 等待所有任务完成
            for key, future in futures.items():
                if future is not None:  # 只处理非None的Future对象
                    try:
                        future.result()
                    except Exception as e:
                        raise e
        
        # 读取生成的文件内容
        # 读取YAML文件并转换为JSON
        with open(openapi_output_path, 'r', encoding='utf-8') as f:
            openapi_data = yaml.safe_load(f)
        
        # 读取关联关系文件
        with open(relation_output_path, 'r', encoding='utf-8') as f:
            relation_json = json.load(f)
        
        # 读取业务场景文件
        with open(scene_output_path, 'r', encoding='utf-8') as f:
            scene_json = json.load(f)
        
        # 返回生成的文件内容
        result = {
            'success': True,
            'url': url,
            'url_hash': url_hash,
            'openapi_data': openapi_data,
            'relation_data': relation_json,
            'scene_data': scene_json,
            'openapi_file': openapi_output_path,
            'relation_file': relation_output_path,
            'scene_file': scene_output_path,
            'message': 'AI解析成功'
        }
        
        return result
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'message': 'AI解析失败'
        }
        return error_result



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