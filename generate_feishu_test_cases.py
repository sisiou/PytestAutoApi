#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.smart_auto.openapi_agent import OpenAPIAgent

def main():
    # 初始化OpenAPIAgent
    agent = OpenAPIAgent()
    
    # 指定file_id
    file_id = "feishu_server-docs_im-v1_message_create"
    
    # 调用generate_test_cases_tool函数生成测试用例
    print(f"正在为file_id: {file_id}生成测试用例...")
    result = agent.generate_test_cases_tool(file_id)
    
    # 解析结果
    result_data = json.loads(result)
    
    if result_data.get("status") == "success":
        print(f"测试用例生成成功!")
        print(f"生成了 {result_data.get('test_cases_count', 0)} 个测试用例")
        print(f"文件保存在: {result_data.get('file_path')}")
    else:
        print(f"测试用例生成失败: {result_data.get('message')}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())