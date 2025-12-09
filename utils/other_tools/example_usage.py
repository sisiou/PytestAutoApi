#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用AI测试用例生成器使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.other_tools.universal_ai_test_generator import UniversalAITestGenerator

def example_1():
    """示例1：生成飞书消息流卡片接口测试用例"""
    print("=" * 60)
    print("示例1：生成飞书消息流卡片接口测试用例")
    print("=" * 60)
    
    generator = UniversalAITestGenerator()
    
    result = generator.generate_all(
        base_name="feishu_im-v2_app_feed_card_create",
        base_dir="uploads",
        output_dir="tests"
    )
    
    if "error" not in result:
        print(f"\n✅ 成功生成 {result['total_test_cases']} 个测试用例")
        print(f"   - 边界值测试: {result['boundary_test_cases']} 个")
        print(f"   - 异常值测试: {result['exception_test_cases']} 个")
    else:
        print(f"\n❌ 生成失败: {result['error']}")

def example_2():
    """示例2：生成卡片创建接口测试用例"""
    print("\n" + "=" * 60)
    print("示例2：生成卡片创建接口测试用例")
    print("=" * 60)
    
    generator = UniversalAITestGenerator()
    
    result = generator.generate_all(
        base_name="feishu_cardkit-v1_card_create",
        base_dir="uploads",
        output_dir="tests"
    )
    
    if "error" not in result:
        print(f"\n✅ 成功生成 {result['total_test_cases']} 个测试用例")
    else:
        print(f"\n❌ 生成失败: {result['error']}")

def example_3():
    """示例3：使用自定义配置"""
    print("\n" + "=" * 60)
    print("示例3：使用自定义配置")
    print("=" * 60)
    
    # 使用自定义API Key和App凭证
    generator = UniversalAITestGenerator(
        api_key="your-api-key-here",
        app_id="your-app-id",
        app_secret="your-app-secret"
    )
    
    result = generator.generate_all(
        base_name="feishu_im-v2_app_feed_card_create",
        base_dir="uploads",
        output_dir="tests/custom"
    )
    
    if "error" not in result:
        print(f"\n✅ 成功生成测试用例")
    else:
        print(f"\n❌ 生成失败: {result['error']}")

if __name__ == "__main__":
    # 运行示例1
    example_1()
    
    # 取消注释以运行其他示例
    # example_2()
    # example_3()

