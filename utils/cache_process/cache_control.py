#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:28
# @Author : 余少琪

"""
缓存文件处理
"""

import os
from typing import Any, Text, Union
from common.setting import ensure_path_sep
from utils.other_tools.exceptions import ValueNotFoundError

# 可选依赖：Redis 缓存
try:
    from utils.cache_process.redis_control import RedisHandler
except Exception:  # noqa: BLE001
    RedisHandler = None


class Cache:
    """ 设置、读取缓存 """
    def __init__(self, filename: Union[Text, None]) -> None:
        # 如果filename不为空，则操作指定文件内容
        if filename:
            self.path = ensure_path_sep("\\cache" + filename)
        # 如果filename为None，则操作所有文件内容
        else:
            self.path = ensure_path_sep("\\cache")

    def set_cache(self, key: Text, value: Any) -> None:
        """
        设置缓存, 只支持设置单字典类型缓存数据, 缓存文件如以存在,则替换之前的缓存内容
        :return:
        """
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write(str({key: value}))

    def set_caches(self, value: Any) -> None:
        """
        设置多组缓存数据
        :param value: 缓存内容
        :return:
        """
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write(str(value))

    def get_cache(self) -> Any:
        """
        获取缓存数据
        :return:
        """
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            pass

    def clean_cache(self) -> None:
        """删除所有缓存文件"""

        if not os.path.exists(self.path):
            raise FileNotFoundError(f"您要删除的缓存文件不存在 {self.path}")
        os.remove(self.path)

    @classmethod
    def clean_all_cache(cls) -> None:
        """
        清除所有缓存文件
        :return:
        """
        cache_path = ensure_path_sep("\\cache")

        # 列出目录下所有文件，生成一个list
        list_dir = os.listdir(cache_path)
        for i in list_dir:
            # 循环删除文件夹下得所有内容
            os.remove(cache_path + i)


_cache_config = {}


class CacheHandler:
    @staticmethod
    def get_cache(cache_data):
        """
        读取缓存：
        - 普通缓存：从内存字典 _cache_config 读取
        - Redis 缓存：cache_data 以 'redis:' 前缀时，从 Redis 读取（依赖 redis_control.py 配置）
        """
        # 检查是否是 Redis 缓存
        if cache_data.startswith("redis:"):
            if RedisHandler is None:
                raise ValueError("未安装或未配置 redis 依赖，无法读取 Redis 缓存")
            key = cache_data.replace("redis:", "", 1)
            try:
                value = RedisHandler().get_key(key)
                if value is None:
                    raise ValueNotFoundError(f"Redis 缓存中未找到 key: {key}，请检查是否将该数据存入缓存中")
                return value
            except Exception as e:  # noqa: BLE001
                raise ValueNotFoundError(f"读取 Redis 缓存失败: {key}，错误: {e}")
        
        # 普通内存缓存
        try:
            return _cache_config[cache_data]
        except KeyError:
            raise ValueNotFoundError(f"{cache_data}的缓存数据未找到，请检查是否将该数据存入缓存中")

    @staticmethod
    def update_cache(*, cache_name, value):
        """
        写入缓存：
        - 普通缓存：存入内存字典 _cache_config
        - Redis 缓存：cache_name 以 'redis:' 前缀时，写入 Redis（依赖 redis_control.py 配置）
        """
        if cache_name.startswith("redis:"):
            if RedisHandler is None:
                raise ValueError("未安装或未配置 redis 依赖，无法写入 Redis 缓存")
            key = cache_name.replace("redis:", "", 1)
            try:
                RedisHandler().set_string(key, value)
                # 添加日志确认 Redis 写入成功
                try:
                    from utils.logging_tool.log_control import INFO
                    INFO.logger.info(f"✓ 成功写入 Redis 缓存: {key} = {value}")
                except Exception:  # noqa: BLE001
                    # 如果日志模块不可用，使用 print
                    print(f"✓ 成功写入 Redis 缓存: {key} = {value}")
            except Exception as e:  # noqa: BLE001
                try:
                    from utils.logging_tool.log_control import ERROR
                    ERROR.logger.error(f"✗ Redis 缓存写入失败: {key} = {value}, 错误: {e}")
                except Exception:  # noqa: BLE001
                    print(f"✗ Redis 缓存写入失败: {key} = {value}, 错误: {e}")
                raise
        else:
            _cache_config[cache_name] = value
            try:
                from utils.logging_tool.log_control import INFO
                INFO.logger.info(f"✓ 成功写入内存缓存: {cache_name} = {value}")
            except Exception:  # noqa: BLE001
                pass
