"""
# @Time   : 2022/3/28 16:08
# @Author : 余少琪
"""
import ast
import json
from typing import Text, Dict, Union, List
from jsonpath import jsonpath
from utils.requests_tool.request_control import RequestControl
from utils.mysql_tool.mysql_control import SetUpMySQL
from utils.read_files_tools.regular_control import regular, cache_regular
from utils.other_tools.jsonpath_date_replace import jsonpath_replace
from utils.logging_tool.log_control import WARNING
from utils.other_tools.models import DependentType
from utils.other_tools.models import TestCase, DependentCaseData, DependentData
from utils.other_tools.exceptions import ValueNotFoundError
from utils.cache_process.cache_control import CacheHandler
from utils import config


class DependentCase:
    """ 处理依赖相关的业务 """

    def __init__(self, dependent_yaml_case: TestCase):
        self.__yaml_case = dependent_yaml_case

    @classmethod
    def get_cache(cls, case_id: Text) -> Dict:
        """
        获取缓存用例池中的数据，通过 case_id 提取
        :param case_id:
        :return: case_id_01
        """
        _case_data = CacheHandler.get_cache(case_id)
        return _case_data

    @classmethod
    def jsonpath_data(
            cls,
            obj: Dict,
            expr: Text) -> list:
        """
        通过jsonpath提取依赖的数据
        :param obj: 对象信息
        :param expr: jsonpath 方法
        :return: 提取到的内容值,返回是个数组

        对象: {"data": applyID} --> jsonpath提取方法: $.data.data.[0].applyId
        """

        _jsonpath_data = jsonpath(obj, expr)
        # 判断是否正常提取到数据，如未提取到，则抛异常
        if _jsonpath_data is False:
            raise ValueNotFoundError(
                f"jsonpath提取失败！\n 提取的数据: {obj} \n jsonpath规则: {expr}"
            )
        return _jsonpath_data

    @classmethod
    def set_cache_value(cls, dependent_data: "DependentData") -> Union[Text, None]:
        """
        获取依赖中是否需要将数据存入缓存中
        """
        try:
            return dependent_data.set_cache
        except KeyError:
            return None

    @classmethod
    def replace_key(cls, dependent_data: "DependentData"):
        """ 获取需要替换的内容 """
        try:
            _replace_key = dependent_data.replace_key
            return _replace_key
        except KeyError:
            return None

    def url_replace(
            self,
            replace_key: Text,
            jsonpath_dates: Dict,
            jsonpath_data: list) -> None:
        """
        url中的动态参数替换
        # 如: 一般有些接口的参数在url中,并且没有参数名称, /api/v1/work/spu/approval/spuApplyDetails/{id}
        # 那么可以使用如下方式编写用例, 可以使用 $url_params{}替换,
        # 如/api/v1/work/spu/approval/spuApplyDetails/$url_params{id}
        :param jsonpath_data: jsonpath 解析出来的数据值
        :param replace_key: 用例中需要替换数据的 replace_key
        :param jsonpath_dates: jsonpath 存放的数据值
        :return:
        """

        if "$url_param" in replace_key:
            _url = self.__yaml_case.url.replace(replace_key, str(jsonpath_data[0]))
            jsonpath_dates['$.url'] = _url
        else:
            jsonpath_dates[replace_key] = jsonpath_data[0]

    def _dependent_type_for_sql(
            self,
            setup_sql: List,
            dependence_case_data: "DependentCaseData",
            jsonpath_dates: Dict) -> None:
        """
        判断依赖类型为 sql，程序中的依赖参数从 数据库中提取数据
        @param setup_sql: 前置sql语句
        @param dependence_case_data: 依赖的数据
        @param jsonpath_dates: 依赖相关的用例数据
        @return:
        """
        # 判断依赖数据类型，依赖 sql中的数据
        if setup_sql is not None:
            if config.mysql_db.switch:
                setup_sql = ast.literal_eval(cache_regular(str(setup_sql)))
                sql_data = SetUpMySQL().setup_sql_data(sql=setup_sql)
                dependent_data = dependence_case_data.dependent_data
                for i in dependent_data:
                    _jsonpath = i.jsonpath
                    jsonpath_data = self.jsonpath_data(obj=sql_data, expr=_jsonpath)
                    _set_value = self.set_cache_value(i)
                    _replace_key = self.replace_key(i)
                    if _set_value is not None:
                        CacheHandler.update_cache(cache_name=_set_value, value=jsonpath_data[0])
                        # Cache(_set_value).set_caches(jsonpath_data[0])
                    if _replace_key is not None:
                        jsonpath_dates[_replace_key] = jsonpath_data[0]
                        self.url_replace(
                            replace_key=_replace_key,
                            jsonpath_dates=jsonpath_dates,
                            jsonpath_data=jsonpath_data,
                        )
            else:
                WARNING.logger.warning("检查到数据库开关为关闭状态，请确认配置")

    def dependent_handler(
            self,
            _jsonpath: Text,
            set_value: Text,
            replace_key: Text,
            jsonpath_dates: Dict,
            data: Dict,
            dependent_type: int
    ) -> None:
        """ 处理数据替换 """
        jsonpath_data = self.jsonpath_data(
            data,
            _jsonpath
        )
        if set_value is not None:
            if len(jsonpath_data) > 1:
                CacheHandler.update_cache(cache_name=set_value, value=jsonpath_data)
            else:
                CacheHandler.update_cache(cache_name=set_value, value=jsonpath_data[0])
        if replace_key is not None:
            if dependent_type == 0:
                # 特殊处理：如果 replace_key 是 data.content，且当前 content 值包含 $cache{redis:xxx} 格式
                # 需要替换 JSON 字符串中的占位符，而不是替换整个 content 字段
                if replace_key == "data.content" or replace_key.endswith(".content"):
                    # 获取当前的 content 值（从 yaml_case.data 中获取原始值）
                    current_content = None
                    try:
                        if hasattr(self, '__yaml_case') and hasattr(self.__yaml_case, 'data'):
                            # replace_key 格式是 "data.content"，需要获取 "content" 字段
                            content_field = replace_key.split(".")[-1]  # 获取 "content"
                            if isinstance(self.__yaml_case.data, dict):
                                current_content = self.__yaml_case.data.get(content_field)
                    except Exception:
                        pass
                    
                    # 如果当前 content 是字符串且包含 $cache{redis:xxx} 格式，进行替换
                    if current_content and isinstance(current_content, str):
                        import re
                        # 查找 $cache{redis:xxx} 格式的占位符
                        cache_pattern = r'\$cache\{redis:([^}]+)\}'
                        if re.search(cache_pattern, current_content):
                            # 替换占位符为实际值
                            replaced_content = re.sub(cache_pattern, jsonpath_data[0], current_content)
                            jsonpath_dates[replace_key] = replaced_content
                        else:
                            # 如果没有占位符，直接替换
                            jsonpath_dates[replace_key] = jsonpath_data[0]
                    else:
                        # 如果当前 content 不是字符串或不存在，直接替换
                        jsonpath_dates[replace_key] = jsonpath_data[0]
                else:
                    jsonpath_dates[replace_key] = jsonpath_data[0]
            self.url_replace(replace_key=replace_key, jsonpath_dates=jsonpath_dates,
                             jsonpath_data=jsonpath_data)

    def is_dependent(self) -> Union[Dict, bool]:
        """
        判断是否有数据依赖
        :return:
        """

        # 获取用例中的dependent_type值，判断该用例是否需要执行依赖
        _dependent_type = self.__yaml_case.dependence_case
        # 获取依赖用例数据
        _dependence_case_dates = self.__yaml_case.dependence_case_data
        _setup_sql = self.__yaml_case.setup_sql
        # 判断是否有依赖
        if _dependent_type is True:
            # 读取依赖相关的用例数据
            jsonpath_dates = {}
            # 循环所有需要依赖的数据
            try:
                for dependence_case_data in _dependence_case_dates:
                    _case_id = dependence_case_data.case_id
                    # 判断依赖数据为sql，case_id需要写成self，否则程序中无法获取case_id
                    if _case_id == 'self':
                        self._dependent_type_for_sql(
                            setup_sql=_setup_sql,
                            dependence_case_data=dependence_case_data,
                            jsonpath_dates=jsonpath_dates)
                    else:
                        re_data = regular(str(self.get_cache(_case_id)))
                        re_data = ast.literal_eval(cache_regular(str(re_data)))
                        
                        # 如果当前用例有 Authorization token，尝试使用当前用例的 token 替换依赖用例的 token
                        # 这样可以避免依赖用例的 token 过期问题
                        current_headers = self.__yaml_case.headers
                        if current_headers and isinstance(current_headers, dict):
                            current_token = current_headers.get("Authorization")
                            if current_token and current_token.startswith("Bearer "):
                                # 更新依赖用例的 headers，使用当前用例的 token
                                if re_data.get("headers") is None:
                                    re_data["headers"] = {}
                                elif not isinstance(re_data["headers"], dict):
                                    re_data["headers"] = dict(re_data["headers"])
                                re_data["headers"]["Authorization"] = current_token
                        
                        res = RequestControl(re_data).http_request()
                        if dependence_case_data.dependent_data is not None:
                            dependent_data = dependence_case_data.dependent_data
                            for i in dependent_data:

                                _case_id = dependence_case_data.case_id
                                _jsonpath = i.jsonpath
                                _request_data = self.__yaml_case.data
                                _replace_key = self.replace_key(i)
                                _set_value = self.set_cache_value(i)
                                # 判断依赖数据类型, 依赖 response 中的数据
                                if i.dependent_type == DependentType.RESPONSE.value:
                                    try:
                                        response_data = json.loads(res.response_data)
                                        # 检查飞书 API 响应，如果 code != 0，说明依赖用例执行失败，直接抛出错误
                                        if isinstance(response_data, dict) and response_data.get("code") != 0:
                                            error_code = response_data.get('code')
                                            error_msg = response_data.get('msg', '')
                                            WARNING.logger.warning(
                                                f"依赖用例 {_case_id} 执行失败: code={error_code}, "
                                                f"msg={error_msg}。响应: {res.response_data[:200]}"
                                            )
                                            raise ValueNotFoundError(
                                                f"依赖用例 {_case_id} 执行失败，无法提取数据。"
                                                f"错误码: {error_code}, 错误信息: {error_msg}。"
                                                f"请检查依赖用例是否正确执行。"
                                            )
                                    except json.JSONDecodeError as e:
                                        WARNING.logger.warning(
                                            f"依赖用例 {_case_id} 响应不是有效的 JSON: {e}。响应: {res.response_data[:200]}"
                                        )
                                        raise ValueNotFoundError(
                                            f"依赖用例 {_case_id} 响应格式错误，无法提取数据"
                                        ) from e
                                    
                                    self.dependent_handler(
                                        data=response_data,
                                        _jsonpath=_jsonpath,
                                        set_value=_set_value,
                                        replace_key=_replace_key,
                                        jsonpath_dates=jsonpath_dates,
                                        dependent_type=0
                                    )

                                # 判断依赖数据类型, 依赖 request 中的数据
                                elif i.dependent_type == DependentType.REQUEST.value:
                                    self.dependent_handler(
                                        data=res.body,
                                        _jsonpath=_jsonpath,
                                        set_value=_set_value,
                                        replace_key=_replace_key,
                                        jsonpath_dates=jsonpath_dates,
                                        dependent_type=1
                                    )

                                else:
                                    raise ValueError(
                                        "依赖的dependent_type不正确，只支持request、response、sql依赖\n"
                                        f"当前填写内容: {i.dependent_type}"
                                    )
                return jsonpath_dates
            except KeyError as exc:
                # pass
                raise ValueNotFoundError(
                    f"dependence_case_data依赖用例中，未找到 {exc} 参数，请检查是否填写"
                    f"如已填写，请检查是否存在yaml缩进问题"
                ) from exc
            except TypeError as exc:
                raise ValueNotFoundError(
                    "dependence_case_data下的所有内容均不能为空！"
                    "请检查相关数据是否填写，如已填写，请检查缩进问题"
                ) from exc
        else:
            return False

    def get_dependent_data(self) -> None:
        """
        jsonpath 和 依赖的数据,进行替换
        :return:
        """
        _dependent_data = DependentCase(self.__yaml_case).is_dependent()
        _new_data = None
        # 判断有依赖
        if _dependent_data is not None and _dependent_data is not False:
            # if _dependent_data is not False:
            for key, value in _dependent_data.items():
                # 通过jsonpath判断出需要替换数据的位置
                _change_data = key.split(".")
                # jsonpath 数据解析
                # 不要删 这个yaml_case
                yaml_case = self.__yaml_case
                _new_data = jsonpath_replace(change_data=_change_data, key_name='yaml_case')
                # 最终提取到的数据,转换成 __yaml_case.data
                # 特殊处理：如果 key 是 data.content，且原始值包含 $cache{redis:xxx} 格式
                # 需要保持 JSON 格式，而不是直接替换
                if key == "data.content" or key.endswith(".content"):
                    # 获取原始 content 值
                    original_content = None
                    try:
                        if hasattr(self.__yaml_case, 'data') and isinstance(self.__yaml_case.data, dict):
                            content_field = key.split(".")[-1]  # 获取 "content"
                            original_content = self.__yaml_case.data.get(content_field)
                    except:
                        pass
                    
                    # 如果原始 content 是字符串且包含 $cache{redis:xxx} 格式，且 value 不包含 JSON 结构
                    # 说明 value 是直接的 image_key 值，需要构建 JSON 格式
                    if original_content and isinstance(original_content, str):
                        import re
                        cache_pattern = r'\$cache\{redis:([^}]+)\}'
                        if re.search(cache_pattern, original_content):
                            # 原始值包含占位符，value 应该是替换后的值
                            # 检查 value 是否是直接的 image_key（不包含 JSON 结构）
                            if isinstance(value, str) and not value.strip().startswith('{'):
                                # value 是直接的 image_key，需要构建 JSON 格式
                                # 从原始值中提取 JSON 结构，替换占位符
                                replaced_content = re.sub(cache_pattern, value, original_content)
                                value = replaced_content
                
                # 如果值是字符串，需要加引号；如果是数字、布尔值等，直接使用
                if isinstance(value, str):
                    # 字符串值需要加引号，并转义内部引号
                    escaped_value = value.replace('"', '\\"')
                    _new_data += f' = "{escaped_value}"'
                else:
                    _new_data += ' = ' + str(value)
                exec(_new_data)
