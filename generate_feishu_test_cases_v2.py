#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import yaml

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.smart_auto.openapi_agent import OpenAPIAgent

def main():
    try:
        # 创建OpenAPIAgent实例，但只使用generate_test_cases_tool方法
        agent = OpenAPIAgent()
        
        # 指定file_id
        file_id = "feishu_server-docs_im-v1_message_create"
        
        # 检查必要的文件是否存在
        api_file_path = f"/Users/oss/code/PytestAutoApi/uploads/openapi/openapi_{file_id}.yaml"
        scene_file_path = f"/Users/oss/code/PytestAutoApi/uploads/scene/scene_{file_id}.json"
        relation_file_path = f"/Users/oss/code/PytestAutoApi/uploads/relation/relation_{file_id}.json"
        
        print(f"检查文件是否存在...")
        print(f"API文档文件: {api_file_path} - {'存在' if os.path.exists(api_file_path) else '不存在'}")
        print(f"场景文件: {scene_file_path} - {'存在' if os.path.exists(scene_file_path) else '不存在'}")
        print(f"关系文件: {relation_file_path} - {'存在' if os.path.exists(relation_file_path) else '不存在'}")
        
        # 如果场景文件不存在，创建一个默认的场景文件
        if not os.path.exists(scene_file_path):
            print(f"创建默认场景文件: {scene_file_path}")
            os.makedirs(os.path.dirname(scene_file_path), exist_ok=True)
            
            # 创建默认场景数据
            default_scene = {
                "business_scenes": {
                    "scenes": [
                        {
                            "scene_id": "scene_001",
                            "scene_name": "发送文本消息",
                            "scene_description": "测试向用户发送文本消息的功能",
                            "priority": "P1",
                            "related_apis": ["/im/v1/messages"],
                            "test_focus": ["功能正确性", "参数验证"],
                            "exception_scenarios": ["无效接收者ID", "空消息内容"],
                            "api_call_combo": [
                                {
                                    "api_path": "/im/v1/messages",
                                    "method": "POST",
                                    "params": {
                                        "receive_id_type": "open_id",
                                        "msg_type": "text",
                                        "content": "{\"text\":\"测试消息\"}"
                                    }
                                }
                            ]
                        },
                        {
                            "scene_id": "scene_002",
                            "scene_name": "发送图片消息",
                            "scene_description": "测试向用户发送图片消息的功能",
                            "priority": "P1",
                            "related_apis": ["/im/v1/messages"],
                            "test_focus": ["功能正确性", "参数验证"],
                            "exception_scenarios": ["无效图片key", "过期图片key"],
                            "api_call_combo": [
                                {
                                    "api_path": "/im/v1/messages",
                                    "method": "POST",
                                    "params": {
                                        "receive_id_type": "open_id",
                                        "msg_type": "image",
                                        "content": "{\"image_key\":\"test_image_key\"}"
                                    }
                                }
                            ]
                        },
                        {
                            "scene_id": "scene_003",
                            "scene_name": "发送卡片消息",
                            "scene_description": "测试向用户发送交互式卡片消息的功能",
                            "priority": "P1",
                            "related_apis": ["/im/v1/messages"],
                            "test_focus": ["功能正确性", "参数验证"],
                            "exception_scenarios": ["无效卡片格式", "卡片内容过长"],
                            "api_call_combo": [
                                {
                                    "api_path": "/im/v1/messages",
                                    "method": "POST",
                                    "params": {
                                        "receive_id_type": "open_id",
                                        "msg_type": "interactive",
                                        "content": "{\"elements\":[{\"tag\":\"div\",\"text\":{\"tag\":\"plain_text\",\"content\":\"测试卡片\"}}]}"
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
            
            with open(scene_file_path, 'w', encoding='utf-8') as f:
                json.dump(default_scene, f, ensure_ascii=False, indent=2)
        
        # 调用generate_test_cases_tool函数生成测试用例
        print(f"正在为file_id: {file_id}生成测试用例...")
        result = agent.generate_test_cases_tool(file_id)
        
        # 解析结果
        result_data = json.loads(result)
        
        if result_data.get("status") == "success":
            print(f"测试用例生成成功!")
            print(f"生成了 {result_data.get('test_cases_count', 0)} 个测试用例")
            print(f"文件保存在: {result_data.get('file_path')}")
            
            # 显示生成的测试用例文件内容
            output_file_path = result_data.get('file_path')
            if os.path.exists(output_file_path):
                print("\n生成的测试用例内容预览:")
                with open(output_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(content[:1000] + "..." if len(content) > 1000 else content)
        else:
            print(f"测试用例生成失败: {result_data.get('message')}")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())