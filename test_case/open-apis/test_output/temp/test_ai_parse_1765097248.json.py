#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2025-12-08 19:57:10


import allure
import pytest
from utils.read_files_tools.get_yaml_data_analysis import GetTestCase
from utils.assertion.assert_control import Assert
from utils.requests_tool.request_control import RequestControl
from utils.read_files_tools.regular_control import regular
from utils.requests_tool.teardown_control import TearDownHandler


case_id = ['01_open-apis_test_output_temp_ai_parse_1765097248.json', '02_open-apis_test_output_temp_ai_parse_1765097248.json', '03_open-apis_test_output_temp_ai_parse_1765097248.json', '04_open-apis_test_output_temp_ai_parse_1765097248.json', '05_open-apis_test_output_temp_ai_parse_1765097248.json', '06_open-apis_test_output_temp_ai_parse_1765097248.json', '07_open-apis_test_output_temp_ai_parse_1765097248.json', '08_open-apis_test_output_temp_ai_parse_1765097248.json', '09_open-apis_test_output_temp_ai_parse_1765097248.json', '10_open-apis_test_output_temp_ai_parse_1765097248.json', '11_open-apis_test_output_temp_ai_parse_1765097248.json', '12_open-apis_test_output_temp_ai_parse_1765097248.json', '13_open-apis_test_output_temp_ai_parse_1765097248.json', '14_open-apis_test_output_temp_ai_parse_1765097248.json', '15_open-apis_test_output_temp_ai_parse_1765097248.json', '16_open-apis_test_output_temp_ai_parse_1765097248.json', '17_open-apis_test_output_temp_ai_parse_1765097248.json', '18_open-apis_test_output_temp_ai_parse_1765097248.json', '19_open-apis_test_output_temp_ai_parse_1765097248.json']
TestData = GetTestCase.case_data(case_id)
re_data = regular(str(TestData))


@allure.epic("API服务接口")
@allure.feature("获取临时解析结果")
class TestAiParse1765097248.json:

    @allure.story("获取临时解析结果")
    @pytest.mark.parametrize('in_data', eval(re_data), ids=[i['detail'] for i in TestData])
    def test_ai_parse_1765097248.json(self, in_data, case_skip):
        """
        :param :
        :return:
        """
        res = RequestControl(in_data).http_request()
        TearDownHandler(res).teardown_handle()
        Assert(in_data['assert_data']).assert_equality(response_data=res.response_data,
                                                       sql_data=res.sql_data, status_code=res.status_code)


if __name__ == '__main__':
    pytest.main(['test_ai_parse_1765097248.json.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])
