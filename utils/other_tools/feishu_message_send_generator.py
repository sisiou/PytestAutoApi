#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书"发送消息"接口测试用例自动生成流程整合脚本

复用之前的方案，整合以下流程：
1. 生成 MessageSend.json（如果不存在）
2. 从 MessageSend.json 生成 YAML 用例文件
3. 启动飞书 OAuth 回调服务（后台）- 可选，用于获取 tenant_access_token
4. 生成授权链接，等待用户完成授权（可选）
5. 自动获取 tenant_access_token 并更新到 YAML（可选）
6. 生成 pytest 测试用例代码

使用方法：
    python utils/other_tools/feishu_message_send_generator.py
"""

import sys
import time
import threading
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
except ImportError:
    requests = None

from utils.read_files_tools.swagger_for_yaml import SwaggerForYaml
from utils.read_files_tools.case_automatic_control import TestCaseAutomaticGeneration

# ================= 手动配置区域 =================
# 为避免多处修改，这里提供默认的 app_id 和 app_secret
# 如果环境变量或 feishu_token_updater.py 没有配置，将回落到这里
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"
DEFAULT_APP_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"
# 可选：根据需要覆盖 receive_id_type / receive_id（也可通过环境变量注入）
DEFAULT_RECEIVE_ID_TYPE = "user_id"
DEFAULT_RECEIVE_ID = "49e646d6"
# =================================================

class FeishuMessageSendGenerator:
    """飞书发送消息接口测试用例生成器"""

    def __init__(self):
        self.message_send_json_path = Path("interfacetest/MessageSend.json")
        self.swagger_json_path = self.message_send_json_path  # 复用 SwaggerForYaml 的逻辑

    def step1_generate_json(self) -> None:
        """步骤1: 生成 MessageSend.json（如果不存在）"""
        print("\n" + "=" * 60)
        print("步骤 1/5: 生成 MessageSend.json")
        print("=" * 60)
        
        if self.message_send_json_path.exists():
            print(f"✓ MessageSend.json 已存在: {self.message_send_json_path}")
            print("  如需重新生成，请先删除该文件")
            return
        
        try:
            from utils.other_tools.generate_message_send_json import generate_message_send_json
            generate_message_send_json()
        except ImportError:
            print("✗ 错误: 无法导入 generate_message_send_json 模块")
            print("  请确保 utils/other_tools/generate_message_send_json.py 文件存在")
            sys.exit(1)
        except Exception as e:
            print(f"✗ 生成 MessageSend.json 时出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def step2_generate_yaml_from_swagger(self) -> None:
        """步骤2: 从 MessageSend.json 生成 YAML 用例文件"""
        print("\n" + "=" * 60)
        print("步骤 2/5: 从 MessageSend.json 生成 YAML 用例文件")
        print("=" * 60)
        
        if not self.message_send_json_path.exists():
            print(f"✗ 错误: 未找到 {self.message_send_json_path}")
            print("  请先运行步骤 1 生成该文件")
            sys.exit(1)
        
        try:
            # 创建一个自定义的 SwaggerForYaml 类，使用 MessageSend.json
            json_path = str(self.message_send_json_path)
            
            class MessageSendSwaggerForYaml(SwaggerForYaml):
                @classmethod
                def get_swagger_json(cls):
                    """获取 MessageSend.json 数据"""
                    try:
                        import json
                        with open(json_path, "r", encoding='utf-8') as f:
                            row_data = json.load(f)
                            return row_data
                    except FileNotFoundError:
                        raise FileNotFoundError(f"文件路径不存在: {json_path}")
                
                def get_allure_epic(self):
                    """重写方法以适配 MessageSend.json 格式"""
                    # MessageSend.json 的 title 在顶层，而不是 info.title
                    if 'title' in self._data:
                        return self._data['title']
                    # 如果格式是标准 Swagger，则使用原来的逻辑
                    elif 'info' in self._data and 'title' in self._data['info']:
                        return self._data['info']['title']
                    else:
                        return "飞书接口测试"
                
                def get_case_data(self, value):
                    """重写方法以处理 requestBody 数据并将 query 参数与 body 分离"""
                    from jsonpath import jsonpath
                    body_data: Dict[str, Any] = {}
                    query_params: Dict[str, Any] = {}
                    
                    # 处理 query 参数（parameters 中 in='query' 的）
                    if jsonpath(obj=value, expr="$.parameters") is not False:
                        _parameters = value['parameters']
                        for i in _parameters:
                            if i['in'] == 'query':
                                example_value = self._get_parameter_example(i)
                                query_params[i['name']] = example_value if example_value is not None else None
                            elif i['in'] != 'header':
                                example_value = self._get_parameter_example(i)
                                body_data[i['name']] = example_value if example_value is not None else None
                    
                    # 处理 requestBody 数据
                    if value.get('requestBody'):
                        request_body = value['requestBody']
                        content = request_body.get('content', {})
                        
                        # 查找 application/json 的 schema
                        if 'application/json' in content:
                            schema = content['application/json'].get('schema', {})
                            
                            # 如果有 $ref，需要解析引用
                            if '$ref' in schema:
                                ref_path = schema['$ref']
                                if ref_path.startswith('#/components/schemas/'):
                                    schema_name = ref_path.split('/')[-1]
                                    components = self._data.get('components', {})
                                    schemas = components.get('schemas', {})
                                    if schema_name in schemas:
                                        schema = schemas[schema_name]
                            
                            # 如果有 example，使用 example 的值
                            example = content['application/json'].get('example')
                            if example:
                                body_data.update(example)
                            else:
                                if 'properties' in schema:
                                    for prop_name in schema['properties'].keys():
                                        if prop_name not in body_data:
                                            body_data[prop_name] = None
                    
                    result = {
                        "__body__": body_data or None,
                        "__query__": query_params or None
                    }
                    return result
                
                def write_yaml_handler(self):
                    """重写写入逻辑，使 query 参数拼接到 URL，body 仅保留请求体"""
                    from urllib.parse import urlencode
                    import copy
                    
                    _api_data = self._data['paths']
                    for key, value in _api_data.items():
                        for k, v in value.items():
                            headers = self.get_headers(v)
                            request_type = self.get_request_type(v, headers)
                            case_data_struct = self.get_case_data(v)
                            
                            body_data = case_data_struct
                            query_params = None
                            if isinstance(case_data_struct, dict) and "__body__" in case_data_struct:
                                body_data = case_data_struct.get("__body__")
                                query_params = case_data_struct.get("__query__")
                            
                            final_url = key
                            if query_params:
                                if DEFAULT_RECEIVE_ID_TYPE:
                                    query_params["receive_id_type"] = DEFAULT_RECEIVE_ID_TYPE
                                filtered_params = {pk: pv for pk, pv in query_params.items() if pv not in (None, "")}
                                if filtered_params:
                                    final_url = f"{key}?{urlencode(filtered_params)}"
                            else:
                                if DEFAULT_RECEIVE_ID_TYPE:
                                    final_url = f"{key}?{urlencode({'receive_id_type': DEFAULT_RECEIVE_ID_TYPE})}"

                            # 基础 body 拷贝，确保多场景互不影响
                            base_body = copy.deepcopy(body_data) if isinstance(body_data, dict) else {}

                            # 覆盖 body 中的 receive_id（成功场景）
                            if isinstance(base_body, dict) and DEFAULT_RECEIVE_ID:
                                base_body["receive_id"] = DEFAULT_RECEIVE_ID

                            # 场景1：成功发送文本消息
                            scene1_body = copy.deepcopy(base_body)
                            scene1_body["msg_type"] = "text"
                            scene1_body["content"] = json.dumps({"text": "test content"}, ensure_ascii=False)

                            # 场景2：成功发送简单卡片消息（interactive）
                            scene2_body = copy.deepcopy(base_body)
                            scene2_body["msg_type"] = "interactive"
                            scene2_body["content"] = json.dumps(
                                {
                                    "elements": [
                                        {
                                            "tag": "markdown",
                                            "content": "自动化测试卡片\n\n这是一条由测试脚本发送的卡片消息"
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            )

                            # 场景3：receive_id 无效，预期 400（负向用例，对应错误码 230034 / 99992360）
                            scene3_body = copy.deepcopy(scene1_body)
                            scene3_body["receive_id"] = "invalid_receive_id_for_test"

                            # 场景4：msg_type 非法，预期 400（负向用例，对应参数错误 230001）
                            scene4_body = copy.deepcopy(base_body)
                            scene4_body["msg_type"] = "invalid_type_for_test"
                            scene4_body.setdefault("content", json.dumps({"text": "test content"}, ensure_ascii=False))

                            # 场景5：缺少 content，预期 400（负向用例，对应参数错误 230001）
                            scene5_body = copy.deepcopy(base_body)
                            scene5_body["msg_type"] = "text"
                            # 故意移除 content 字段，模拟缺少必填参数
                            if "content" in scene5_body:
                                scene5_body.pop("content")

                            # 场景6：content 为空字符串，预期 400（负向用例，对应参数错误 230001）
                            scene6_body = copy.deepcopy(base_body)
                            scene6_body["msg_type"] = "text"
                            scene6_body["content"] = ""

                            # 场景7：content 非 JSON 字符串，预期 400（负向用例，对应参数错误 230001）
                            scene7_body = copy.deepcopy(base_body)
                            scene7_body["msg_type"] = "text"
                            scene7_body["content"] = "not_a_json_string_for_test"

                            # 场景8：非法卡片内容，预期 400（负向用例，对应 230099 创建卡片失败）
                            scene8_body = copy.deepcopy(base_body)
                            scene8_body["msg_type"] = "interactive"
                            # 构造明显不符合卡片 schema 的内容
                            scene8_body["content"] = json.dumps(
                                {"invalid_card": True, "elements": "not_a_list"}, ensure_ascii=False
                            )

                            base_case_id = self.get_case_id(key)
                            yaml_data = {
                                "case_common": {
                                    "allureEpic": self.get_allure_epic(),
                                    "allureFeature": self.get_allure_feature(v),
                                    "allureStory": self.get_allure_story(v)
                                },
                                # 场景1：文本成功
                                base_case_id: {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 文本成功",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene1_body,
                                    "dependence_case": False,
                                    "assert": {"status_code": 200},
                                    "sql": None
                                },
                                # 场景2：卡片成功
                                base_case_id.replace("01", "02", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 卡片成功",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene2_body,
                                    "dependence_case": False,
                                    "assert": {"status_code": 200},
                                    "sql": None
                                },
                                # 场景3：无效 receive_id（接收人 ID 不存在）
                                base_case_id.replace("01", "03", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 无效接收人",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene3_body,
                                    "dependence_case": False,
                                    "assert": {
                                        "status_code": 400,
                                        # 实际线上返回为 99992360，这里按真实观测值做一一对应校验
                                        "feishu_code": 99992360,
                                    },
                                    "sql": None
                                },
                                # 场景4：msg_type 非法（请求参数错误）
                                base_case_id.replace("01", "04", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 非法消息类型",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene4_body,
                                    "dependence_case": False,
                                    "assert": {
                                        "status_code": 400,
                                        "feishu_code": 230001,
                                    },
                                    "sql": None
                                },
                                # 场景5：缺少 content（请求体缺少必填字段）
                                base_case_id.replace("01", "05", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 缺少内容字段",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene5_body,
                                    "dependence_case": False,
                                    # 实际观测缺少 content 返回 99992402（field validation failed）
                                    "assert": {
                                        "status_code": 400,
                                        "feishu_code": 99992402,
                                    },
                                    "sql": None
                                },
                                # 场景6：content 为空字符串
                                base_case_id.replace("01", "06", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 内容为空",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene6_body,
                                    "dependence_case": False,
                                    "assert": {
                                        "status_code": 400,
                                        "feishu_code": 230001,
                                    },
                                    "sql": None,
                                },
                                # 场景7：content 非 JSON 字符串
                                base_case_id.replace("01", "07", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 内容非JSON",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene7_body,
                                    "dependence_case": False,
                                    "assert": {
                                        "status_code": 400,
                                        "feishu_code": 230001,
                                    },
                                    "sql": None,
                                },
                                # 场景8：非法卡片内容（卡片内容创建失败）
                                base_case_id.replace("01", "08", 1): {
                                    "host": self._host,
                                    "url": final_url,
                                    "method": k,
                                    "detail": self.get_detail(v) + " - 非法卡片内容",
                                    "headers": headers,
                                    "requestType": request_type,
                                    "is_run": None,
                                    "data": scene8_body,
                                    "dependence_case": False,
                                    "assert": {
                                        "status_code": 400,
                                        "feishu_code": 230099,
                                    },
                                    "sql": None,
                                },
                            }
                            self.yaml_cases(yaml_data, file_path=key)
            
            # 使用自定义类
            swagger = MessageSendSwaggerForYaml()
            swagger.write_yaml_handler()
            print("✓ YAML 用例文件生成成功")
                
        except Exception as e:
            print(f"✗ 生成 YAML 文件时出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def get_tenant_access_token(self, app_id: str, app_secret: str) -> Optional[str]:
        """
        获取 tenant_access_token
        
        Args:
            app_id: 应用唯一标识
            app_secret: 应用秘钥
            
        Returns:
            tenant_access_token 字符串，失败返回 None
        """
        if requests is None:
            print("✗ 错误: 需要安装 requests 库才能获取 token")
            print("   请运行: pip install requests")
            return None
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                expire = data.get("expire", 0)
                print(f"✓ 成功获取 tenant_access_token")
                print(f"  过期时间: {expire} 秒 ({expire // 60} 分钟)")
                return token
            else:
                print(f"✗ 获取 tenant_access_token 失败")
                print(f"  错误码: {data.get('code')}")
                print(f"  错误信息: {data.get('msg', '未知错误')}")
                return None
        except Exception as e:
            print(f"✗ 获取 tenant_access_token 时出错: {e}")
            return None
    
    def update_yaml_with_token(self, yaml_path: Path, token: str) -> bool:
        """
        更新 YAML 文件中的 Authorization token
        
        Args:
            yaml_path: YAML 文件路径
            token: tenant_access_token
            
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            import ruamel.yaml
        except ImportError:
            print("✗ 错误: 需要安装 ruamel.yaml 库才能更新 YAML 文件")
            print("   请运行: pip install ruamel.yaml")
            return False
        
        try:
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            
            # 读取现有 YAML 文件
            if yaml_path.exists():
                with yaml_path.open("r", encoding="utf-8") as f:
                    data = yaml.load(f) or {}
            else:
                data = {}
            
            # 查找所有用例并更新 Authorization header
            updated = False
            for key, value in data.items():
                if key != "case_common" and isinstance(value, dict):
                    headers = value.get("headers") or {}
                    if isinstance(headers, dict):
                        headers["Authorization"] = f"Bearer {token}"
                        value["headers"] = headers
                        updated = True
            
            # 写回文件
            if updated:
                with yaml_path.open("w", encoding="utf-8") as f:
                    yaml.dump(data, f)
                print(f"✓ 已更新 YAML 文件: {yaml_path}")
                return True
            else:
                print(f"⚠ 警告: 未找到需要更新的用例配置")
                return False
                
        except Exception as e:
            print(f"✗ 更新 YAML 文件时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def step3_update_token_in_yaml(self) -> None:
        """步骤3: 更新 YAML 中的 tenant_access_token（可选）"""
        print("\n" + "=" * 60)
        print("步骤 3/5: 更新 YAML 中的 tenant_access_token（可选）")
        print("=" * 60)
        
        yaml_path = Path("data/open-apis/im/v1/messages.yaml")
        if not yaml_path.exists():
            print(f"⚠ 警告: 未找到 YAML 文件 {yaml_path}")
            print("   请确认步骤 2 是否成功执行")
            return
        
        # 尝试从环境变量或 feishu_token_updater.py 中获取 app_id 和 app_secret
        app_id = (
            os.getenv("FEISHU_APP_ID")
            or os.getenv("FEISHU_CLIENT_ID")
            or DEFAULT_APP_ID
        )
        app_secret = (
            os.getenv("FEISHU_APP_SECRET")
            or os.getenv("FEISHU_CLIENT_SECRET")
            or DEFAULT_APP_SECRET
        )
        
        # 如果环境变量中没有，尝试从 feishu_token_updater.py 读取
        if not app_id or not app_secret:
            try:
                token_updater_path = Path(__file__).parent / "feishu_token_updater.py"
                if token_updater_path.exists():
                    content = token_updater_path.read_text(encoding="utf-8")
                    # 简单提取 FEISHU_CLIENT_ID 和 FEISHU_CLIENT_SECRET
                    import re
                    id_match = re.search(r'FEISHU_CLIENT_ID\s*=\s*["\']([^"\']+)["\']', content)
                    secret_match = re.search(r'FEISHU_CLIENT_SECRET\s*=\s*["\']([^"\']+)["\']', content)
                    if id_match and not app_id:
                        app_id = id_match.group(1)
                    if secret_match and not app_secret:
                        app_secret = secret_match.group(1)
            except Exception:
                pass
        
        # 如果还是没有，提示用户输入
        if not app_id or not app_secret:
            print("\n提示: tenant_access_token 与 user_access_token 不同")
            print("     tenant_access_token 用于应用级别的接口调用")
            print("\n要自动获取 tenant_access_token，请提供以下信息：")
            print("方式1: 设置环境变量")
            print("      FEISHU_APP_ID=你的app_id")
            print("      FEISHU_APP_SECRET=你的app_secret")
            print("\n方式2: 在 feishu_token_updater.py 中配置 FEISHU_CLIENT_ID 和 FEISHU_CLIENT_SECRET")
            print("\n方式3: 手动在 YAML 文件中填写 tenant_access_token")
            print(f"     YAML 文件路径: {yaml_path}")
            
            # 询问用户是否要手动输入
            try:
                user_input = input("\n是否现在输入 app_id 和 app_secret 来获取 token? (y/n): ").strip().lower()
                if user_input == 'y':
                    if not app_id:
                        app_id = input("请输入 app_id: ").strip()
                    if not app_secret:
                        app_secret = input("请输入 app_secret: ").strip()
                else:
                    print("\n跳过自动获取 token，你可以在 YAML 文件中手动填写 tenant_access_token")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\n\n跳过自动获取 token")
                return
        
        # 获取 token
        if app_id and app_secret:
            token = self.get_tenant_access_token(app_id, app_secret)
            if token:
                # 更新 YAML 文件
                if self.update_yaml_with_token(yaml_path, token):
                    print("✓ tenant_access_token 已成功更新到 YAML 文件")
                else:
                    print("⚠ 获取 token 成功，但更新 YAML 文件失败")
                    print(f"   请手动将以下 token 填入 YAML 文件: Bearer {token}")
            else:
                print("\n⚠ 获取 token 失败，请手动在 YAML 文件中填写 tenant_access_token")
                print(f"   YAML 文件路径: {yaml_path}")
        else:
            print("\n⚠ 未提供 app_id 或 app_secret，跳过自动获取 token")
            print(f"   你可以在 YAML 文件中手动填写 tenant_access_token")
            print(f"   YAML 文件路径: {yaml_path}")

    def step4_generate_test_cases(self) -> None:
        """步骤4: 生成 pytest 测试用例代码"""
        print("\n" + "=" * 60)
        print("步骤 4/5: 生成 pytest 测试用例代码")
        print("=" * 60)
        
        try:
            generator = TestCaseAutomaticGeneration()
            generator.get_case_automatic()
            print("✓ pytest 测试用例代码生成成功")
        except Exception as e:
            print(f"✗ 生成测试用例时出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def step5_summary(self) -> None:
        """步骤5: 输出总结信息"""
        print("\n" + "=" * 60)
        print("步骤 5/5: 完成总结")
        print("=" * 60)
        
        yaml_path = Path("data/open-apis/im/v1/messages.yaml")
        test_case_path = Path("test_case/open-apis/im/v1/test_messages.py")
        
        print("\n生成的文件：")
        if yaml_path.exists():
            print(f"  ✓ YAML 用例文件: {yaml_path}")
        else:
            print(f"  ✗ YAML 用例文件: {yaml_path} (未找到)")
        
        if test_case_path.exists():
            print(f"  ✓ 测试用例代码: {test_case_path}")
        else:
            print(f"  ✗ 测试用例代码: {test_case_path} (未找到)")
        
        print("\n接下来你可以：")
        print("1. 如果需要重新刷新 token，可运行步骤 3 自动获取 tenant_access_token")
        print("   当前 YAML 文件已写入最新 token，如需覆盖请重新执行脚本或手动编辑：")
        print(f"   文件路径: {yaml_path}")
        print("   字段位置: headers.Authorization（格式: Bearer t-xxxxxxxxxxxxx）")
        print("\n2. 运行 pytest 测试用例:")
        if test_case_path.exists():
            print(f"   pytest {test_case_path} -s")
        else:
            print("   pytest test_case/open-apis/im/v1/test_messages.py -s")

    def update_test_messages_case_ids(self) -> None:
        """
        根据 messages.yaml 中的所有用例 ID，更新 test_messages.py 里的 case_id 列表，
        让 pytest 一次性覆盖多个场景。
        """
        try:
            from pathlib import Path
            import re
            try:
                import ruamel.yaml  # type: ignore[import]
            except ImportError:
                print("⚠ 未安装 ruamel.yaml，无法自动更新 test_messages.py 的 case_id，多场景请手动维护。")
                return

            yaml_path = Path("data/open-apis/im/v1/messages.yaml")
            test_path = Path("test_case/open-apis/im/v1/test_messages.py")

            if not yaml_path.exists() or not test_path.exists():
                return

            yaml = ruamel.yaml.YAML()
            data = yaml.load(yaml_path.read_text(encoding="utf-8")) or {}

            # 收集所有 case_id（除 case_common 以外的 key）
            case_ids = [k for k in data.keys() if k != "case_common"]
            if not case_ids:
                return

            content = test_path.read_text(encoding="utf-8")
            pattern = r"case_id\s*=\s*\[.*?\]"
            replacement = f"case_id = {case_ids!r}"

            new_content, count = re.subn(pattern, replacement, content, count=1)
            if count == 1:
                test_path.write_text(new_content, encoding="utf-8")
                print(f"✓ 已更新 test_messages.py 中的 case_id，当前用例数: {len(case_ids)}")
            else:
                print("⚠ 未能在 test_messages.py 中找到 case_id 定义，跳过自动更新。")
        except Exception as e:  # noqa: BLE001
            print(f"⚠ 自动更新 test_messages.py case_id 时出错: {e}")
    def run_all(self) -> None:
        """执行完整流程"""
        print("\n" + "=" * 60)
        print('飞书"发送消息"接口测试用例自动生成流程')
        print("=" * 60)
        print("\n本脚本将自动执行以下步骤：")
        print("1. 生成 MessageSend.json（如果不存在）")
        print("2. 从 MessageSend.json 生成 YAML 用例文件")
        print("3. 提示更新 tenant_access_token（可选）")
        print("4. 生成 pytest 测试用例代码")
        print("5. 输出总结信息")
        print("\n开始执行...\n")
        
        try:
            # 步骤1: 生成 JSON
            self.step1_generate_json()
            
            # 步骤2: 生成 YAML
            self.step2_generate_yaml_from_swagger()
            
            # 步骤3: 更新 token（可选）
            self.step3_update_token_in_yaml()
            
            # 步骤4: 生成测试用例
            self.step4_generate_test_cases()

            # 更新 test_messages.py 中的 case_id，使其覆盖 messages.yaml 中的多个场景
            self.update_test_messages_case_ids()
            
            # 步骤5: 总结
            self.step5_summary()
            
            print("\n" + "=" * 60)
            print("✓ 所有步骤执行完成！")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n用户中断，正在退出...")
            sys.exit(0)
        except Exception as e:
            print(f"\n✗ 执行过程中出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """主函数"""
    generator = FeishuMessageSendGenerator()
    generator.run_all()


if __name__ == "__main__":
    main()

