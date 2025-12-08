import yaml
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_openapi_file(file_path: str) -> Dict[str, Any]:
    """加载 OpenAPI YAML 或 JSON 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return yaml.safe_load(f)
        elif file_path.endswith('.json'):
            return json.load(f)
        else:
            raise ValueError("不支持的文件格式，仅支持 YAML(.yaml/.yml) 和 JSON(.json)")


def extract_components_for_path(openapi: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
    """提取指定接口路径和方法所需的组件"""
    components = openapi.get('components', {})
    if not components:
        return {}

    # 获取接口的请求和响应定义
    path_item = openapi['paths'][path][method]
    req_schema_ref = path_item.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema',
                                                                                                         {}).get('$ref')
    responses = path_item.get('responses', {})

    # 收集所有需要的引用
    required_refs = set()
    if req_schema_ref:
        required_refs.add(req_schema_ref)

    for resp in responses.values():
        content = resp.get('content', {}).get('application/json', {})
        schema = content.get('schema', {})
        if '$ref' in schema:
            required_refs.add(schema['$ref'])
        # 处理 allOf 结构
        if 'allOf' in schema:
            for item in schema['allOf']:
                if '$ref' in item:
                    required_refs.add(item['$ref'])

    # 提取需要的组件
    filtered_components = {'schemas': {}}
    for ref in required_refs:
        # 解析引用路径，如 #/components/schemas/Calendar
        parts = ref.split('/')
        if len(parts) < 4 or parts[0] != '#' or parts[1] != 'components' or parts[2] != 'schemas':
            continue
        schema_name = parts[3]
        if schema_name in components['schemas']:
            filtered_components['schemas'][schema_name] = components['schemas'][schema_name]
            # 检查嵌套引用
            nested_refs = find_nested_refs(components['schemas'][schema_name])
            for nested_ref in nested_refs:
                nested_parts = nested_ref.split('/')
                if len(nested_parts) >= 4 and nested_parts[2] == 'schemas':
                    nested_schema = nested_parts[3]
                    if nested_schema not in filtered_components['schemas'] and nested_schema in components['schemas']:
                        filtered_components['schemas'][nested_schema] = components['schemas'][nested_schema]

    # 保留安全方案
    if 'securitySchemes' in components:
        filtered_components['securitySchemes'] = components['securitySchemes']

    return filtered_components


def find_nested_refs(schema: Any) -> List[str]:
    """查找嵌套在 schema 中的引用"""
    refs = []
    if isinstance(schema, dict):
        if '$ref' in schema:
            refs.append(schema['$ref'])
        for key, value in schema.items():
            refs.extend(find_nested_refs(value))
    elif isinstance(schema, list):
        for item in schema:
            refs.extend(find_nested_refs(item))
    return refs


def get_output_dir(input_file_path: str, base_output_path: str = None) -> str:
    """
    获取输出文件夹路径
    :param input_file_path: 输入文件路径
    :param base_output_path: 基础输出路径（可选）
    :return: 完整的输出文件夹路径
    """
    # 提取输入文件名（不含扩展名）作为子文件夹名
    file_name = os.path.splitext(os.path.basename(input_file_path))[0]

    # 如果指定了基础输出路径，拼接路径；否则使用当前目录
    if base_output_path:
        output_dir = os.path.join(base_output_path, file_name)
    else:
        output_dir = file_name

    return output_dir


def split_openapi(openapi: Dict[str, Any], input_file_path: str, base_output_path: str = None) -> Tuple[str, int]:
    """
    将 OpenAPI 文档拆分为单个接口文件
    :param openapi: 加载的OpenAPI数据
    :param input_file_path: 输入文件路径
    :param base_output_path: 基础输出路径（可选）
    :return: (输出文件夹路径, 生成的文件数量)
    """
    # 获取输出目录（支持指定基础路径）
    output_dir = get_output_dir(input_file_path, base_output_path)
    # 初始化生成文件计数器
    generated_count = 0

    # 如果文件夹存在则清空，不存在则创建
    if os.path.exists(output_dir):
        # 清空文件夹内容
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
    else:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 基础信息（不包含info，info将在每个接口中单独设置）
    base_info = {
        'openapi': openapi.get('openapi', '3.0.0'),
        'servers': openapi.get('servers', []),
        'tags': openapi.get('tags', [])
    }

    # 处理每个路径和方法
    for path, path_item in openapi.get('paths', {}).items():
        for method, operation in path_item.items():
            # 跳过非 HTTP 方法（如 parameters）
            if method not in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                continue

            # 创建单个接口的 OpenAPI 文档
            single_api = base_info.copy()

            # 替换info为当前接口的summary和description
            single_api['info'] = {
                'title': operation.get('summary', '未命名接口'),
                'description': operation.get('description', ''),
                'version': openapi.get('info', {}).get('version', '1.0.0')  # 保留原版本号
            }

            # 提取必要的组件
            components = extract_components_for_path(openapi, path, method)
            if components:
                single_api['components'] = components

            # 添加安全配置
            if 'security' in openapi:
                single_api['security'] = openapi['security']

            # 添加当前接口路径
            single_api['paths'] = {
                path: {
                    method: operation
                }
            }

            # 生成文件名（使用 operationId 或路径+方法）
            operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').strip('_')}")
            filename = f"{operation_id}.yaml"
            output_path = os.path.join(output_dir, filename)

            # 保存为 YAML 文件
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(single_api, f, allow_unicode=True, sort_keys=False)

            print(f"已生成: {output_path}")
            # 计数器加1
            generated_count += 1

    return output_dir, generated_count  # 返回输出文件夹路径和生成数量


def split_all(input_file_path: str, base_output_path: str = None) -> Tuple[str, int]:
    """
    完整的OpenAPI拆分流程
    :param input_file_path: 输入文件路径
    :param base_output_path: 基础输出路径（可选）
    :return: (输出文件夹路径, 生成的文件数量)
    """
    try:
        # 加载OpenAPI文件
        openapi_data = load_openapi_file(input_file_path)
        # 拆分OpenAPI文档（支持指定输出路径）
        output_dir, generated_count = split_openapi(openapi_data, input_file_path, base_output_path)
        print(f"拆分完成! 接口文件已保存至: {output_dir}，共生成 {generated_count} 个文件")
        return output_dir, generated_count
    except Exception as e:
        print(f"处理失败: {str(e)}")
        raise  # 抛出异常让调用方处理


# Flask接口集成示例（和之前的上传接口整合）
def integrate_with_upload_api(file_path, target_path=None) -> Tuple[str, int]:
    """
    集成到上传接口的处理函数
    :param file_path: 上传文件的路径
    :param target_path: 指定的目标存储路径
    :return: (拆分后的文件夹路径, 生成的文件数量)
    """
    try:
        # 移除：不再拼接file_basename，直接使用target_path作为基础路径
        if target_path:
            split_base_path = target_path  # 直接使用传入的目标路径，不额外拼接
        else:
            # 使用默认路径（原有逻辑不变）
            from flask import current_app
            split_base_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                          os.path.splitext(os.path.basename(file_path))[0])

        # 执行拆分
        split_dir, generated_count = split_all(file_path, split_base_path)
        return split_dir, generated_count
    except Exception as e:
        print(f"集成拆分功能失败: {str(e)}")
        return None, 0


if __name__ == "__main__":
    # 示例1：默认路径拆分
    # file_path = "D:/Study/pytestauto/openApi/openapi_bailian_da093a41.yaml"
    # output_dir, count = split_all(file_path)
    # print(f"输出目录: {output_dir}, 生成文件数量: {count}")

    # 示例2：指定基础路径拆分
    file_path = "D:/Study/pytestauto/openApi/openapi_bailian_da093a41.yaml"
    base_output_path = "D:/Study/pytestauto/uploads/openapi"  # 指定存储路径
    output_dir, count = split_all(file_path, base_output_path)
    print(f"输出目录: {output_dir}, 生成文件数量: {count}")