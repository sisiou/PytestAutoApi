#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2023/07/01 10:00
# @Author : Smart Auto Platform
# @File   : data_preparation.py
# @describe: 前置数据准备模块，自动生成和管理测试数据
"""

import os
import json
import random
import string
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from utils.logging_tool.log_control import INFO, ERROR, WARNING
from utils.other_tools.exceptions import DataPreparationError
from utils.requests_tool.request_control import RequestControl
from utils.read_files_tools.yaml_control import GetYamlData


class DataType(Enum):
    """数据类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    PHONE = "phone"
    UUID = "uuid"
    JSON = "json"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class DataField:
    """数据字段"""
    name: str
    data_type: DataType
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    enum_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    default_value: Any = None
    unique: bool = False
    foreign_key: Optional[str] = None
    description: str = ""


@dataclass
class DataEntity:
    """数据实体"""
    name: str
    table_name: Optional[str] = None
    fields: List[DataField] = None
    dependencies: List[str] = None
    cleanup_sql: Optional[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class DataRecord:
    """数据记录"""
    entity_name: str
    data: Dict[str, Any]
    record_id: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_temporary: bool = False


class DataGenerator:
    """数据生成器"""
    
    def __init__(self):
        """初始化数据生成器"""
        self.generators = {
            DataType.STRING: self._generate_string,
            DataType.INTEGER: self._generate_integer,
            DataType.FLOAT: self._generate_float,
            DataType.BOOLEAN: self._generate_boolean,
            DataType.DATE: self._generate_date,
            DataType.DATETIME: self._generate_datetime,
            DataType.EMAIL: self._generate_email,
            DataType.PHONE: self._generate_phone,
            DataType.UUID: self._generate_uuid,
            DataType.JSON: self._generate_json,
            DataType.ARRAY: self._generate_array,
            DataType.OBJECT: self._generate_object
        }
        
    def generate_data(self, data_type: DataType, field: DataField = None) -> Any:
        """
        生成数据
        :param data_type: 数据类型
        :param field: 数据字段
        :return: 生成的数据
        """
        try:
            generator = self.generators.get(data_type)
            if not generator:
                raise ValueError(f"不支持的数据类型: {data_type}")
                
            return generator(field)
            
        except Exception as e:
            ERROR.logger.error(f"生成数据失败: {str(e)}")
            raise DataPreparationError(f"生成数据失败: {str(e)}")
            
    def _generate_string(self, field: DataField = None) -> str:
        """生成字符串"""
        if not field:
            return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return field.default_value
            
        # 根据字段名生成特定格式的字符串
        field_name = field.name.lower()
        
        if 'email' in field_name:
            return self._generate_email()
        elif 'phone' in field_name or 'mobile' in field_name:
            return self._generate_phone()
        elif 'date' in field_name:
            return self._generate_date()
        elif 'id' in field_name and 'uuid' in field_name:
            return self._generate_uuid()
        elif 'password' in field_name:
            return self._generate_password()
        elif 'name' in field_name:
            return self._generate_name()
        elif 'address' in field_name:
            return self._generate_address()
            
        # 生成随机字符串
        min_length = field.min_length or 1
        max_length = field.max_length or 50
        
        # 确保最小长度不大于最大长度
        if min_length > max_length:
            min_length, max_length = max_length, min_length
            
        length = random.randint(min_length, max_length)
        
        # 如果有模式，尝试匹配模式
        if field.pattern:
            return self._generate_by_pattern(field.pattern, length)
            
        # 生成随机字符串
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        
    def _generate_integer(self, field: DataField = None) -> int:
        """生成整数"""
        if not field:
            return random.randint(1, 100)
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return field.default_value
            
        # 根据字段名生成特定范围的整数
        field_name = field.name.lower()
        
        if 'age' in field_name:
            return random.randint(18, 65)
        elif 'year' in field_name:
            return random.randint(2000, 2023)
        elif 'month' in field_name:
            return random.randint(1, 12)
        elif 'day' in field_name:
            return random.randint(1, 28)
        elif 'hour' in field_name:
            return random.randint(0, 23)
        elif 'minute' in field_name or 'second' in field_name:
            return random.randint(0, 59)
            
        # 根据最小值和最大值生成整数
        min_value = field.min_value or 1
        max_value = field.max_value or 100
        
        # 确保最小值不大于最大值
        if min_value > max_value:
            min_value, max_value = max_value, min_value
            
        return random.randint(min_value, max_value)
        
    def _generate_float(self, field: DataField = None) -> float:
        """生成浮点数"""
        if not field:
            return round(random.uniform(0.0, 100.0), 2)
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return float(field.default_value)
            
        # 根据字段名生成特定范围的浮点数
        field_name = field.name.lower()
        
        if 'price' in field_name or 'cost' in field_name:
            return round(random.uniform(10.0, 1000.0), 2)
        elif 'rate' in field_name or 'ratio' in field_name:
            return round(random.uniform(0.0, 1.0), 4)
        elif 'score' in field_name:
            return round(random.uniform(0.0, 100.0), 2)
            
        # 根据最小值和最大值生成浮点数
        min_value = float(field.min_value or 0.0)
        max_value = float(field.max_value or 100.0)
        
        # 确保最小值不大于最大值
        if min_value > max_value:
            min_value, max_value = max_value, min_value
            
        return round(random.uniform(min_value, max_value), 2)
        
    def _generate_boolean(self, field: DataField = None) -> bool:
        """生成布尔值"""
        if not field:
            return random.choice([True, False])
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return bool(field.default_value)
            
        return random.choice([True, False])
        
    def _generate_date(self, field: DataField = None) -> str:
        """生成日期"""
        if not field:
            year = random.randint(2000, 2023)
            month = random.randint(1, 12)
            day = random.randint(1, 28)  # 简化处理，不处理月份天数差异
            return f"{year}-{month:02d}-{day:02d}"
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return str(field.default_value)
            
        # 根据字段名生成特定范围的日期
        field_name = field.name.lower()
        
        if 'birth' in field_name:
            year = random.randint(1970, 2005)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            return f"{year}-{month:02d}-{day:02d}"
        elif 'create' in field_name:
            year = random.randint(2020, 2023)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            return f"{year}-{month:02d}-{day:02d}"
        elif 'expire' in field_name or 'end' in field_name:
            year = random.randint(2023, 2025)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            return f"{year}-{month:02d}-{day:02d}"
            
        # 生成随机日期
        year = random.randint(2000, 2023)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"
        
    def _generate_datetime(self, field: DataField = None) -> str:
        """生成日期时间"""
        if not field:
            year = random.randint(2000, 2023)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            return f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return str(field.default_value)
            
        # 生成随机日期时间
        year = random.randint(2000, 2023)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        
    def _generate_email(self, field: DataField = None) -> str:
        """生成邮箱"""
        if not field:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            domain = random.choice(['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com'])
            return f"{username}@{domain}"
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return str(field.default_value)
            
        # 生成随机邮箱
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        domain = random.choice(['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com'])
        return f"{username}@{domain}"
        
    def _generate_phone(self, field: DataField = None) -> str:
        """生成手机号"""
        if not field:
            return f"1{random.choice(['3', '4', '5', '6', '7', '8', '9'])}{random.choices(string.digits, k=9)}"
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return str(field.default_value)
            
        # 生成随机手机号
        return f"1{random.choice(['3', '4', '5', '6', '7', '8', '9'])}{random.choices(string.digits, k=9)}"
        
    def _generate_uuid(self, field: DataField = None) -> str:
        """生成UUID"""
        if not field:
            return str(uuid.uuid4())
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return str(field.default_value)
            
        # 生成随机UUID
        return str(uuid.uuid4())
        
    def _generate_json(self, field: DataField = None) -> Dict:
        """生成JSON"""
        if not field:
            return {"key": "value", "number": 123}
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return field.default_value
            
        # 生成随机JSON
        return {"key": ''.join(random.choices(string.ascii_letters, k=5)), "number": random.randint(1, 100)}
        
    def _generate_array(self, field: DataField = None) -> List:
        """生成数组"""
        if not field:
            return [1, 2, 3]
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return field.default_value
            
        # 生成随机数组
        length = random.randint(1, 5)
        return [random.randint(1, 100) for _ in range(length)]
        
    def _generate_object(self, field: DataField = None) -> Dict:
        """生成对象"""
        if not field:
            return {"key": "value"}
            
        # 如果有枚举值，从枚举值中随机选择
        if field.enum_values:
            return random.choice(field.enum_values)
            
        # 如果有默认值，使用默认值
        if field.default_value is not None:
            return field.default_value
            
        # 生成随机对象
        return {"key": ''.join(random.choices(string.ascii_letters, k=5))}
        
    def _generate_password(self, length: int = 10) -> str:
        """生成密码"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choices(chars, k=length))
        
    def _generate_name(self) -> str:
        """生成姓名"""
        first_names = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
        last_names = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军"]
        return random.choice(first_names) + random.choice(last_names)
        
    def _generate_address(self) -> str:
        """生成地址"""
        provinces = ["北京市", "上海市", "广东省", "浙江省", "江苏省", "山东省", "河南省", "四川省"]
        cities = ["北京市", "上海市", "广州市", "深圳市", "杭州市", "南京市", "济南市", "郑州市", "成都市"]
        streets = ["中山路", "解放路", "人民路", "建设路", "文化路", "青年路", "新华路", "和平路"]
        return f"{random.choice(provinces)}{random.choice(cities)}{random.choice(streets)}{random.randint(1, 100)}号"
        
    def _generate_by_pattern(self, pattern: str, length: int) -> str:
        """根据模式生成字符串"""
        # 简化实现，实际应该解析正则表达式
        if pattern.startswith('^') and pattern.endswith('$'):
            pattern = pattern[1:-1]
            
        # 如果模式是简单的字符集
        if pattern.startswith('[') and ']' in pattern:
            char_set = pattern[pattern.find('[')+1:pattern.find(']')]
            return ''.join(random.choices(char_set, k=length))
            
        # 默认生成随机字符串
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class DataPreparation:
    """数据准备器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化数据准备器
        :param config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.generator = DataGenerator()
        self.data_entities = {}
        self.data_records = {}
        self.request_control = None
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        default_config = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "password",
                "database": "test_db"
            },
            "api": {
                "base_url": "http://localhost:8080/api",
                "headers": {
                    "Content-Type": "application/json"
                }
            },
            "data": {
                "cleanup_after_test": True,
                "temp_data_ttl": 3600  # 临时数据生存时间（秒）
            }
        }
        
        if not config_path or not os.path.exists(config_path):
            return default_config
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 合并默认配置
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
                elif isinstance(default_config[key], dict):
                    for sub_key in default_config[key]:
                        if sub_key not in config[key]:
                            config[key][sub_key] = default_config[key][sub_key]
                            
            return config
            
        except Exception as e:
            ERROR.logger.error(f"加载配置文件失败: {str(e)}")
            return default_config
            
    def register_entity(self, entity: DataEntity) -> None:
        """
        注册数据实体
        :param entity: 数据实体
        """
        try:
            self.data_entities[entity.name] = entity
            INFO.logger.info(f"注册数据实体: {entity.name}")
            
        except Exception as e:
            ERROR.logger.error(f"注册数据实体失败: {str(e)}")
            raise DataPreparationError(f"注册数据实体失败: {str(e)}")
            
    def generate_record(self, entity_name: str, custom_data: Dict = None) -> DataRecord:
        """
        生成数据记录
        :param entity_name: 实体名称
        :param custom_data: 自定义数据
        :return: 数据记录
        """
        try:
            if entity_name not in self.data_entities:
                raise ValueError(f"未找到数据实体: {entity_name}")
                
            entity = self.data_entities[entity_name]
            data = {}
            
            # 生成字段数据
            for field in entity.fields:
                # 如果有自定义数据，使用自定义数据
                if custom_data and field.name in custom_data:
                    data[field.name] = custom_data[field.name]
                # 否则生成数据
                else:
                    data[field.name] = self.generator.generate_data(field.data_type, field)
                    
            # 创建数据记录
            record = DataRecord(
                entity_name=entity_name,
                data=data,
                record_id=str(uuid.uuid4()),
                created_at=datetime.now(),
                is_temporary=True
            )
            
            # 存储记录
            if entity_name not in self.data_records:
                self.data_records[entity_name] = []
            self.data_records[entity_name].append(record)
            
            INFO.logger.info(f"生成数据记录: {entity_name} - {record.record_id}")
            return record
            
        except Exception as e:
            ERROR.logger.error(f"生成数据记录失败: {str(e)}")
            raise DataPreparationError(f"生成数据记录失败: {str(e)}")
            
    def prepare_test_data(self, test_scenario: Dict) -> Dict[str, DataRecord]:
        """
        准备测试数据
        :param test_scenario: 测试场景
        :return: 数据记录字典
        """
        try:
            records = {}
            
            # 按依赖关系排序实体
            sorted_entities = self._sort_entities_by_dependency(test_scenario)
            
            # 为每个实体生成数据
            for entity_name in sorted_entities:
                entity_config = test_scenario.get(entity_name, {})
                count = entity_config.get('count', 1)
                custom_data = entity_config.get('data', {})
                
                entity_records = []
                for i in range(count):
                    # 为每条记录生成唯一自定义数据
                    record_custom_data = {}
                    for key, value in custom_data.items():
                        if callable(value):
                            record_custom_data[key] = value(i)
                        else:
                            record_custom_data[key] = value
                            
                    # 生成记录
                    record = self.generate_record(entity_name, record_custom_data)
                    entity_records.append(record)
                    
                records[entity_name] = entity_records
                
            INFO.logger.info(f"准备测试数据完成，共生成 {len(records)} 种实体数据")
            return records
            
        except Exception as e:
            ERROR.logger.error(f"准备测试数据失败: {str(e)}")
            raise DataPreparationError(f"准备测试数据失败: {str(e)}")
            
    def _sort_entities_by_dependency(self, test_scenario: Dict) -> List[str]:
        """根据依赖关系对实体进行排序"""
        entities = list(test_scenario.keys())
        sorted_entities = []
        
        # 简化实现，实际应该使用拓扑排序
        while entities:
            # 找到没有依赖或依赖已满足的实体
            for entity in entities:
                entity_dependencies = self.data_entities.get(entity, DataEntity(entity)).dependencies
                
                # 检查依赖是否已满足
                dependencies_satisfied = True
                for dep in entity_dependencies:
                    if dep in entities and dep not in sorted_entities:
                        dependencies_satisfied = False
                        break
                        
                if dependencies_satisfied:
                    sorted_entities.append(entity)
                    entities.remove(entity)
                    break
            else:
                # 如果没有找到满足条件的实体，说明存在循环依赖
                ERROR.logger.warning("检测到循环依赖，按原始顺序处理")
                sorted_entities.extend(entities)
                break
                
        return sorted_entities
        
    def setup_data_via_api(self, records: Dict[str, DataRecord]) -> None:
        """
        通过API设置数据
        :param records: 数据记录字典
        """
        try:
            base_url = self.config['api']['base_url']
            headers = self.config['api']['headers']
            
            for entity_name, entity_records in records.items():
                entity = self.data_entities.get(entity_name)
                if not entity or not entity.table_name:
                    continue
                    
                # 构建API端点
                endpoint = f"{base_url}/{entity.table_name}"
                
                for record in entity_records:
                    # 发送请求创建数据
                    response = self.request_control.request_control(
                        method="POST",
                        url=endpoint,
                        headers=headers,
                        json_data=record.data
                    )
                    
                    # 检查响应
                    if response.status_code != 200 and response.status_code != 201:
                        ERROR.logger.error(f"通过API创建数据失败: {entity_name} - {response.text}")
                        continue
                        
                    # 更新记录ID
                    try:
                        response_data = response.json()
                        if 'data' in response_data and 'id' in response_data['data']:
                            record.data['id'] = response_data['data']['id']
                    except Exception:
                        pass
                        
            INFO.logger.info("通过API设置数据完成")
            
        except Exception as e:
            ERROR.logger.error(f"通过API设置数据失败: {str(e)}")
            raise DataPreparationError(f"通过API设置数据失败: {str(e)}")
            
    def setup_data_via_sql(self, records: Dict[str, DataRecord]) -> None:
        """
        通过SQL设置数据
        :param records: 数据记录字典
        """
        try:
            # 这里简化实现，实际应该使用数据库连接
            INFO.logger.info("通过SQL设置数据完成")
            
        except Exception as e:
            ERROR.logger.error(f"通过SQL设置数据失败: {str(e)}")
            raise DataPreparationError(f"通过SQL设置数据失败: {str(e)}")
            
    def cleanup_data(self, records: Dict[str, DataRecord] = None) -> None:
        """
        清理数据
        :param records: 数据记录字典，如果为None则清理所有数据
        """
        try:
            if not self.config['data']['cleanup_after_test']:
                INFO.logger.info("配置为不清理测试数据")
                return
                
            target_records = records or self.data_records
            
            for entity_name, entity_records in target_records.items():
                entity = self.data_entities.get(entity_name)
                if not entity:
                    continue
                    
                # 如果有自定义清理SQL，执行清理SQL
                if entity.cleanup_sql:
                    self._execute_cleanup_sql(entity.cleanup_sql)
                    continue
                    
                # 否则通过API清理数据
                if entity.table_name:
                    self._cleanup_data_via_api(entity, entity_records)
                    
            INFO.logger.info("清理测试数据完成")
            
        except Exception as e:
            ERROR.logger.error(f"清理测试数据失败: {str(e)}")
            raise DataPreparationError(f"清理测试数据失败: {str(e)}")
            
    def _execute_cleanup_sql(self, sql: str) -> None:
        """执行清理SQL"""
        # 简化实现，实际应该使用数据库连接
        pass
        
    def _cleanup_data_via_api(self, entity: DataEntity, records: List[DataRecord]) -> None:
        """通过API清理数据"""
        try:
            base_url = self.config['api']['base_url']
            headers = self.config['api']['headers']
            
            for record in records:
                # 如果记录有ID，通过ID删除
                if 'id' in record.data:
                    endpoint = f"{base_url}/{entity.table_name}/{record.data['id']}"
                    
                    # 发送请求删除数据
                    response = self.request_control.request_control(
                        method="DELETE",
                        url=endpoint,
                        headers=headers
                    )
                    
                    # 检查响应
                    if response.status_code != 200 and response.status_code != 204:
                        ERROR.logger.error(f"通过API删除数据失败: {entity.name} - {response.text}")
                        
        except Exception as e:
            ERROR.logger.error(f"通过API清理数据失败: {str(e)}")
            
    def get_data_record(self, entity_name: str, record_id: str = None) -> DataRecord:
        """
        获取数据记录
        :param entity_name: 实体名称
        :param record_id: 记录ID，如果为None则返回最新记录
        :return: 数据记录
        """
        if entity_name not in self.data_records or not self.data_records[entity_name]:
            raise ValueError(f"未找到实体 {entity_name} 的数据记录")
            
        if record_id:
            for record in self.data_records[entity_name]:
                if record.record_id == record_id:
                    return record
            raise ValueError(f"未找到记录ID为 {record_id} 的数据记录")
        else:
            # 返回最新记录
            return self.data_records[entity_name][-1]


def create_data_preparation(config_path: str = None) -> DataPreparation:
    """
    创建数据准备器
    :param config_path: 配置文件路径
    :return: 数据准备器
    """
    return DataPreparation(config_path)


if __name__ == '__main__':
    # 示例用法
    try:
        # 创建数据准备器
        data_prep = create_data_preparation()
        
        # 注册用户实体
        user_entity = DataEntity(
            name="user",
            table_name="users",
            fields=[
                DataField("username", DataType.STRING, True, 3, 20),
                DataField("email", DataType.EMAIL, True),
                DataField("password", DataType.STRING, True, 6, 20),
                DataField("age", DataType.INTEGER, False, 18, 65),
                DataField("is_active", DataType.BOOLEAN, False, default_value=True)
            ],
            description="用户实体"
        )
        data_prep.register_entity(user_entity)
        
        # 注册订单实体
        order_entity = DataEntity(
            name="order",
            table_name="orders",
            fields=[
                DataField("user_id", DataType.INTEGER, True),
                DataField("order_no", DataType.STRING, True),
                DataField("total_amount", DataType.FLOAT, False, min_value=0.0),
                DataField("status", DataType.STRING, True, enum_values=["pending", "paid", "shipped", "completed", "cancelled"])
            ],
            dependencies=["user"],
            description="订单实体"
        )
        data_prep.register_entity(order_entity)
        
        # 准备测试数据
        test_scenario = {
            "user": {
                "count": 2,
                "data": {
                    "username": lambda i: f"testuser{i}",
                    "email": lambda i: f"test{i}@example.com"
                }
            },
            "order": {
                "count": 3,
                "data": {
                    "user_id": lambda i: data_prep.get_data_record("user").data.get("id", i + 1),
                    "order_no": lambda i: f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{i:03d}"
                }
            }
        }
        
        records = data_prep.prepare_test_data(test_scenario)
        
        # 输出生成的数据
        for entity_name, entity_records in records.items():
            print(f"\n{entity_name} 实体数据:")
            for record in entity_records:
                print(f"  {record.record_id}: {record.data}")
                
    except Exception as e:
        print(f"数据准备失败: {str(e)}")