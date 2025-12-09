#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pytest配置文件
"""

import pytest
import os


def pytest_configure(config):
    """pytest配置钩子"""
    # 添加自定义标记
    config.addinivalue_line("markers", "normal: 正常场景测试")
    config.addinivalue_line("markers", "exception: 异常场景测试")
    config.addinivalue_line("markers", "xfail: 预期失败测试")


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    for item in items:
        # 为所有测试添加默认标记
        if not any(mark.name for mark in item.own_markers):
            item.add_marker(pytest.mark.normal)
