#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Allure 配置辅助工具

用于确保 Allure 报告正确显示中文
"""

import os
from pathlib import Path


def ensure_allure_properties_file(report_dir: str = "./report/tmp") -> None:
    """
    确保 Allure 配置文件存在，支持中文显示
    
    Args:
        report_dir: Allure 报告目录路径
    """
    report_path = Path(report_dir)
    
    # 确保目录存在
    report_path.mkdir(parents=True, exist_ok=True)
    
    # allure.properties 文件路径
    properties_file = report_path / "allure.properties"
    
    # 如果文件不存在或内容不完整，则创建/更新
    properties_content = """# Allure 报告配置
# 支持中文显示
allure.results.directory=.
allure.report.encoding=UTF-8
"""
    
    # 检查文件是否存在且内容正确
    if not properties_file.exists():
        properties_file.write_text(properties_content, encoding="utf-8")
    else:
        # 读取现有内容
        existing_content = properties_file.read_text(encoding="utf-8")
        # 如果缺少编码配置，则添加
        if "allure.report.encoding" not in existing_content:
            with properties_file.open("a", encoding="utf-8") as f:
                f.write("\n# 支持中文显示\n")
                f.write("allure.report.encoding=UTF-8\n")


if __name__ == "__main__":
    ensure_allure_properties_file()

