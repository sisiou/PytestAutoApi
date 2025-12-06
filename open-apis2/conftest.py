#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : Auto-generated for open-apis2 test cases
# 此文件用于定义 open-apis2 目录下测试用例需要的 fixture
# 注意：不导入 test_case.conftest，避免触发 test_case/__init__.py 的执行导致 case_id 冲突

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import ast
import allure
from utils.requests_tool.request_control import cache_regular
from utils.other_tools.models import TestCase
from utils.other_tools.allure_data.allure_tools import allure_step, allure_step_no


@pytest.fixture(scope="function", autouse=True)
def case_skip(in_data):
    """处理跳过用例"""
    in_data = TestCase(**in_data)
    if ast.literal_eval(cache_regular(str(in_data.is_run))) is False:
        allure.dynamic.title(in_data.detail)
        allure_step_no(f"请求URL: {in_data.is_run}")
        allure_step_no(f"请求方式: {in_data.method}")
        allure_step("请求头: ", in_data.headers)
        allure_step("请求数据: ", in_data.data)
        allure_step("依赖数据: ", in_data.dependence_case_data)
        allure_step("预期数据: ", in_data.assert_data)
        pytest.skip()


def pytest_configure(config):
    """pytest 配置"""
    config.addinivalue_line("markers", '回归测试')


def pytest_collection_modifyitems(items):
    """
    测试用例收集完成时，将收集到的 item 的 name 和 node_id 的中文显示在控制台上
    """
    for item in items:
        item.name = item.name.encode("utf-8").decode("unicode_escape")
        item._nodeid = item.nodeid.encode("utf-8").decode("unicode_escape")

