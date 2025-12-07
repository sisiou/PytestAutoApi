#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书“上传图片”接口测试用例生成脚本

功能：
1. 准备测试图片（将 img/sendImage.png 拷贝到 Files/ 目录，并生成 0B 空文件用于异常场景）
2. 生成 YAML 用例（正向 + 负向）
3. 自动获取 tenant_access_token 并写入 YAML
4. 生成 pytest 测试用例
5. 更新 test_images.py 的 case_id

使用方法：
    python utils/other_tools/feishu_image_upload_generator.py
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
except ImportError:
    requests = None

from utils.read_files_tools.case_automatic_control import TestCaseAutomaticGeneration
from utils.other_tools.allure_config_helper import ensure_allure_properties_file

# ================= 手动配置区域 =================
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"
DEFAULT_APP_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"
SOURCE_IMAGE_PATH = Path("img/sendImage.png")
TARGET_FILES_DIR = Path("Files")
TARGET_IMAGE_NAME = "sendImage.png"
EMPTY_IMAGE_NAME = "empty.png"  # 0B 文件，用于 size=0 的异常场景
# =================================================


class FeishuImageUploadGenerator:
    """飞书上传图片接口测试用例生成器"""

    def __init__(self):
        self.yaml_path = Path("data/open-apis/im/v1/images.yaml")
        self.test_path = Path("test_case/open-apis/im/v1/test_images.py")
        self.host = "https://open.feishu.cn"
        self.url = "/open-apis/im/v1/images"

    # ----------------- 工具方法 -----------------
    def copy_image(self) -> None:
        """将测试图片拷贝到 Files 目录，并生成 0B 空文件"""
        TARGET_FILES_DIR.mkdir(parents=True, exist_ok=True)

        # 拷贝正常图片
        target_img = TARGET_FILES_DIR / TARGET_IMAGE_NAME
        if SOURCE_IMAGE_PATH.exists():
            shutil.copy2(SOURCE_IMAGE_PATH, target_img)
            print(f"✓ 已拷贝图片到 {target_img}")
        else:
            print(f"⚠ 警告: 源图片不存在 {SOURCE_IMAGE_PATH}，请放置测试图片或自行替换文件名")

        # 生成 0B 空文件
        empty_img = TARGET_FILES_DIR / EMPTY_IMAGE_NAME
        empty_img.write_bytes(b"")
        print(f"✓ 已生成 0B 测试文件: {empty_img}")

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
        except Exception as exc:  # noqa: BLE001
            print(f"✗ 获取 tenant_access_token 时出错: {exc}")
            return None

    def write_yaml(self) -> None:
        """生成 images.yaml，包含正向与典型负向场景"""
        try:
            import ruamel.yaml  # type: ignore
        except ImportError:
            print("✗ 错误: 需要安装 ruamel.yaml 才能生成 YAML")
            print("   请运行: pip install ruamel.yaml")
            sys.exit(1)

        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True

        base_case_id = "01_open-apis_im_v1_images"
        # 为每个用例准备独立 headers，避免生成 YAML 时出现锚点引用导致后续用例缺少 Authorization
        headers = {"Authorization": "Bearer <tenant_access_token>"}
        headers1 = dict(headers)
        headers2 = dict(headers)
        headers3 = dict(headers)

        def make_data(image_name: str, image_type: str) -> Dict[str, Any]:
            return {
                "file": {"image": image_name},
                "data": {"image_type": image_type},
            }

        yaml_data = {
            "case_common": {
                "allureEpic": "飞书IM",
                "allureFeature": "上传图片",
                "allureStory": "获取 image_key 后续发送图片",
            },
            # 场景1：成功上传 message 用途图片
            base_case_id: {
                "host": self.host,
                "url": self.url,
                "method": "post",
                "detail": "上传图片 - 成功",
                "headers": headers1,
                "requestType": "FILE",
                "is_run": None,
                "data": make_data(TARGET_IMAGE_NAME, "message"),
                "dependence_case": False,
                # 将 image_key 写入 Redis（依赖 cache_control 中的 redis: 前缀）
                "current_request_set_cache": [
                    {
                        "type": "response",
                        "jsonpath": "$.data.image_key",
                        "name": "redis:image_key",
                    }
                ],
                "assert": {"status_code": 200},
                "sql": None,
            },
            # 场景2：image_type 非法
            base_case_id.replace("01", "02", 1): {
                "host": self.host,
                "url": self.url,
                "method": "post",
                "detail": "上传图片 - 非法 image_type",
                "headers": headers2,
                "requestType": "FILE",
                "is_run": None,
                "data": make_data(TARGET_IMAGE_NAME, "invalid_type"),
                "dependence_case": False,
                # 文档：234001 Invalid request param
                "assert": {"status_code": 400, "feishu_code": 234001},
                "sql": None,
            },
            # 场景3：0B 文件，预期 234010
            base_case_id.replace("01", "03", 1): {
                "host": self.host,
                "url": self.url,
                "method": "post",
                "detail": "上传图片 - 文件大小为0",
                "headers": headers3,
                "requestType": "FILE",
                "is_run": None,
                "data": make_data(EMPTY_IMAGE_NAME, "message"),
                "dependence_case": False,
                # 文档：234010 File's size can't be 0.
                "assert": {"status_code": 400, "feishu_code": 234010},
                "sql": None,
            },
        }

        self.yaml_path.parent.mkdir(parents=True, exist_ok=True)
        with self.yaml_path.open("w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f)
        print(f"✓ YAML 用例已生成: {self.yaml_path}")

    def update_yaml_with_token(self, token: str) -> bool:
        """将 token 写入 YAML，处理 YAML 锚点引用问题"""
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

            if not self.yaml_path.exists():
                print(f"⚠ 警告: YAML 文件不存在: {self.yaml_path}")
                return False

            with self.yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.load(f) or {}
            
            updated = False
            first_headers_obj = None  # 用于检测锚点引用
            
            for key, value in data.items():
                if key == "case_common" or not isinstance(value, Dict):
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
                
                # 跳过无效 token 的用例（用于测试认证失败场景）
                detail = value.get("detail", "")
                if "Token无效" in detail or "Token过期" in detail or "TC_AUTH_001" in detail:
                    continue
                
                # 更新 Authorization
                headers["Authorization"] = f"Bearer {token}"
                updated = True

            if updated:
                with self.yaml_path.open("w", encoding="utf-8") as f:
                    yaml.dump(data, f)
                print(f"✓ 已更新 YAML 中的 Authorization: {self.yaml_path}")
            else:
                print("⚠ 警告: 未找到需要更新的用例配置")
            return updated
        except Exception as exc:  # noqa: BLE001
            print(f"✗ 更新 YAML 文件时出错: {exc}")
            import traceback
            traceback.print_exc()
            return False

    def generate_tests(self) -> None:
        """生成 pytest 用例"""
        try:
            generator = TestCaseAutomaticGeneration()
            generator.get_case_automatic()
            print("✓ pytest 测试用例生成成功")
        except Exception as exc:  # noqa: BLE001
            print(f"✗ 生成测试用例时出错: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def update_test_images_case_ids(self) -> None:
        """根据 images.yaml 更新 test_images.py 的 case_id"""
        try:
            import re
            import ruamel.yaml  # type: ignore
        except ImportError:
            print("⚠ 未安装 ruamel.yaml，跳过 test_images.py case_id 更新")
            return

        if not self.yaml_path.exists() or not self.test_path.exists():
            return

        yaml = ruamel.yaml.YAML()
        data = yaml.load(self.yaml_path.read_text(encoding="utf-8")) or {}
        case_ids = [k for k in data.keys() if k != "case_common"]
        if not case_ids:
            return

        content = self.test_path.read_text(encoding="utf-8")
        pattern = r"case_id\s*=\s*\[.*?\]"
        replacement = f"case_id = {case_ids!r}"
        new_content, count = re.subn(pattern, replacement, content, count=1)
        if count == 1:
            self.test_path.write_text(new_content, encoding="utf-8")
            print(f"✓ 已更新 test_images.py 中的 case_id，当前用例数: {len(case_ids)}")
        else:
            print("⚠ 未能在 test_images.py 中找到 case_id 定义，跳过自动更新")

    # ----------------- 主流程 -----------------
    def run_all(self) -> None:
        print("\n" + "=" * 60)
        print('飞书"上传图片"接口测试用例自动生成流程')
        print("=" * 60)

        try:
            # 准备图片
            self.copy_image()

            # 生成 YAML
            self.write_yaml()

            # 自动获取 token 并写入 YAML
            token = self.get_tenant_access_token(DEFAULT_APP_ID, DEFAULT_APP_SECRET)
            if token:
                self.update_yaml_with_token(token)
            else:
                print("⚠ 未能自动获取 token，请手动更新 YAML 中的 Authorization")

            # 生成 pytest 测试用例
            self.generate_tests()

            # 更新 test_images.py 的 case_id
            self.update_test_images_case_ids()

            # 确保 Allure 配置存在（支持中文）
            ensure_allure_properties_file("./report/tmp")

            # 总结
            print("\n" + "=" * 60)
            print("✓ 所有步骤执行完成！")
            print(f"YAML: {self.yaml_path}")
            print(f"Tests: {self.test_path}")
            print("=" * 60)
        except KeyboardInterrupt:
            print("\n用户中断，正在退出...")
            sys.exit(130)
        except Exception as exc:  # noqa: BLE001
            print(f"\n✗ 执行过程中出错: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    generator = FeishuImageUploadGenerator()
    generator.run_all()


if __name__ == "__main__":
    main()


