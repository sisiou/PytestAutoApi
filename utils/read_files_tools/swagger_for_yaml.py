#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2022/8/11 10:51
# @Author : 余少琪
"""
import json
from jsonpath import jsonpath
from common.setting import ensure_path_sep
from typing import Dict, Optional
from ruamel import yaml
import os
from urllib.parse import urlparse


class SwaggerForYaml:
    def __init__(self):
        self._data = self.get_swagger_json()
        self._host = self.get_host()

    @classmethod
    def get_swagger_json(cls):
        """
        获取 swagger 中的 json 数据
        :return:
        """
        try:
            with open('./interfacetest/userInfo.json', "r", encoding='utf-8') as f:
                row_data = json.load(f)
                return row_data
        except FileNotFoundError:
            raise FileNotFoundError("文件路径不存在，请重新输入")

    def get_allure_epic(self):
        """ 获取 yaml 用例中的 allure_epic """
        _allure_epic = self._data['info']['title']
        return _allure_epic

    @classmethod
    def get_allure_feature(cls, value):
        """ 获取 yaml 用例中的 allure_feature """
        _allure_feature = value['tags']
        return str(_allure_feature)

    @classmethod
    def get_allure_story(cls, value):
        """ 获取 yaml 用例中的 allure_story """
        _allure_story = value['summary']
        return _allure_story

    @classmethod
    def get_case_id(cls, value):
        """ 获取 case_id """
        _case_id = value.replace("/", "_")
        return "01" + _case_id

    @classmethod
    def get_detail(cls, value):
        _get_detail = value['summary']
        return "测试" + _get_detail

    @classmethod
    def get_request_type(cls, value, headers):
        """ 处理 request_type """
        non_header_params = []
        if jsonpath(obj=value, expr="$.parameters") is not False:
            for parameter in value['parameters']:
                if parameter.get('in') != 'header':
                    non_header_params.append(parameter)

        content_types = []
        if headers:
            header_content_type = headers.get('Content-Type')
            if header_content_type:
                content_types.append(header_content_type)

        if value.get('consumes'):
            content_types.extend(value.get('consumes'))

        if value.get('requestBody'):
            request_body = value['requestBody']
            content = request_body.get('content', {})
            content_types.extend(list(content.keys()))

        normalized_content_types = [ct.lower() for ct in content_types if isinstance(ct, str)]

        if any('multipart/form-data' in ct or 'application/x-www-form-urlencoded' in ct for ct in normalized_content_types):
            return "data"
        if any('application/json' in ct for ct in normalized_content_types):
            return "json"
        if any('application/octet-stream' in ct for ct in normalized_content_types):
            return "file"

        if non_header_params:
            first_param = non_header_params[0]
            if first_param.get('in') == 'query':
                return "params"
            return "data"

        return "NONE"

    @classmethod
    def get_case_data(cls, value):
        """ 处理 data 数据 """
        _dict = {}
        if jsonpath(obj=value, expr="$.parameters") is not False:
            _parameters = value['parameters']
            for i in _parameters:
                if i['in'] == 'header':
                    ...
                else:
                    _dict[i['name']] = None
        else:
            return None
        return _dict or None

    @classmethod
    def yaml_cases(cls, data: Dict, file_path: str) -> None:
        """
        写入 yaml 数据
        :param file_path:
        :param data: 测试用例数据
        :return:
        """

        _file_path = ensure_path_sep("\\data\\" + file_path[1:].replace("/", os.sep) + '.yaml')
        _file = _file_path.split(os.sep)[:-1]
        _dir_path = ''
        for i in _file:
            _dir_path += i + os.sep
        try:
            os.makedirs(_dir_path)
        except FileExistsError:
            ...
        # 使用写入模式（"w"）而不是追加模式（"a"），避免重复内容
        with open(_file_path, "w", encoding="utf-8") as file:
            yaml.dump(data, file, Dumper=yaml.RoundTripDumper, allow_unicode=True)
            file.write('\n')

    @classmethod
    def _get_parameter_example(cls, parameter: Dict) -> Optional[str]:
        schema = parameter.get('schema', {})
        if isinstance(schema, dict):
            example = schema.get('example')
            if example is not None:
                return example
            default = schema.get('default')
            if default is not None:
                return default
        if parameter.get('example') is not None:
            return parameter['example']
        examples = parameter.get('examples')
        if isinstance(examples, dict) and examples:
            first = next(iter(examples.values()))
            if isinstance(first, dict):
                return first.get('value')
        return None

    @classmethod
    def get_headers(cls, value):
        """ 获取请求头 """
        _headers = {}
        if jsonpath(obj=value, expr="$.consumes") is not False:
            _headers = {"Content-Type": value['consumes'][0]}
        elif value.get('requestBody'):
            content = value['requestBody'].get('content', {})
            if content:
                _headers["Content-Type"] = next(iter(content.keys()))

        if jsonpath(obj=value, expr="$.parameters") is not False:
            for i in value['parameters']:
                if i['in'] == 'header':
                    _headers[i['name']] = cls._get_parameter_example(i)

        return _headers or None

    def get_host(self):
        """获取 host """
        servers = self._data.get('servers')
        if isinstance(servers, list):
            for server in servers:
                url = server.get('url')
                if url:
                    return url.rstrip('/')

        request_info = self._data.get('request', {})
        request_url = request_info.get('url')
        if request_url:
            parsed = urlparse(request_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}".rstrip('/')

        host = self._data.get('host')
        if host:
            schemes = self._data.get('schemes', ['http'])
            scheme = schemes[0] if schemes else 'http'
            return f"{scheme}://{host}".rstrip('/')

        return "${{host()}}"

    def write_yaml_handler(self):

        _api_data = self._data['paths']
        for key, value in _api_data.items():
            for k, v in value.items():
                headers = self.get_headers(v)
                request_type = self.get_request_type(v, headers)
                yaml_data = {
                    "case_common": {"allureEpic": self.get_allure_epic(), "allureFeature": self.get_allure_feature(v),
                                    "allureStory": self.get_allure_story(v)},
                    self.get_case_id(key): {
                        "host": self._host, "url": key, "method": k, "detail": self.get_detail(v),
                        "headers": headers, "requestType": request_type,
                        "is_run": None, "data": self.get_case_data(v), "dependence_case": False,
                        "assert": {"status_code": 200}, "sql": None}}
                self.yaml_cases(yaml_data, file_path=key)


if __name__ == '__main__':
    SwaggerForYaml().write_yaml_handler()
