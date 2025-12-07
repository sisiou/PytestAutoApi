#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书URL测试用例生成器启动脚本
使用方法:
  python run_url_to_testcase.py --url "https://open.feishu.cn/open-apis/docx/v1/documents..."
  python run_url_to_testcase.py --urls urls.txt
  python run_url_to_testcase.py --server
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 直接导入并执行主函数
if __name__ == "__main__":
    from utils.integration.url_to_testcase_integration import main
    main()