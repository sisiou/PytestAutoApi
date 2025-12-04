#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书“查询日历信息”接口测试用例自动生成脚本

步骤：
1. 校验 CalendarGet.json 是否存在
2. 基于 JSON 生成 YAML
3. 自动刷新 tenant_access_token（可选）
4. 生成 pytest 用例
5. 输出总结

使用方法：
    python utils/other_tools/feishu_calendar_get_generator.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
except ImportError:
    requests = None

from utils.read_files_tools.swagger_for_yaml import SwaggerForYaml
from utils.read_files_tools.case_automatic_control import TestCaseAutomaticGeneration

# ================= 手动配置 =================
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"
DEFAULT_APP_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"
# 当无法从“查询日历列表”接口获取 calendar_id 时，退回到该默认值
DEFAULT_CALENDAR_ID = "feishu.cn_xxxxxxxxxx@group.calendar.feishu.cn"
CALENDAR_ID_CACHE_PATH = project_root / "runtime" / "cache" / "last_calendar_id.txt"
# =================================================


def sanitize_calendar_id(calendar_id: str) -> str:
    """将 calendar_id 中不适合用作文件名 / 类名的字符转换掉"""
    import re
    return re.sub(r'[^0-9a-zA-Z]+', '_', calendar_id).strip('_') or "calendar"

 
class FeishuCalendarGetGenerator:
    def __init__(self):
        self.json_path = Path("interfacetest/CalendarGet.json")

    def step1_check_json(self) -> None:
        print("\n" + "=" * 60)
        print("步骤 1/5: 检查 CalendarGet.json")
        print("=" * 60)
        if self.json_path.exists():
            print(f"✓ CalendarGet.json 已存在: {self.json_path}")
            return
        print(f"✗ 错误: 未找到 {self.json_path}")
        sys.exit(1)

    def step2_generate_yaml(self) -> None:
        print("\n" + "=" * 60)
        print("步骤 2/5: 生成 YAML 用例")
        print("=" * 60)

        # 优先读取创建流程缓存的 calendar_id，其次调用“查询日历列表”接口
        cached_calendar_id = self.load_cached_calendar_id()
        auto_calendar_id = cached_calendar_id or self.fetch_calendar_id_from_list()
        selected_calendar_id = auto_calendar_id or DEFAULT_CALENDAR_ID
        sanitized_calendar_id = sanitize_calendar_id(selected_calendar_id)

        if cached_calendar_id:
            print(f"✓ 使用缓存中的 calendar_id: {selected_calendar_id}")
        elif auto_calendar_id:
            print(f"✓ 已从查询日历列表接口获取 calendar_id: {selected_calendar_id}")
        else:
            print(f"⚠ 未能自动获取 calendar_id，使用默认值: {selected_calendar_id}")

        json_file = str(self.json_path)

        class CalendarGetSwagger(SwaggerForYaml):
            @classmethod
            def get_swagger_json(cls):
                import json
                with open(json_file, "r", encoding="utf-8") as f:
                    return json.load(f)

            def get_case_data(self, value):
                return None

            def write_yaml_handler(self):
                _api_data = self._data['paths']
                for path, methods in _api_data.items():
                    for method, meta in methods.items():
                        headers = self.get_headers(meta)
                        request_type = self.get_request_type(meta, headers)

                        final_path = path
                        if "{calendar_id}" in final_path:
                            final_path = final_path.replace("{calendar_id}", selected_calendar_id)

                        case_id_key = self.get_case_id(path.replace("{calendar_id}", sanitized_calendar_id))
                        yaml_data = {
                            "case_common": {
                                "allureEpic": self.get_allure_epic(),
                                "allureFeature": self.get_allure_feature(meta),
                                "allureStory": self.get_allure_story(meta)
                            },
                            case_id_key: {
                                "host": self._host,
                                "url": final_path,
                                "method": method,
                                "detail": self.get_detail(meta),
                                "headers": headers,
                                "requestType": request_type,
                                "is_run": None,
                                "data": None,
                                "dependence_case": False,
                                "assert": {"status_code": 200},
                                "sql": None
                            }
                        }
                        sanitized_path = path.replace("{calendar_id}", sanitized_calendar_id)
                        self.yaml_cases(yaml_data, file_path=sanitized_path)

        try:
            swagger = CalendarGetSwagger()
            swagger.write_yaml_handler()
            print("✓ YAML 用例生成成功")
        except Exception as exc:
            print(f"✗ 生成 YAML 失败: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def get_tenant_access_token(self, app_id: str, app_secret: str) -> Optional[str]:
        if requests is None:
            print("✗ 需要安装 requests 才能获取 token")
            return None

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}
        headers = {"Content-Type": "application/json; charset=utf-8"}
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
            print(f"✗ 获取 token 失败: {data.get('msg')}")
            return None
        except Exception as exc:
            print(f"✗ 获取 token 出错: {exc}")
            return None

    def load_cached_calendar_id(self) -> Optional[str]:
        """从缓存文件读取创建共享日历时保存的 calendar_id"""
        try:
            if CALENDAR_ID_CACHE_PATH.exists():
                value = CALENDAR_ID_CACHE_PATH.read_text(encoding="utf-8").strip()
                if value:
                    return value
        except Exception as exc:
            print(f"⚠ 读取缓存 calendar_id 失败: {exc}")
        return None

    def fetch_calendar_id_from_list(self) -> Optional[str]:
        """
        调用『查询日历列表』接口，自动获取一个可用的 calendar_id
        优先选择当前身份可访问、且未删除的日历，若无则返回 None
        """
        if requests is None:
            print("⚠ 未安装 requests，无法自动获取 calendar_id")
            return None

        token = self.get_tenant_access_token(DEFAULT_APP_ID, DEFAULT_APP_SECRET)
        if not token:
            return None

        url = "https://open.feishu.cn/open-apis/calendar/v4/calendars"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        params = {"page_size": 50}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                print(f"⚠ 查询日历列表失败，code={data.get('code')}, msg={data.get('msg')}")
                return None

            calendar_list = (data.get("data") or {}).get("calendar_list") or []
            for cal in calendar_list:
                # 只取未删除的日历
                if not cal.get("is_deleted", False):
                    return cal.get("calendar_id")

            print("⚠ 日历列表为空或全部已删除，无法自动选择 calendar_id")
            return None
        except Exception as exc:
            print(f"⚠ 调用查询日历列表接口出错: {exc}")
            return None

    def update_yaml_with_token(self, yaml_path: Path, token: str) -> bool:
        try:
            import ruamel.yaml
        except ImportError:
            print("✗ 需要安装 ruamel.yaml 才能写入 YAML")
            return False

        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True

        if yaml_path.exists():
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.load(f) or {}
        else:
            data = {}

        updated = False
        for key, value in data.items():
            if key == "case_common" or not isinstance(value, dict):
                continue
            headers = value.get("headers") or {}
            headers["Authorization"] = f"Bearer {token}"
            value["headers"] = headers
            updated = True

        if updated:
            with yaml_path.open("w", encoding="utf-8") as f:
                yaml.dump(data, f)
            print(f"✓ 已更新 YAML 文件: {yaml_path}")
        else:
            print("⚠ 未找到需要更新的用例")
        return updated

    def step3_update_token(self) -> None:
        print("\n" + "=" * 60)
        print("步骤 3/5: 更新 YAML 中的 tenant_access_token（可选）")
        print("=" * 60)

        yaml_path = Path("data/open-apis/calendar/v4/calendars_{get}.yaml")
        if not yaml_path.exists():
            yaml_path = Path("data/open-apis/calendar/v4/calendars.yaml")

        if not yaml_path.exists():
            print(f"⚠ 未找到 YAML 文件: {yaml_path}")
            return

        token = self.get_tenant_access_token(DEFAULT_APP_ID, DEFAULT_APP_SECRET)
        if token:
            if self.update_yaml_with_token(yaml_path, token):
                print("✓ tenant_access_token 已写入 YAML")
            else:
                print("⚠ token 写入失败，请手动更新 YAML")
        else:
            print("⚠ 获取 token 失败，请手动更新 YAML")

    def step4_generate_tests(self) -> None:
        print("\n" + "=" * 60)
        print("步骤 4/5: 生成 pytest 测试用例")
        print("=" * 60)
        try:
            generator = TestCaseAutomaticGeneration()
            generator.get_case_automatic()
            print("✓ pytest 测试用例生成成功")
        except Exception as exc:
            print(f"✗ 生成测试用例失败: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def step5_summary(self) -> None:
        print("\n" + "=" * 60)
        print("步骤 5/5: 总结")
        print("=" * 60)

        yaml_path = Path("data/open-apis/calendar/v4/calendars.yaml")
        test_case_path = Path("test_case/open-apis/calendar/v4/test_calendars.py")

        print(f"  {'✓' if yaml_path.exists() else '✗'} YAML: {yaml_path}")
        print(f"  {'✓' if test_case_path.exists() else '✗'} Pytest: {test_case_path}")
        print("\n接下来你可以：")
        print("1. 根据需要重新获取 token（步骤3）或手动修改 YAML Authorization。")
        print("2. 执行 pytest：pytest test_case/open-apis/calendar/v4/test_calendars.py -s")

    def run_all(self) -> None:
        print("\n" + "=" * 60)
        print('飞书"查询日历信息"接口测试用例自动生成流程')
        print("=" * 60)
        print("\n自动执行以下步骤：")
        print("1. 检查 CalendarGet.json")
        print("2. 生成 YAML 用例")
        print("3. 获取并更新 tenant_access_token（可选）")
        print("4. 生成 pytest 测试用例")
        print("5. 输出总结\n")

        try:
            self.step1_check_json()
            self.step2_generate_yaml()
            self.step3_update_token()
            self.step4_generate_tests()
            self.step5_summary()

            print("\n" + "=" * 60)
            print("✓ 所有步骤执行完成！")
            print("=" * 60)
        except KeyboardInterrupt:
            print("\n用户中断，退出中...")
            sys.exit(0)
        except Exception as exc:
            print(f"\n✗ 执行过程中出错: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    FeishuCalendarGetGenerator().run_all()


if __name__ == "__main__":
    main()

