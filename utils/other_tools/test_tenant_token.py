#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试获取 tenant_access_token 的功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.other_tools.feishu_message_send_generator import FeishuMessageSendGenerator

# ================= 手动配置区域 =================
# 为避免交互式输入，这里提供默认的 app_id 和 app_secret
# 请将下面两个常量替换为你自己的应用凭证
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"
DEFAULT_APP_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"
# =================================================

def test_get_tenant_token():
    """测试获取 tenant_access_token"""
    print("=" * 60)
    print("测试获取 tenant_access_token 功能")
    print("=" * 60)
    
    generator = FeishuMessageSendGenerator()
    
    # 测试用例1: 从环境变量获取
    import os
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
    
    # 测试用例2: 从 feishu_token_updater.py 读取
    if not app_id or not app_secret:
        try:
            token_updater_path = Path(__file__).parent / "feishu_token_updater.py"
            if token_updater_path.exists():
                content = token_updater_path.read_text(encoding="utf-8")
                import re
                id_match = re.search(r'FEISHU_CLIENT_ID\s*=\s*["\']([^"\']+)["\']', content)
                secret_match = re.search(r'FEISHU_CLIENT_SECRET\s*=\s*["\']([^"\']+)["\']', content)
                if id_match and not app_id:
                    app_id = id_match.group(1)
                if secret_match and not app_secret:
                    app_secret = secret_match.group(1)
        except Exception as e:
            print(f"⚠ 从 feishu_token_updater.py 读取配置时出错: {e}")
    
    if not app_id or not app_secret:
        print("\n✗ 错误: 未提供 app_id 或 app_secret，无法测试")
        print("  请在文件开头的 DEFAULT_APP_ID/DEFAULT_APP_SECRET 中配置你的凭证。")
        return False
    
    print(f"\n使用以下配置:")
    print(f"  app_id: {app_id[:10]}..." if len(app_id) > 10 else f"  app_id: {app_id}")
    print(f"  app_secret: {'*' * min(len(app_secret), 10)}...")
    print("\n正在调用飞书 API 获取 tenant_access_token...\n")
    
    # 调用获取 token 的方法
    token = generator.get_tenant_access_token(app_id, app_secret)
    
    if token:
        print("\n" + "=" * 60)
        print("✓ 测试成功！")
        print("=" * 60)
        print(f"\n获取到的 tenant_access_token:")
        print(f"  {token[:50]}..." if len(token) > 50 else f"  {token}")
        print(f"\n完整 token: {token}")
        return True
    else:
        print("\n" + "=" * 60)
        print("✗ 测试失败！")
        print("=" * 60)
        return False

if __name__ == "__main__":
    try:
        success = test_get_tenant_token()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

