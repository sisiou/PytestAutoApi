#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书接口测试用例自动生成和执行脚本

功能：
1. 同时运行 feishu_calendar_generator.py 和 feishu_message_send_generator.py
2. 自动执行生成的测试用例
3. 生成 Allure 报告
4. 发送测试结果通知（钉钉、微信、邮件、飞书）
5. 生成 Excel 报告（可选）

使用方法：
    python utils/other_tools/run_all_feishu_tests.py
"""

import os
import sys
import time
import traceback
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pytest
except ImportError:
    print("✗ 错误: 需要安装 pytest 库")
    print("   请运行: pip install pytest")
    sys.exit(1)

# 导入 run.py 中使用的模块
from utils.other_tools.models import NotificationType
from utils.other_tools.allure_data.allure_report_data import AllureFileClean
from utils.logging_tool.log_control import INFO
from utils.notify.wechat_send import WeChatSend
from utils.notify.ding_talk import DingTalkSendMsg
from utils.notify.send_mail import SendEmail
from utils.notify.lark import FeiShuTalkChatBot
from utils.other_tools.allure_data.error_case_excel import ErrorCaseExcel
from utils.other_tools.allure_config_helper import ensure_allure_properties_file
from utils import config


class FeishuTestRunner:
    """飞书接口测试用例生成和执行器"""

    def __init__(self):
        self.calendar_generator_path = Path("utils/other_tools/feishu_calendar_generator.py")
        self.message_generator_path = Path("utils/other_tools/feishu_message_send_generator_v2.py")
        
        # 生成的测试用例路径
        self.calendar_test_path = Path("test_case/open-apis/calendar/v4/test_calendars.py")
        self.message_test_path = Path("test_case/open-apis/im/v1/test_messages.py")

    def step1_run_generators(self) -> None:
        """步骤1: 运行两个生成器"""
        print("\n" + "=" * 60)
        print("步骤 1/6: 运行测试用例生成器")
        print("=" * 60)

        generators = [
            ("日历创建接口", self.calendar_generator_path),
            ("消息发送接口", self.message_generator_path),
        ]

        for name, generator_path in generators:
            if not generator_path.exists():
                print(f"✗ 错误: 未找到生成器文件 {generator_path}")
                sys.exit(1)

            print(f"\n正在运行 {name} 生成器...")
            print("-" * 60)

            try:
                # 动态导入并运行生成器
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    generator_path.stem, generator_path
                )
                if spec is None or spec.loader is None:
                    raise ImportError(f"无法加载模块: {generator_path}")

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 运行生成器的 main 函数
                if hasattr(module, "main"):
                    module.main()
                    print(f"✓ {name} 生成器执行完成")
                else:
                    print(f"⚠ 警告: {generator_path} 没有 main() 函数")
            except Exception as e:
                print(f"✗ {name} 生成器执行失败: {e}")
                import traceback
                traceback.print_exc()
                print(f"\n⚠ 警告: {name} 生成器失败，将继续执行其他生成器和测试")
                continue

            # 短暂延迟，避免资源竞争
            time.sleep(1)

        print("\n" + "=" * 60)
        print("✓ 所有生成器执行完成")
        print("=" * 60)

    def step2_collect_test_cases(self) -> list:
        """步骤2: 收集生成的测试用例"""
        print("\n" + "=" * 60)
        print("步骤 2/6: 收集测试用例")
        print("=" * 60)

        test_paths = []
        test_files = [
            ("日历创建测试", self.calendar_test_path),
            ("消息发送测试", self.message_test_path),
        ]

        for name, test_path in test_files:
            if test_path.exists():
                test_paths.append(str(test_path))
                print(f"✓ 找到 {name}: {test_path}")
            else:
                print(f"⚠ 警告: 未找到 {name}: {test_path}")

        if not test_paths:
            print("\n✗ 错误: 未找到任何测试用例文件")
            print("   请确认生成器是否成功执行")
            sys.exit(1)

        print(f"\n✓ 共收集到 {len(test_paths)} 个测试文件")
        return test_paths

    def step3_run_tests(self, test_paths: list) -> int:
        """步骤3: 执行测试用例（带 Allure 报告）"""
        print("\n" + "=" * 60)
        print("步骤 3/6: 执行测试用例")
        print("=" * 60)

        if not test_paths:
            print("✗ 错误: 没有可执行的测试用例")
            return 1

        # 确保 Allure 配置文件存在（支持中文显示）
        try:
            ensure_allure_properties_file("./report/tmp")
            print("✓ Allure 配置文件已就绪（支持中文显示）")
        except Exception as e:
            print(f"⚠ 警告: 创建 Allure 配置文件时出错: {e}")

        print(f"\n即将执行以下测试文件：")
        for path in test_paths:
            print(f"  - {path}")

        print("\n开始执行测试...")
        print("-" * 60)

        # 构建 pytest 参数（与 run.py 保持一致）
        pytest_args = [
            "-s",  # 显示 print 输出
            "-W", "ignore:Module already imported:pytest.PytestWarning",  # 忽略警告
            "--alluredir", "./report/tmp",  # Allure 报告目录
            "--clean-alluredir",  # 清理旧的报告
        ]

        # 添加所有测试文件路径
        pytest_args.extend(test_paths)

        try:
            # 执行 pytest
            exit_code = pytest.main(pytest_args)
            return exit_code
        except Exception as e:
            print(f"\n✗ 执行测试时出错: {e}")
            traceback.print_exc()
            return 1

    def step4_generate_allure_report(self) -> None:
        """步骤4: 生成 Allure HTML 报告"""
        print("\n" + "=" * 60)
        print("步骤 4/6: 生成 Allure HTML 报告")
        print("=" * 60)

        try:
            os.system(r"allure generate ./report/tmp -o ./report/html --clean")
            print("✓ Allure HTML 报告生成成功")
        except Exception as e:
            print(f"⚠ 警告: 生成 Allure 报告时出错: {e}")
            print("   请确认已安装 allure 命令行工具")

    def step5_send_notifications_and_reports(self) -> None:
        """步骤5: 发送通知和生成 Excel 报告"""
        print("\n" + "=" * 60)
        print("步骤 5/6: 发送通知和生成报告")
        print("=" * 60)

        try:
            # 获取测试统计数据
            allure_data = AllureFileClean().get_case_count()
            print(f"✓ 测试统计: 总计 {allure_data.total}, 通过 {allure_data.passed}, "
                  f"失败 {allure_data.failed}, 跳过 {allure_data.skipped}")

            # 发送通知（根据配置）
            notification_mapping = {
                NotificationType.DING_TALK.value: DingTalkSendMsg(allure_data).send_ding_notification,
                NotificationType.WECHAT.value: WeChatSend(allure_data).send_wechat_notification,
                NotificationType.EMAIL.value: SendEmail(allure_data).send_main,
                NotificationType.FEI_SHU.value: FeiShuTalkChatBot(allure_data).post
            }

            if config.notification_type != NotificationType.DEFAULT.value:
                notification_func = notification_mapping.get(config.notification_type)
                if notification_func:
                    try:
                        notification_func()
                        print(f"✓ 已发送 {config.notification_type} 通知")
                    except Exception as e:
                        print(f"⚠ 警告: 发送通知失败: {e}")
                else:
                    print(f"⚠ 警告: 未找到通知类型 {config.notification_type} 的处理函数")
            else:
                print("ℹ 未配置通知类型，跳过通知发送")

            # 生成 Excel 报告（如果配置了）
            if config.excel_report:
                try:
                    ErrorCaseExcel().write_case()
                    print("✓ Excel 报告生成成功")
                except Exception as e:
                    print(f"⚠ 警告: 生成 Excel 报告时出错: {e}")
            else:
                print("ℹ 未启用 Excel 报告，跳过生成")

        except FileNotFoundError as e:
            print(f"⚠ 警告: {e}")
            print("   可能是 Allure 报告未生成，跳过通知和报告生成")
        except Exception as e:
            print(f"⚠ 警告: 处理通知和报告时出错: {e}")
            traceback.print_exc()

    def step6_start_allure_server(self) -> None:
        """步骤6: 启动 Allure 报告服务器"""
        print("\n" + "=" * 60)
        print("启动 Allure 报告服务器")
        print("=" * 60)
        print("Allure 报告将在浏览器中自动打开")
        print("访问地址: http://127.0.0.1:9999")
        print("按 Ctrl+C 可停止服务器\n")

        try:
            os.system("allure serve ./report/tmp -h 127.0.0.1 -p 9999")
        except KeyboardInterrupt:
            print("\n\n用户中断，正在退出...")
        except Exception as e:
            print(f"⚠ 警告: 启动 Allure 服务器时出错: {e}")
            print("   请确认已安装 allure 命令行工具")

    def run_all(self) -> None:
        """执行完整流程"""
        try:
            # 显示项目名称的 ASCII 艺术（与 run.py 保持一致）
            INFO.logger.info(
                """
                             _    _         _      _____         _
              __ _ _ __ (_)  / \\  _   _| |_ __|_   _|__  ___| |_
             / _` | '_ \\| | / _ \\| | | | __/ _ \\| |/ _ \\/ __| __|
            | (_| | |_) | |/ ___ \\ |_| | || (_) | |  __/\\__ \\ |_
             \\__,_| .__|_/_/   \\_\\__,_|\\__\\___/|_|\\___||___/\\__|
                  |_|
                  开始执行{}项目...
                """.format(config.project_name)
            )

            print("\n" + "=" * 60)
            print("飞书接口测试用例自动生成和执行流程")
            print("=" * 60)
            print("\n本脚本将自动执行以下步骤：")
            print("1. 运行 feishu_calendar_generator.py 和 feishu_message_send_generator.py")
            print("2. 收集生成的测试用例")
            print("3. 执行所有测试用例（带 Allure 报告）")
            print("4. 生成 Allure HTML 报告")
            print("5. 发送测试结果通知和生成 Excel 报告")
            print("6. 启动 Allure 报告服务器")
            print("\n开始执行...\n")

            # 步骤1: 运行生成器
            self.step1_run_generators()

            # 步骤2: 收集测试用例
            test_paths = self.step2_collect_test_cases()

            # 步骤3: 执行测试（带 Allure 报告）
            exit_code = self.step3_run_tests(test_paths)

            # 步骤4: 生成 Allure HTML 报告
            self.step4_generate_allure_report()

            # 步骤5: 发送通知和生成 Excel 报告
            self.step5_send_notifications_and_reports()

            # 输出总结
            print("\n" + "=" * 60)
            print("执行完成总结")
            print("=" * 60)
            if exit_code == 0:
                print("✓ 所有测试用例执行成功")
            else:
                print(f"⚠ 部分测试用例失败，退出码: {exit_code}")
            print("=" * 60)

            # 步骤6: 启动 Allure 报告服务器
            self.step6_start_allure_server()

        except KeyboardInterrupt:
            print("\n\n用户中断，正在退出...")
            sys.exit(130)
        except Exception as e:
            # 如有异常，相关异常发送邮件（与 run.py 保持一致）
            error_msg = traceback.format_exc()
            print(f"\n✗ 执行过程中出错: {e}")
            print(error_msg)
            try:
                send_email = SendEmail(AllureFileClean.get_case_count())
                send_email.error_mail(error_msg)
            except Exception as email_error:
                print(f"⚠ 警告: 发送错误邮件失败: {email_error}")
            raise


def main():
    """主函数"""
    runner = FeishuTestRunner()
    runner.run_all()


if __name__ == "__main__":
    main()

