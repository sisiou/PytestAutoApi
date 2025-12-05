import requests
from urllib.parse import quote
import json
import os

def transform_feishu_url(original_url):
    """
    将飞书文档URL转换为API格式

    规则：
    1. 提取 /document 之后的路径（如：server-docs/contact-v3/user/create）
    2. 在路径前添加 / 并进行URL编码（/ 变为 %2F）
    3. 拼接到新的API端点

    返回:
        new_url: 转换后的API URL
        path: /document 之后的路径（用于生成文件名）
    """
    # 提取 /document 之后的路径
    path_start = original_url.find('/document/') + len('/document/')
    path = original_url[path_start:]

    # 对路径进行URL编码（将 / 编码为 %2F）
    # 先添加前导斜杠，然后编码
    encoded_path = quote('/' + path, safe='')

    # 构建新的API URL
    base_url = "https://open.feishu.cn/document_portal/v1/document/get_detail"
    new_url = f"{base_url}?fullPath={encoded_path}"

    return new_url, path


def is_file_exist(file_path):
    """
    判断文件是否存在

    返回:
        bool: 文件存在返回True，不存在返回False
    """
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        print(f"文件已存在（{file_size} 字节），跳过下载: {file_path}")
        return True
    return False

def download_json(url, output_file=None):
    """
    从URL下载JSON数据

    Args:
        url: 要请求的URL
        output_file: 可选，保存JSON的文件路径
    """

    if output_file and is_file_exist(output_file):
        # TODO
        return

    try:
        # 发送GET请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # 检查请求是否成功

        # 解析JSON
        data = response.json()

        # 打印JSON内容
        print("成功获取JSON数据:")
        # print(json.dumps(data, ensure_ascii=False, indent=2))

        # 保存到文件（如果指定了）
        if output_file:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n数据已保存到: {output_file}")

        return data

    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return None


# 使用示例
if __name__ == "__main__":
    # 原始URL
    # original_url = "https://open.feishu.cn/document/server-docs/contact-v3/user/create"
    original_url = input("请输入网址：")
    original_url = original_url.split('?')[0]

    # 转换URL并获取路径
    api_url, path = transform_feishu_url(original_url)
    print(f"原始URL: {original_url}")
    print(f"转换后的API URL: {api_url}")

    # 生成文件名：将路径中的 / 替换为 _
    # filename = path.replace('/', '_') + '.json'
    # 保存到api目录下
    filename = os.path.join('../../api', path.replace('/', '_') + '.json')
    print(f"生成的文件名: {filename}")
    print("-" * 50)

    # 下载JSON并保存
    data = download_json(api_url, filename)