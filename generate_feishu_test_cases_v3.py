#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import yaml
import logging
from datetime import datetime

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入飞书配置管理工具
from utils.feishu_config import feishu_config

# 设置日志
logging.basicConfig(level=logging.INFO)
INFO = logging.getLogger("info")
ERROR = logging.getLogger("error")

def generate_test_cases_tool(file_id: str) -> str:
    """
    根据file_id从路径uploads/openapi/{file_id}.yaml/.json获取API文档、
    从路径uploads/scene/{file_id}.json获取API文档测试场景、
    从路径uploads/relation/{file_id}.json获取API文档关联关系，然后根据
    测试场景、关联关系和API文档生成测试用例
    
    Args:
        file_id: 文件ID，用于构建API文档、测试场景、关联关系文件路径
        
    Returns:
        生成的测试用例的YAML文件路径
    """
    try:
        # 从配置中获取授权令牌和基础URL
        authorization = feishu_config.get_authorization()
        base_url = feishu_config.get_base_url()
        
        INFO.info("开始生成测试用例...")
        
        # 构建文件路径
        api_file_path = f"/Users/oss/code/PytestAutoApi/uploads/openapi/openapi_{file_id}.yaml"
        scene_file_path = f"/Users/oss/code/PytestAutoApi/uploads/scene/scene_{file_id}.json"
        relation_file_path = f"/Users/oss/code/PytestAutoApi/uploads/relation/relation_{file_id}.json"
        
        # 检查文件是否存在
        if not os.path.exists(api_file_path):
            raise FileNotFoundError(f"API文档文件不存在: {api_file_path}")
        
        # 加载API文档
        with open(api_file_path, 'r', encoding='utf-8') as f:
            if api_file_path.endswith('.yaml') or api_file_path.endswith('.yml'):
                doc_data = yaml.safe_load(f)
            else:
                doc_data = json.load(f)
        
        # 加载测试场景（如果存在）
        scenes_data = {}
        if os.path.exists(scene_file_path):
            with open(scene_file_path, 'r', encoding='utf-8') as f:
                scenes_data = json.load(f)
        
        # 加载API依赖关系（如果存在）
        relations_data = {}
        if os.path.exists(relation_file_path):
            with open(relation_file_path, 'r', encoding='utf-8') as f:
                relations_data = json.load(f)
        
        # 从场景文件中获取业务场景数据
        test_scenes_list = []
        if 'business_scenes' in scenes_data and 'scenes' in scenes_data['business_scenes']:
            test_scenes_list = scenes_data['business_scenes']['scenes']
        elif 'scenes_name' in scenes_data:
            # 兼容旧格式
            test_scenes_list = scenes_data['scenes_name']
        
        # 如果有关联关系数据，生成基于关联关系的测试场景
        if relations_data and 'relation_info' in relations_data:
            # 这里简化处理，实际项目中应该实现关联关系分析
            pass
        
        paths = doc_data.get('paths', {})
        
        # 创建YAML格式的测试用例
        yaml_test_cases = {
            "case_common": {
                "allureEpic": "消息发送与管理API",
                "allureFeature": "发送消息",
                "allureStory": "发送消息"
            }
        }
        
        # 为每个测试场景生成测试用例
        test_case_index = 1
        
        for scene in test_scenes_list:
            # 处理新格式的场景数据
            if 'scene_id' in scene:
                # 新格式场景数据
                scene_name = scene.get('scene_name', '')
                scene_description = scene.get('scene_description', '')
                scene_priority = scene.get('priority', 'P1').replace('P', '')  # 将P1转换为1
                related_apis = scene.get('related_apis', [])
                test_focus = scene.get('test_focus', [])
                exception_scenarios = scene.get('exception_scenarios', [])
                api_call_combo = scene.get('api_call_combo', [])
                
                # 从related_apis或api_call_combo中提取API路径和方法
                scene_path = ''
                scene_method = 'POST'  # 默认方法
                if related_apis:
                    scene_path = related_apis[0]
                elif api_call_combo:
                    scene_path = api_call_combo[0].get('api_path', '')
                
                # 根据路径确定HTTP方法
                if scene_path and scene_path in paths:
                    for method in paths[scene_path]:
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            scene_method = method.upper()
                            break
                
                # 创建兼容格式的场景对象
                scene_obj = {
                    'name': scene_name,
                    'description': scene_description,
                    'type': 'business_flow',  # 业务场景默认为业务流程类型
                    'path': scene_path,
                    'method': scene_method,
                    'priority': 'high' if scene_priority == '1' else 'medium' if scene_priority == '2' else 'low',
                    'test_focus': test_focus,
                    'exception_scenarios': exception_scenarios,
                    'api_call_combo': api_call_combo
                }
            else:
                # 旧格式场景数据
                scene_obj = scene
            
            scene_type = scene_obj.get('type', 'basic')
            scene_path = scene_obj.get('path', '')
            scene_method = scene_obj.get('method', '')
            
            # 获取对应的API定义
            api_definition = None
            if scene_path and scene_method and scene_path in paths:
                api_definition = paths[scene_path].get(scene_method.lower(), {})
            
            # 生成基础测试用例
            test_cases = []
            
            # 根据API路径生成特定的测试数据
            test_data = {}
            expected_results = {"status_code": 200}
            
            # 根据不同的API路径生成特定的测试数据
            if '/im/v1/messages' in scene_path:
                # 发送消息API的测试数据
                test_data = {
                    "receive_id_type": "open_id",
                    "receive_id": "ou_xxx",
                    "msg_type": "text",
                    "content": "{\"text\":\"测试消息\"}"
                }
                expected_results = {"status_code": 200, "response_contains": "success"}
            
            # 正常请求测试用例
            normal_case = {
                "name": f"正常请求 - {scene_method} {scene_path}",
                "description": f"测试{scene_method} {scene_path}的正常请求功能",
                "type": "normal",
                "priority": "high",
                "api_path": scene_path,
                "api_method": scene_method,
                "test_case_description": scene_obj.get('description', ''),
                "test_data": test_data,
                "expected_results": expected_results
            }
            test_cases.append(normal_case)
            
            # 异常场景测试用例
            for exception_scenario in scene_obj.get('exception_scenarios', []):
                exception_test_data = test_data.copy()
                exception_expected_results = {"status_code": 400}
                
                if "无效接收者ID" in exception_scenario:
                    exception_test_data["receive_id"] = "invalid_id"
                    exception_expected_results["feishu_code"] = 230013
                elif "空消息内容" in exception_scenario:
                    exception_test_data["content"] = "{\"text\":\"\"}"
                    exception_expected_results["feishu_code"] = 230025
                elif "无效图片key" in exception_scenario:
                    exception_test_data["content"] = "{\"image_key\":\"invalid_key\"}"
                    exception_expected_results["feishu_code"] = 300240
                
                exception_case = {
                    "name": f"异常请求 - {exception_scenario}",
                    "description": f"测试{scene_method} {scene_path}的{exception_scenario}异常场景",
                    "type": "exception",
                    "priority": "medium",
                    "api_path": scene_path,
                    "api_method": scene_method,
                    "test_case_description": f"测试{exception_scenario}异常场景",
                    "test_data": exception_test_data,
                    "expected_results": exception_expected_results
                }
                test_cases.append(exception_case)
            
            # 将测试用例转换为YAML格式
            for test_case in test_cases:
                # 从API路径生成测试用例键名
                api_path = test_case.get('api_path', scene_path)
                if api_path.startswith('/'):
                    api_path = api_path[1:]  # 去掉开头的斜杠
                # 将路径中的斜杠替换为下划线
                api_path_key = api_path.replace('/', '_')
                
                # 生成测试用例键名
                test_case_key = f"{test_case_index:02d}_{api_path_key}"
                
                # 构建YAML格式的测试用例
                yaml_test_case = {
                    "host": base_url,
                    "url": api_path,
                    "method": test_case.get('api_method', scene_method).lower(),
                    "detail": test_case.get('test_case_description', ''),
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {authorization}"
                    },
                    "requestType": "json",
                    "is_run": None,
                    "data": test_case.get('test_data', {}),
                    "dependence_case": False,
                    "assert": {
                        "status_code": test_case.get('expected_results', {}).get('status_code', 200)
                    },
                    "sql": None
                }
                
                # 添加飞书错误码（如果有）
                if 'feishu_code' in test_case.get('expected_results', {}):
                    yaml_test_case["assert"]["feishu_code"] = test_case['expected_results']['feishu_code']
                
                # 添加到YAML测试用例字典
                yaml_test_cases[test_case_key] = yaml_test_case
                test_case_index += 1
        
        # 确保输出目录存在
        output_dir = "/Users/oss/code/PytestAutoApi/uploads/test_cases"
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件路径
        output_file_path = f"{output_dir}/test_cases_{file_id}.yaml"
        
        # 写入YAML文件
        with open(output_file_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_test_cases, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        INFO.info(f"测试用例生成完成，共生成 {len(yaml_test_cases)-1} 个测试用例，保存到 {output_file_path}")
        
        result = {
            "status": "success",
            "message": f"成功生成 {len(yaml_test_cases)-1} 个测试用例",
            "file_path": output_file_path,
            "test_cases_count": len(yaml_test_cases)-1
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        ERROR.error(f"生成测试用例失败: {str(e)}")
        error_result = {
            "status": "error",
            "message": f"生成测试用例失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False)

def main():
    try:
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
        result = generate_test_cases_tool(file_id)
        
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