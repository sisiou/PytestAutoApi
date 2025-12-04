#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试更新 YAML 文件中的 tenant_access_token
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.other_tools.feishu_message_send_generator import FeishuMessageSendGenerator

def test_update_yaml():
    """测试更新 YAML 文件中的 token"""
    print("=" * 60)
    print("测试更新 YAML 文件中的 tenant_access_token")
    print("=" * 60)
    
    generator = FeishuMessageSendGenerator()
    
    # 先获取一个测试 token
    import os
    app_id = os.getenv("FEISHU_APP_ID") or os.getenv("FEISHU_CLIENT_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET") or os.getenv("FEISHU_CLIENT_SECRET")
    
    # 从 feishu_token_updater.py 读取
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
        print("\n✗ 错误: 未提供 app_id 或 app_secret，无法获取 token")
        return False
    
    print("\n步骤 1: 获取 tenant_access_token...")
    token = generator.get_tenant_access_token(app_id, app_secret)
    
    if not token:
        print("\n✗ 获取 token 失败，无法继续测试")
        return False
    
    print(f"\n步骤 2: 更新 YAML 文件...")
    yaml_path = Path("data/open-apis/im/v1/messages.yaml")
    
    if not yaml_path.exists():
        print(f"⚠ 警告: YAML 文件不存在: {yaml_path}")
        print("   请先运行生成脚本创建 YAML 文件")
        return False
    
    # 备份原文件
    backup_path = yaml_path.with_suffix('.yaml.backup')
    try:
        import shutil
        shutil.copy2(yaml_path, backup_path)
        print(f"✓ 已备份原文件到: {backup_path}")
    except Exception as e:
        print(f"⚠ 备份文件失败: {e}")
        backup_path = None
    
    # 更新 YAML 文件
    success = generator.update_yaml_with_token(yaml_path, token)
    
    if success:
        print("\n" + "=" * 60)
        print("✓ 测试成功！YAML 文件已更新")
        print("=" * 60)
        
        # 读取并显示更新后的内容
        try:
            import ruamel.yaml
            yaml = ruamel.yaml.YAML()
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.load(f)
            
            print("\n更新后的 YAML 文件内容:")
            for key, value in data.items():
                if key != "case_common" and isinstance(value, dict):
                    headers = value.get("headers", {})
                    auth = headers.get("Authorization", "")
                    print(f"  用例: {key}")
                    print(f"  Authorization: {auth[:50]}..." if len(auth) > 50 else f"  Authorization: {auth}")
        except Exception as e:
            print(f"⚠ 读取 YAML 文件时出错: {e}")
        
        # 询问是否恢复备份
        if backup_path and backup_path.exists():
            try:
                user_input = input("\n是否恢复备份文件? (y/n): ").strip().lower()
                if user_input == 'y':
                    shutil.copy2(backup_path, yaml_path)
                    print("✓ 已恢复备份文件")
                else:
                    print("保留更新后的文件")
            except (EOFError, KeyboardInterrupt):
                print("\n保留更新后的文件")
        
        return True
    else:
        print("\n" + "=" * 60)
        print("✗ 测试失败！YAML 文件更新失败")
        print("=" * 60)
        
        # 恢复备份
        if backup_path and backup_path.exists():
            try:
                import shutil
                shutil.copy2(backup_path, yaml_path)
                print("✓ 已恢复备份文件")
            except Exception as e:
                print(f"⚠ 恢复备份文件失败: {e}")
        
        return False

if __name__ == "__main__":
    try:
        success = test_update_yaml()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

