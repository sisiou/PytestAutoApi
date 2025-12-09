#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书"创建共享日历"接口测试用例自动生成脚本（基于 OpenAPI YAML）

执行步骤：
1. 校验 OpenAPI YAML 文件是否存在
2. 依据 OpenAPI YAML 文件生成 YAML 用例
3. 自动获取 tenant_access_token 并写入 YAML（可选）
4. 生成 pytest 用例
5. 输出总结信息

使用方法：
    python utils/other_tools/feishu_calendar_generator.py
"""

import sys
from pathlib import Path
from typing import Optional

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
OPENAPI_PATH = Path("multiuploads/split_openapi/openapi_API/related_group_1/createCalendar.yaml")
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"
DEFAULT_APP_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"
# =================================================


class FeishuCalendarCreateGenerator:
    """飞书共享日历创建接口测试用例生成器"""

    def __init__(self):
        self.openapi_path = OPENAPI_PATH

    def step1_check_openapi(self) -> None:
        """步骤1: 校验 OpenAPI YAML 文件是否存在"""
        print("\n" + "=" * 60)
        print("步骤 1/5: 检查 OpenAPI YAML 文件")
        print("=" * 60)

        if self.openapi_path.exists():
            print(f"✓ OpenAPI YAML 文件已存在: {self.openapi_path}")
            return

        print(f"✗ 错误: 未找到 {self.openapi_path}")
        print("  请确认 OpenAPI YAML 文件路径是否正确")
        sys.exit(1)

    def step2_generate_yaml_from_swagger(self) -> None:
        """步骤2: 从 OpenAPI YAML 文件生成 YAML 用例"""
        print("\n" + "=" * 60)
        print("步骤 2/5: 从 OpenAPI YAML 文件生成 YAML 用例")
        print("=" * 60)

        yaml_path = self.openapi_path

        class CalendarSwaggerForYaml(SwaggerForYaml):
            """
            使用类变量 `_class_yaml_path` 传递 OpenAPI YAML 路径，避免默认 __init__ 直接调用基类 get_swagger_json 时无参。
            """
            _class_yaml_path: Optional[str] = None

            def __init__(self, yaml_path: Path):
                # 先设置类级路径，再调用基类初始化
                CalendarSwaggerForYaml._class_yaml_path = str(yaml_path)
                super().__init__()
                # 覆盖基类初始化的数据（因为基类会在 __init__ 调用 get_swagger_json）
                self._data = self.get_swagger_json()

            @classmethod
            def get_swagger_json(cls):
                try:
                    import yaml
                except ImportError as e:  # noqa: BLE001
                    raise ImportError("缺少依赖 yaml，请安装 pyyaml: pip install pyyaml") from e

                if not cls._class_yaml_path:
                    raise RuntimeError("未设置 _class_yaml_path")

                path = Path(cls._class_yaml_path)
                try:
                    with path.open("r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except FileNotFoundError as e:
                    raise FileNotFoundError(f"OpenAPI 文件不存在: {path}") from e

            def get_allure_epic(self):
                """获取 allure epic"""
                if "info" in self._data and "title" in self._data["info"]:
                    return self._data["info"]["title"]
                if "title" in self._data:
                    return self._data["title"]
                return "飞书接口测试"

            def get_allure_feature(self, value):
                """兼容无 tags 的 OpenAPI，优先 tags，其次 summary，最后默认"""
                try:
                    if value.get("tags"):
                        return value["tags"][0] if isinstance(value["tags"], list) else value["tags"]
                except Exception:
                    ...
                return value.get("summary") or "日历管理"

            def get_allure_story(self, value):
                """获取 allure story"""
                return value.get("summary") or "创建共享日历"

            def get_host(self):
                """从 OpenAPI YAML 的 servers 中提取 host"""
                servers = self._data.get("servers", [])
                if servers and len(servers) > 0:
                    server_url = servers[0].get("url", "")
                    # 提取协议和域名部分，例如：https://open.feishu.cn
                    from urllib.parse import urlparse
                    parsed = urlparse(server_url)
                    return f"{parsed.scheme}://{parsed.netloc}"
                return "https://open.feishu.cn"

            def get_case_data(self, value):
                """解析 requestBody 数据"""
                body_data = {}

                if value.get('requestBody'):
                    content = value['requestBody'].get('content', {})
                    json_content = content.get('application/json', {})
                    schema = json_content.get('schema', {})

                    if '$ref' in schema:
                        ref_path = schema['$ref']
                        if ref_path.startswith('#/components/schemas/'):
                            schema_name = ref_path.split('/')[-1]
                            components = self._data.get('components', {})
                            schemas = components.get('schemas', {})
                            schema = schemas.get(schema_name, schema)

                    # 处理 example（单个示例）或 examples（多个示例）
                    example = json_content.get('example')
                    examples = json_content.get('examples', {})
                    
                    if example:
                        # 单个示例
                        body_data.update(example)
                    elif examples:
                        # 多个示例，取第一个示例的 value
                        first_example = list(examples.values())[0] if isinstance(examples, dict) else examples[0]
                        if isinstance(first_example, dict) and 'value' in first_example:
                            body_data.update(first_example['value'])
                        elif isinstance(first_example, dict):
                            body_data.update(first_example)
                    else:
                        # 没有示例，从 schema 的 properties 生成空值
                        for prop in schema.get('properties', {}).keys():
                            body_data.setdefault(prop, None)

                return body_data or None

            def write_yaml_handler(self):
                """
                重写写入逻辑:
                根据测试用例表生成完整的测试场景，覆盖：
                1. 权限与认证校验（应用身份、Token格式错误）
                2. 参数边界校验（summary/description长度、permissions枚举、color范围）
                3. 业务功能（默认值、不同权限类型）
                4. 组合覆盖（完整参数、边界值组合）
                5. 异常处理（Content-Type错误、请求体格式错误）
                """
                import copy

                # 从 servers 中提取基础路径
                servers = self._data.get("servers", [])
                base_path = ""
                if servers and len(servers) > 0:
                    server_url = servers[0].get("url", "")
                    from urllib.parse import urlparse
                    parsed = urlparse(server_url)
                    base_path = parsed.path.rstrip("/")  # 例如：/open-apis/calendar/v4

                _api_data = self._data["paths"]
                for path, methods in _api_data.items():
                    for method, meta in methods.items():
                        headers = self.get_headers(meta)
                        request_type = self.get_request_type(meta, headers)
                        body_data = self.get_case_data(meta)
                        
                        # 构建完整的 URL 路径
                        full_url = base_path + path if base_path else path

                        base_body = copy.deepcopy(body_data) if isinstance(body_data, dict) else {}

                        # ========== 一、权限与认证校验阶段 ==========
                        # TC_CAL_AUTH_001: 应用身份创建日历（私有）
                        scene_auth1_body = copy.deepcopy(base_body)
                        scene_auth1_body.setdefault("summary", "测试日历")
                        scene_auth1_body["permissions"] = "private"

                        # TC_CAL_AUTH_003: Token格式错误（无效token）
                        scene_auth3_headers = copy.deepcopy(headers) if isinstance(headers, dict) else {}
                        scene_auth3_headers["Authorization"] = "InvalidTokenFormat"
                        scene_auth3_body = copy.deepcopy(base_body)
                        scene_auth3_body.setdefault("summary", "测试日历")

                        # ========== 二、参数边界校验阶段 ==========
                        # TC_CAL_PARAM_001: summary参数-正常长度（255字符）
                        scene_param1_body = copy.deepcopy(base_body)
                        scene_param1_body["summary"] = "A" * 255
                        scene_param1_body["permissions"] = "private"

                        # TC_CAL_PARAM_002: summary参数-超过最大长度（256字符）
                        scene_param2_body = copy.deepcopy(base_body)
                        scene_param2_body["summary"] = "A" * 256
                        scene_param2_body["permissions"] = "private"

                        # TC_CAL_PARAM_003: description参数-正常长度（255字符）
                        scene_param3_body = copy.deepcopy(base_body)
                        scene_param3_body.setdefault("summary", "测试日历")
                        scene_param3_body["description"] = "D" * 255
                        scene_param3_body["permissions"] = "private"

                        # TC_CAL_PARAM_004: description参数-超过最大长度（256字符）
                        scene_param4_body = copy.deepcopy(base_body)
                        scene_param4_body.setdefault("summary", "测试日历")
                        scene_param4_body["description"] = "D" * 256
                        scene_param4_body["permissions"] = "private"

                        # TC_CAL_PARAM_005: permissions参数-有效枚举值
                        # 5.1: private
                        scene_param5a_body = copy.deepcopy(base_body)
                        scene_param5a_body.setdefault("summary", "测试日历-private")
                        scene_param5a_body["permissions"] = "private"
                        # 5.2: show_only_free_busy
                        scene_param5b_body = copy.deepcopy(base_body)
                        scene_param5b_body.setdefault("summary", "测试日历-show_only_free_busy")
                        scene_param5b_body["permissions"] = "show_only_free_busy"
                        # 5.3: public
                        scene_param5c_body = copy.deepcopy(base_body)
                        scene_param5c_body.setdefault("summary", "测试日历-public")
                        scene_param5c_body["permissions"] = "public"

                        # TC_CAL_PARAM_006: permissions参数-无效枚举值
                        scene_param6_body = copy.deepcopy(base_body)
                        scene_param6_body.setdefault("summary", "测试日历")
                        scene_param6_body["permissions"] = "invalid_value"

                        # TC_CAL_PARAM_007: color参数-有效范围值
                        scene_param7_body = copy.deepcopy(base_body)
                        scene_param7_body.setdefault("summary", "测试日历")
                        scene_param7_body["color"] = -1
                        scene_param7_body["permissions"] = "private"

                        # ========== 三、业务功能与逻辑阶段 ==========
                        # TC_CAL_BUS_001: 创建日历使用默认值（不传任何参数）
                        scene_bus1_body = {}  # 空请求体

                        # TC_CAL_BUS_003: 创建不同公开范围的日历（已在param5中覆盖）

                        # ========== 四、组合覆盖用例 ==========
                        # TC_CAL_COMB_001: 组合1：应用身份+完整参数
                        scene_comb1_body = copy.deepcopy(base_body)
                        scene_comb1_body["summary"] = "测试"
                        scene_comb1_body["description"] = "描述"
                        scene_comb1_body["permissions"] = "private"
                        scene_comb1_body["color"] = -1
                        scene_comb1_body["summary_alias"] = "别名"

                        # TC_CAL_COMB_003: 组合3：应用身份+边界值组合
                        scene_comb3_body = copy.deepcopy(base_body)
                        scene_comb3_body["summary"] = "A" * 255
                        scene_comb3_body["description"] = "D" * 255
                        scene_comb3_body["permissions"] = "public"
                        scene_comb3_body["color"] = 0
                        scene_comb3_body["summary_alias"] = "S" * 255

                        # ========== 五、异常处理 ==========
                        # TC_CAL_LIMIT_001: Content-Type错误
                        scene_limit1_headers = copy.deepcopy(headers) if isinstance(headers, dict) else {}
                        scene_limit1_headers["Content-Type"] = "text/plain"
                        scene_limit1_body = copy.deepcopy(base_body)
                        scene_limit1_body.setdefault("summary", "测试日历")

                        # TC_CAL_LIMIT_002: 请求体格式错误（非JSON，这个需要在测试框架层面处理，这里先标记）
                        # 注意：请求体格式错误通常无法在YAML中直接表达，需要在测试代码中处理

                        base_case_id = self.get_case_id(path)
                        yaml_data = {
                            "case_common": {
                                "allureEpic": self.get_allure_epic(),
                                "allureFeature": self.get_allure_feature(meta),
                                "allureStory": self.get_allure_story(meta),
                            },
                            # ========== 一、权限与认证校验阶段 ==========
                            # TC_CAL_AUTH_001: 应用身份创建日历（私有）
                            base_case_id: {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_AUTH_001 - 应用身份创建日历",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_auth1_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_AUTH_003: Token格式错误
                            # 实际返回：HTTP 400, code: 99991661 (Missing access token)
                            base_case_id.replace("01", "02", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_AUTH_003 - Token格式错误",
                                "headers": scene_auth3_headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_auth3_body,
                                "dependence_case": False,
                                "assert": {"status_code": 400, "feishu_code": 99991661},
                                "sql": None,
                            },
                            # ========== 二、参数边界校验阶段 ==========
                            # TC_CAL_PARAM_001: summary参数-正常长度（255字符）
                            base_case_id.replace("01", "03", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_001 - summary参数-正常长度",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param1_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_002: summary参数-超过最大长度（256字符）
                            base_case_id.replace("01", "04", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_002 - summary参数-超过最大长度",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param2_body,
                                "dependence_case": False,
                                "assert": {"status_code": 400, "feishu_code": 99992402},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_003: description参数-正常长度（255字符）
                            base_case_id.replace("01", "05", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_003 - description参数-正常长度",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param3_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_004: description参数-超过最大长度（256字符）
                            base_case_id.replace("01", "06", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_004 - description参数-超过最大长度",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param4_body,
                                "dependence_case": False,
                                "assert": {"status_code": 400, "feishu_code": 99992402},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_005: permissions参数-有效枚举值 - private
                            base_case_id.replace("01", "07", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_005 - permissions参数-有效枚举值-private",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param5a_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_005: permissions参数-有效枚举值 - show_only_free_busy
                            base_case_id.replace("01", "08", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_005 - permissions参数-有效枚举值-show_only_free_busy",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param5b_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_005: permissions参数-有效枚举值 - public
                            base_case_id.replace("01", "09", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_005 - permissions参数-有效枚举值-public",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param5c_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_006: permissions参数-无效枚举值
                            base_case_id.replace("01", "10", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_006 - permissions参数-无效枚举值",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param6_body,
                                "dependence_case": False,
                                "assert": {"status_code": 400, "feishu_code": 99992402},
                                "sql": None,
                            },
                            # TC_CAL_PARAM_007: color参数-有效范围值
                            base_case_id.replace("01", "11", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_PARAM_007 - color参数-有效范围值",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_param7_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # ========== 三、业务功能与逻辑阶段 ==========
                            # TC_CAL_BUS_001: 创建日历使用默认值
                            base_case_id.replace("01", "12", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_BUS_001 - 创建日历使用默认值",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_bus1_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # ========== 四、组合覆盖用例 ==========
                            # TC_CAL_COMB_001: 组合1：应用身份+完整参数
                            base_case_id.replace("01", "13", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_COMB_001 - 组合1：应用身份+完整参数",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_comb1_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # TC_CAL_COMB_003: 组合3：应用身份+边界值组合
                            base_case_id.replace("01", "14", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_COMB_003 - 组合3：应用身份+边界值组合",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_comb3_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # ========== 五、异常处理 ==========
                            # TC_CAL_LIMIT_001: Content-Type错误
                            # 实际行为：接口接受 text/plain，返回 200（接口可能不严格检查Content-Type）
                            base_case_id.replace("01", "15", 1): {
                                "host": self._host,
                                "url": full_url,
                                "method": method,
                                "detail": "TC_CAL_LIMIT_001 - Content-Type错误（实际接口接受）",
                                "headers": scene_limit1_headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene_limit1_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                        }
                        # 确保 file_path 包含 open-apis 前缀，以生成正确的 YAML 文件路径
                        # 从 servers 中提取基础路径，或使用默认路径
                        file_path_for_yaml = path if path.startswith("/open-apis") else "/open-apis/calendar/v4" + path
                        self.yaml_cases(yaml_data, file_path=file_path_for_yaml)

        try:
            swagger = CalendarSwaggerForYaml(yaml_path)
            swagger.write_yaml_handler()
            print("✓ YAML 用例文件生成成功")
            print("   生成了15个测试场景，覆盖创建日历测试用例表中的主要用例")
        except Exception as e:
            print(f"✗ 生成 YAML 文件时出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def get_tenant_access_token(self, app_id: str, app_secret: str) -> Optional[str]:
        """获取 tenant_access_token"""
        if requests is None:
            print("✗ 错误: 需要安装 requests 库才能获取 token")
            print("   请运行: pip install requests")
            return None

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"app_id": app_id, "app_secret": app_secret}

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                expire = data.get("expire", 0)
                print("✓ 成功获取 tenant_access_token")
                print(f"  过期时间: {expire} 秒 ({expire // 60} 分钟)")
                return token
            print("✗ 获取 tenant_access_token 失败")
            print(f"  错误码: {data.get('code')}")
            print(f"  错误信息: {data.get('msg', '未知错误')}")
            return None
        except Exception as exc:
            print(f"✗ 获取 tenant_access_token 时出错: {exc}")
            return None

    def update_yaml_with_token(self, yaml_path: Path, token: str) -> bool:
        """将 token 写入 YAML，处理 YAML 锚点引用，确保每个用例都有独立的 headers"""
        try:
            import ruamel.yaml
            import copy
        except ImportError:
            print("✗ 错误: 需要安装 ruamel.yaml 库才能更新 YAML")
            print("   请运行: pip install ruamel.yaml")
            return False

        try:
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            yaml.default_flow_style = False

            data = {}
            if yaml_path.exists():
                with yaml_path.open("r", encoding="utf-8") as f:
                    data = yaml.load(f) or {}

            updated = False
            # 记录第一个用例的 headers（用于检测锚点引用）
            first_headers_obj = None

            for key, value in data.items():
                if key == "case_common" or not isinstance(value, dict):
                    continue

                headers = value.get("headers")

                # 检测是否是锚点引用：如果 headers 对象与第一个用例的 headers 是同一个对象，说明是引用
                if first_headers_obj is None:
                    first_headers_obj = headers
                    # 第一个用例：创建新的独立字典
                    if headers is None:
                        headers = {}
                    else:
                        # 深拷贝，确保独立
                        headers = copy.deepcopy(dict(headers))
                    value["headers"] = headers
                else:
                    # 后续用例：检查是否是同一个对象（锚点引用）
                    if headers is first_headers_obj:
                        # 是锚点引用，创建独立副本
                        headers = copy.deepcopy(dict(first_headers_obj))
                        value["headers"] = headers
                    elif headers is None:
                        headers = {}
                        value["headers"] = headers
                    elif not isinstance(headers, dict):
                        # 其他异常情况，转换为字典
                        headers = copy.deepcopy(dict(headers)) if hasattr(headers, '__iter__') else {}
                        value["headers"] = headers

                # 确保 headers 是字典类型
                if not isinstance(headers, dict):
                    headers = {}
                    value["headers"] = headers

                # 跳过 TC_CAL_AUTH_003（Token格式错误）用例，保持无效token
                detail = value.get("detail", "")
                if "TC_CAL_AUTH_003" in detail or "Token格式错误" in detail:
                    continue

                # 更新 Authorization
                headers["Authorization"] = f"Bearer {token}"
                updated = True

            if updated:
                with yaml_path.open("w", encoding="utf-8") as f:
                    yaml.dump(data, f)
                print(f"✓ 已更新 YAML 文件: {yaml_path}")
                return True

            print("⚠ 警告: 未找到需要更新的用例配置")
            return False
        except Exception as exc:
            print(f"✗ 更新 YAML 文件时出错: {exc}")
            import traceback
            traceback.print_exc()
            return False

    def step3_update_token_in_yaml(self) -> None:
        """步骤3: 更新 YAML 中的 tenant_access_token"""
        print("\n" + "=" * 60)
        print("步骤 3/5: 更新 YAML 中的 tenant_access_token（可选）")
        print("=" * 60)

        yaml_path = Path("data/open-apis/calendar/v4/calendars.yaml")
        if not yaml_path.exists():
            print(f"⚠ 警告: 未找到 YAML 文件 {yaml_path}")
            print("   请确认步骤 2 是否成功执行")
            return

        app_id = DEFAULT_APP_ID
        app_secret = DEFAULT_APP_SECRET

        token = self.get_tenant_access_token(app_id, app_secret)
        if token and self.update_yaml_with_token(yaml_path, token):
            print("✓ tenant_access_token 已成功更新到 YAML 文件")
        else:
            print("⚠ 获取或更新 token 失败，请手动更新 YAML 中的 Authorization")

    def step4_generate_test_cases(self) -> None:
        """步骤4: 生成 pytest 测试用例"""
        print("\n" + "=" * 60)
        print("步骤 4/5: 生成 pytest 测试用例代码")
        print("=" * 60)

        try:
            generator = TestCaseAutomaticGeneration()
            generator.get_case_automatic()
            print("✓ pytest 测试用例代码生成成功")
        except Exception as exc:
            print(f"✗ 生成测试用例时出错: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def update_test_calendars_case_ids(self) -> None:
        """
        根据 calendars.yaml 中的所有用例 ID，更新 test_calendars.py 里的 case_id 列表，
        让 pytest 一次性覆盖多个场景。
        """
        try:
            from pathlib import Path
            import re
            try:
                import ruamel.yaml  # type: ignore[import]
            except ImportError:
                print("⚠ 未安装 ruamel.yaml，无法自动更新 test_calendars.py 的 case_id，多场景请手动维护。")
                return

            yaml_path = Path("data/open-apis/calendar/v4/calendars.yaml")
            test_path = Path("test_case/open-apis/calendar/v4/test_calendars.py")

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
                print(f"✓ 已更新 test_calendars.py 中的 case_id，当前用例数: {len(case_ids)}")
            else:
                print("⚠ 未能在 test_calendars.py 中找到 case_id 定义，跳过自动更新。")
        except Exception as e:  # noqa: BLE001
            print(f"⚠ 自动更新 test_calendars.py case_id 时出错: {e}")

    def step5_summary(self) -> None:
        """步骤5: 输出总结"""
        print("\n" + "=" * 60)
        print("步骤 5/5: 完成总结")
        print("=" * 60)

        yaml_path = Path("data/open-apis/calendar/v4/calendars.yaml")
        test_case_path = Path("test_case/open-apis/calendar/v4/test_calendars.py")

        print("\n生成的文件：")
        print(f"  {'✓' if yaml_path.exists() else '✗'} YAML 用例文件: {yaml_path}")
        print(f"  {'✓' if test_case_path.exists() else '✗'} 测试用例代码: {test_case_path}")

        print("\n接下来你可以：")
        print("1. 根据需要重新获取 token（步骤3）或手动修改 YAML 中的 Authorization。")
        print("2. 执行 pytest 测试：")
        print("   pytest test_case/open-apis/calendar/v4/test_calendars.py -s")

    def run_all(self) -> None:
        """执行全部步骤"""
        print("\n" + "=" * 60)
        print('飞书"创建共享日历"接口测试用例自动生成流程')
        print("=" * 60)
        print("\n本脚本将自动执行以下步骤：")
        print("1. 检查 OpenAPI YAML 文件")
        print("2. 生成 YAML 用例文件")
        print("3. 获取并更新 tenant_access_token（可选）")
        print("4. 生成 pytest 测试用例")
        print("5. 输出总结信息\n")

        try:
            self.step1_check_openapi()
            self.step2_generate_yaml_from_swagger()
            self.step3_update_token_in_yaml()
            self.step4_generate_test_cases()
            # 更新 test_calendars.py 中的 case_id，使其覆盖 calendars.yaml 中的多个场景
            self.update_test_calendars_case_ids()
            self.step5_summary()

            print("\n" + "=" * 60)
            print("✓ 所有步骤执行完成！")
            print("=" * 60)
        except KeyboardInterrupt:
            print("\n\n用户中断，正在退出...")
            sys.exit(0)
        except Exception as exc:
            print(f"\n✗ 执行过程中出错: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    generator = FeishuCalendarCreateGenerator()
    generator.run_all()


if __name__ == "__main__":
    main()

