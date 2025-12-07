#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书测试用例自动生成流程整合脚本

整合以下流程：
1. 从 Swagger JSON 生成 YAML 用例文件
2. 启动飞书 OAuth 回调服务（后台）
3. 生成授权链接，等待用户完成授权
4. 自动获取 user_access_token 并更新到 YAML
5. 生成 pytest 测试用例代码

使用方法：
    python utils/other_tools/feishu_test_generator.py
"""

import sys
import time
import threading
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.read_files_tools.swagger_for_yaml import SwaggerForYaml
from utils.read_files_tools.case_automatic_control import TestCaseAutomaticGeneration
from utils.other_tools.feishu_get_code import build_feishu_authorize_url, FEISHU_CLIENT_ID, FEISHU_REDIRECT_URI
from utils.other_tools.feishu_token_updater import (
    run_callback_server,
    FEISHU_CLIENT_ID as TOKEN_CLIENT_ID,
    FEISHU_CLIENT_SECRET,
    REDIRECT_URI,
)


class FeishuTestGenerator:
    """飞书测试用例生成器"""

    def __init__(self):
        self.server_thread: Optional[threading.Thread] = None
        self.server_running = False

    def step1_generate_yaml_from_swagger(self) -> None:
        """步骤1: 从 Swagger JSON 生成 YAML 用例文件"""
        print("\n" + "=" * 60)
        print("步骤 1/5: 从 Swagger JSON 生成 YAML 用例文件")
        print("=" * 60)
        
        try:
            swagger = SwaggerForYaml()
            swagger.write_yaml_handler()
            print("✓ YAML 用例文件生成成功")
        except FileNotFoundError as e:
            print(f"✗ 错误: {e}")
            print("请确保 ./interfacetest/userInfo.json 文件存在")
            sys.exit(1)
        except Exception as e:
            print(f"✗ 生成 YAML 文件时出错: {e}")
            sys.exit(1)

    def step2_start_callback_server(self) -> None:
        """步骤2: 启动飞书 OAuth 回调服务（后台线程）"""
        print("\n" + "=" * 60)
        print("步骤 2/5: 启动飞书 OAuth 回调服务")
        print("=" * 60)
        
        # 检查 client_id 和 client_secret 是否已配置
        if TOKEN_CLIENT_ID == "你的 App ID" or FEISHU_CLIENT_SECRET == "你的 App Secret":
            print("✗ 错误: 请先在 feishu_token_updater.py 中配置 FEISHU_CLIENT_ID 和 FEISHU_CLIENT_SECRET")
            sys.exit(1)
        
        # 在后台线程中启动回调服务
        self.server_running = True
        self.server_thread = threading.Thread(
            target=self._run_server_in_thread,
            daemon=True
        )
        self.server_thread.start()
        
        # 等待服务启动
        time.sleep(2)
        print(f"✓ 回调服务已启动，监听地址: {REDIRECT_URI}")
        print("  请确保飞书应用『重定向 URL』中已配置该地址")

    def _run_server_in_thread(self) -> None:
        """在线程中运行回调服务"""
        try:
            run_callback_server()
        except Exception as e:
            print(f"\n✗ 回调服务运行出错: {e}")
            self.server_running = False

    def step3_generate_auth_url(self) -> None:
        """步骤3: 生成授权链接，等待用户完成授权"""
        print("\n" + "=" * 60)
        print("步骤 3/5: 生成授权链接")
        print("=" * 60)
        
        # 检查配置
        if FEISHU_CLIENT_ID == "你的 App ID":
            print("✗ 错误: 请先在 feishu_get_code.py 中配置 FEISHU_CLIENT_ID")
            sys.exit(1)
        
        # 生成授权链接
        auth_url = build_feishu_authorize_url(
            client_id=FEISHU_CLIENT_ID,
            redirect_uri=FEISHU_REDIRECT_URI,
        )
        
        print("\n请在浏览器中打开以下授权链接并完成授权：")
        print("-" * 60)
        print(auth_url)
        print("-" * 60)
        print("\n等待授权完成...")
        print("提示: 授权成功后，回调服务会自动获取 user_access_token 并更新到 YAML 文件")
        print("      完成后，请按 Ctrl+C 继续下一步，或等待 60 秒后自动继续...\n")
        
        # 等待用户完成授权（最多等待 60 秒）
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n检测到用户中断，继续下一步...")

    def step4_wait_for_token_update(self) -> None:
        """步骤4: 等待 token 更新完成"""
        print("\n" + "=" * 60)
        print("步骤 4/5: 检查 user_access_token 是否已更新")
        print("=" * 60)
        
        yaml_path = Path("data/open-apis/authen/v1/user_info.yaml")
        if not yaml_path.exists():
            print(f"⚠ 警告: 未找到 YAML 文件 {yaml_path}")
            print("   请确认步骤 1 是否成功执行")
            return
        
        # 检查 YAML 中是否有有效的 token
        try:
            try:
                import ruamel.yaml
                yaml_parser = ruamel.yaml.YAML()
                # 允许重复键，但只保留最后一个
                yaml_parser.allow_duplicate_keys = True
                yaml_parser.preserve_quotes = True
            except ImportError:
                print("⚠ 警告: 未安装 ruamel.yaml，无法检查 token")
                return
            
            content = yaml_path.read_text(encoding="utf-8")
            data = yaml_parser.load(content) or {}
            
            case_key = "01_open-apis_authen_v1_user_info"
            case_conf = data.get(case_key, {})
            headers = case_conf.get("headers", {})
            auth_header = headers.get("Authorization", "")
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                if len(token) > 20:  # 简单检查 token 是否有效
                    print(f"✓ user_access_token 已更新到 YAML 文件")
                    print(f"  Token 前缀: {token[:20]}...")
                else:
                    print("⚠ 警告: YAML 中的 token 看起来无效，请检查")
            else:
                print("⚠ 警告: YAML 中未找到有效的 Authorization header")
                print("   如果授权已完成，请检查回调服务是否正常运行")
        except Exception as e:
            error_msg = str(e)
            if "duplicate key" in error_msg.lower() or "DuplicateKeyError" in error_msg:
                print("⚠ 警告: YAML 文件中存在重复的键")
                print("   这通常是因为多次运行 swagger_for_yaml.py 导致的")
                print("   建议：删除该 YAML 文件后重新运行步骤 1")
                print(f"   文件路径: {yaml_path}")
            else:
                print(f"⚠ 警告: 检查 YAML 文件时出错: {e}")
                print("   如果 YAML 文件格式有问题，建议删除后重新运行步骤 1")

    def step5_generate_test_cases(self) -> None:
        """步骤5: 生成 pytest 测试用例代码"""
        print("\n" + "=" * 60)
        print("步骤 5/5: 生成 pytest 测试用例代码")
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

    def run_all(self) -> None:
        """执行完整流程"""
        print("\n" + "=" * 60)
        print("飞书测试用例自动生成流程")
        print("=" * 60)
        print("\n本脚本将自动执行以下步骤：")
        print("1. 从 Swagger JSON 生成 YAML 用例文件")
        print("2. 启动飞书 OAuth 回调服务（后台）")
        print("3. 生成授权链接，等待用户完成授权")
        print("4. 检查 user_access_token 是否已更新")
        print("5. 生成 pytest 测试用例代码")
        print("\n开始执行...\n")
        
        try:
            # 步骤1: 生成 YAML
            self.step1_generate_yaml_from_swagger()
            
            # 步骤2: 启动回调服务
            self.step2_start_callback_server()
            
            # 步骤3: 生成授权链接
            self.step3_generate_auth_url()
            
            # 步骤4: 检查 token
            self.step4_wait_for_token_update()
            
            # 步骤5: 生成测试用例
            self.step5_generate_test_cases()
            
            print("\n" + "=" * 60)
            print("✓ 所有步骤执行完成！")
            print("=" * 60)
            print("\n接下来你可以：")
            print("1. 运行 pytest 测试用例:")
            print("   pytest test_case/open-apis/authen/v1/test_user_info.py -s")
            print("\n2. 如果回调服务仍在运行，可以按 Ctrl+C 停止")
            
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
    generator = FeishuTestGenerator()
    generator.run_all()


if __name__ == "__main__":
    main()

