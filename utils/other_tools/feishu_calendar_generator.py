#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书“创建共享日历”接口测试用例自动生成脚本

执行步骤：
1. 校验 CalendarCreate.json 是否存在
2. 依据 CalendarCreate.json 生成 YAML 用例
3. 自动获取 tenant_access_token 并写入 YAML（可选）
4. 生成 pytest 用例
5. 输出总结信息

使用方法：
    python utils/other_tools/feishu_calendar_generator.py
"""

import sys
import time
import os
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
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"
DEFAULT_APP_SECRET =  "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"
# =================================================


class FeishuCalendarCreateGenerator:
    """飞书共享日历创建接口测试用例生成器"""

    def __init__(self):
        self.calendar_json_path = Path("interfacetest/CalendarCreate.json")
        self.swagger_json_path = self.calendar_json_path

    def step1_check_json(self) -> None:
        """步骤1: 校验 CalendarCreate.json 是否存在"""
        print("\n" + "=" * 60)
        print("步骤 1/5: 检查 CalendarCreate.json")
        print("=" * 60)

        if self.calendar_json_path.exists():
            print(f"✓ CalendarCreate.json 已存在: {self.calendar_json_path}")
            return

        print(f"✗ 错误: 未找到 {self.calendar_json_path}")
        print("  请根据接口文档创建该 JSON 文件")
        sys.exit(1)

    def step2_generate_yaml_from_swagger(self) -> None:
        """步骤2: 从 CalendarCreate.json 生成 YAML 用例"""
        print("\n" + "=" * 60)
        print("步骤 2/5: 从 CalendarCreate.json 生成 YAML 用例")
        print("=" * 60)

        json_path = str(self.calendar_json_path)

        class CalendarSwaggerForYaml(SwaggerForYaml):
            @classmethod
            def get_swagger_json(cls):
                try:
                    import json
                    with open(json_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except FileNotFoundError:
                    raise FileNotFoundError(f"文件路径不存在: {json_path}")

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

                    example = json_content.get('example')
                    if example:
                        body_data.update(example)
                    else:
                        for prop in schema.get('properties', {}).keys():
                            body_data.setdefault(prop, None)

                return body_data or None

            def write_yaml_handler(self):
                """
                重写写入逻辑:
                - 基于同一个接口，生成多种场景的用例，覆盖正常和典型错误场景
                  场景1: 创建私有日历（permissions=private，成功）
                  场景2: 创建公开日历（permissions=public，成功）
                  场景3: 缺少 summary（必填字段缺失，预期 400）
                  场景4: summary 超长（>255，预期 400）
                  场景5: permissions 非法取值（预期 400）
                  场景6: description 超长（>255，预期 400）
                  场景7: color 超出 int32 范围（预期 400）
                """
                import copy

                _api_data = self._data["paths"]
                for path, methods in _api_data.items():
                    for method, meta in methods.items():
                        headers = self.get_headers(meta)
                        request_type = self.get_request_type(meta, headers)
                        body_data = self.get_case_data(meta)

                        base_body = copy.deepcopy(body_data) if isinstance(body_data, dict) else {}

                        # 场景1：私有日历，期望成功
                        scene1_body = copy.deepcopy(base_body)
                        scene1_body.setdefault("summary", "自动化测试日历 - 私有")
                        scene1_body["permissions"] = "private"

                        # 场景2：公开日历，期望成功
                        scene2_body = copy.deepcopy(base_body)
                        scene2_body.setdefault("summary", "自动化测试日历 - 公开")
                        scene2_body["permissions"] = "public"

                        # 场景3：缺少 summary，期望 400 参数错误
                        scene3_body = copy.deepcopy(base_body)
                        if "summary" in scene3_body:
                            scene3_body.pop("summary")

                        # 场景4：summary 超长，期望 400 参数错误
                        scene4_body = copy.deepcopy(base_body)
                        scene4_body["summary"] = "A" * 300  # 超过 255 的边界

                        # 场景5：permissions 非法取值，期望 400 参数错误
                        scene5_body = copy.deepcopy(base_body)
                        scene5_body["permissions"] = "invalid_permission_for_test"

                        # 场景6：description 超长，期望 400 参数错误
                        scene6_body = copy.deepcopy(base_body)
                        scene6_body.setdefault("summary", "自动化测试日历 - 描述超长")
                        scene6_body["description"] = "D" * 300  # 超过 255 的边界

                        # 场景7：color 超出 int32 范围，期望 400 参数错误
                        scene7_body = copy.deepcopy(base_body)
                        scene7_body.setdefault("summary", "自动化测试日历 - 颜色越界")
                        scene7_body["color"] = 2 ** 31  # 超出 32 位有符号整型上限

                        base_case_id = self.get_case_id(path)
                        yaml_data = {
                            "case_common": {
                                "allureEpic": self.get_allure_epic(),
                                "allureFeature": self.get_allure_feature(meta),
                                "allureStory": self.get_allure_story(meta),
                            },
                            # 场景1：私有日历成功
                            base_case_id: {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 私有日历成功",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene1_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # 场景2：公开日历成功
                            base_case_id.replace("01", "02", 1): {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 公开日历成功",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene2_body,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # 场景3：缺少 summary（实测为允许，视为标题为空的成功场景）
                            base_case_id.replace("01", "03", 1): {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 缺少标题字段默认成功",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene3_body,
                                "dependence_case": False,
                                # 实测: 不传 summary 时接口仍成功，只是 summary 为空字符串
                                "assert": {"status_code": 200},
                                "sql": None,
                            },
                            # 场景4：summary 超长
                            base_case_id.replace("01", "04", 1): {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 标题超长",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene4_body,
                                "dependence_case": False,
                                # 标题超长 -> 实际返回 99992402（field validation failed）
                                "assert": {"status_code": 400, "feishu_code": 99992402},
                                "sql": None,
                            },
                            # 场景5：permissions 非法取值
                            base_case_id.replace("01", "05", 1): {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 非法权限类型",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene5_body,
                                "dependence_case": False,
                                # 非法权限类型 -> 实际返回 99992402（field validation failed）
                                "assert": {"status_code": 400, "feishu_code": 99992402},
                                "sql": None,
                            },
                            # 场景6：description 超长
                            base_case_id.replace("01", "06", 1): {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 描述超长",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene6_body,
                                "dependence_case": False,
                                # 描述超长 -> 实际返回 99992402（field validation failed）
                                "assert": {"status_code": 400, "feishu_code": 99992402},
                                "sql": None,
                            },
                            # 场景7：color 越界
                            base_case_id.replace("01", "07", 1): {
                                "host": self._host,
                                "url": path,
                                "method": method,
                                "detail": self.get_detail(meta) + " - 颜色越界",
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": scene7_body,
                                "dependence_case": False,
                                # 颜色越界 -> 实际返回 9499（Invalid parameter type in json: color）
                                "assert": {"status_code": 400, "feishu_code": 9499},
                                "sql": None,
                            },
                        }
                        self.yaml_cases(yaml_data, file_path=path)

        try:
            swagger = CalendarSwaggerForYaml()
            swagger.write_yaml_handler()
            print("✓ YAML 用例文件生成成功")
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
        """将 token 写入 YAML"""
        try:
            import ruamel.yaml
        except ImportError:
            print("✗ 错误: 需要安装 ruamel.yaml 库才能更新 YAML")
            print("   请运行: pip install ruamel.yaml")
            return False

        try:
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True

            data = {}
            if yaml_path.exists():
                with yaml_path.open("r", encoding="utf-8") as f:
                    data = yaml.load(f) or {}

            updated = False
            for key, value in data.items():
                if key == "case_common" or not isinstance(value, dict):
                    continue
                headers = value.get("headers") or {}
                if isinstance(headers, dict):
                    headers["Authorization"] = f"Bearer {token}"
                    value["headers"] = headers
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
        print("1. 检查 CalendarCreate.json")
        print("2. 生成 YAML 用例文件")
        print("3. 获取并更新 tenant_access_token（可选）")
        print("4. 生成 pytest 测试用例")
        print("5. 输出总结信息\n")

        try:
            self.step1_check_json()
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

