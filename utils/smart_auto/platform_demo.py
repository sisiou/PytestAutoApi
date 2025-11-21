"""
智能自动化平台示例

该示例展示如何使用智能自动化平台完成以下任务：
1. 解析API文档
2. 分析接口依赖关系
3. 自动生成测试用例
4. 评估测试覆盖度
5. 生成测试报告

示例包含3个典型接口场景：
1. 用户注册登录场景
2. 商品浏览购买场景
3. 订单管理场景
"""

import os
import sys
import json
import time
import datetime
import random
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# 添加模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from utils.smart_auto.api_parser import APIParser, APIEndpoint, SwaggerParser
from utils.smart_auto.dependency_analyzer import DependencyAnalyzer
from utils.smart_auto.test_generator import TestCaseGenerator, TestSuite
from utils.smart_auto.assertion_generator import AssertionGenerator
from utils.smart_auto.data_preparation import DataPreparation
from utils.smart_auto.report_analyzer import TestExecutor, ReportGenerator, TestStatus
from utils.smart_auto.coverage_scorer import CoverageScorer, APIScenario
from utils.smart_auto.suggestion_generator import TestSuggestionGenerator, SuggestionReporter


def create_sample_api_docs() -> Dict[str, Any]:
    """创建示例API文档"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "电商平台API",
            "version": "1.0.0",
            "description": "电商平台API文档"
        },
        "servers": [
            {"url": "https://api.example.com/v1", "description": "生产环境"}
        ],
        "paths": {
            "/api/auth/register": {
                "post": {
                    "summary": "用户注册",
                    "description": "新用户注册接口",
                    "tags": ["认证"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username", "password", "email"],
                                    "properties": {
                                        "username": {
                                            "type": "string",
                                            "description": "用户名",
                                            "minLength": 3,
                                            "maxLength": 20
                                        },
                                        "password": {
                                            "type": "string",
                                            "description": "密码",
                                            "minLength": 6,
                                            "maxLength": 20
                                        },
                                        "email": {
                                            "type": "string",
                                            "format": "email",
                                            "description": "邮箱"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "注册成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "user_id": {"type": "string"},
                                            "username": {"type": "string"},
                                            "email": {"type": "string"},
                                            "token": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "请求参数错误"
                        },
                        "409": {
                            "description": "用户名或邮箱已存在"
                        }
                    }
                }
            },
            "/api/auth/login": {
                "post": {
                    "summary": "用户登录",
                    "description": "用户登录接口",
                    "tags": ["认证"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username", "password"],
                                    "properties": {
                                        "username": {
                                            "type": "string",
                                            "description": "用户名或邮箱"
                                        },
                                        "password": {
                                            "type": "string",
                                            "description": "密码"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "登录成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "user_id": {"type": "string"},
                                            "username": {"type": "string"},
                                            "email": {"type": "string"},
                                            "token": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "用户名或密码错误"
                        }
                    }
                }
            },
            "/api/user/profile": {
                "get": {
                    "summary": "获取用户信息",
                    "description": "获取当前登录用户的详细信息",
                    "tags": ["用户"],
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "获取成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "user_id": {"type": "string"},
                                            "username": {"type": "string"},
                                            "email": {"type": "string"},
                                            "phone": {"type": "string"},
                                            "address": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "未授权"
                        }
                    }
                }
            },
            "/api/products": {
                "get": {
                    "summary": "获取商品列表",
                    "description": "获取商品列表，支持分页和筛选",
                    "tags": ["商品"],
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "description": "页码",
                            "schema": {"type": "integer", "default": 1}
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "每页数量",
                            "schema": {"type": "integer", "default": 10}
                        },
                        {
                            "name": "category",
                            "in": "query",
                            "description": "商品分类",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "获取成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "products": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "product_id": {"type": "string"},
                                                        "name": {"type": "string"},
                                                        "price": {"type": "number"},
                                                        "category": {"type": "string"},
                                                        "description": {"type": "string"}
                                                    }
                                                }
                                            },
                                            "pagination": {
                                                "type": "object",
                                                "properties": {
                                                    "page": {"type": "integer"},
                                                    "limit": {"type": "integer"},
                                                    "total": {"type": "integer"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/products/{product_id}": {
                "get": {
                    "summary": "获取商品详情",
                    "description": "根据商品ID获取商品详细信息",
                    "tags": ["商品"],
                    "parameters": [
                        {
                            "name": "product_id",
                            "in": "path",
                            "required": True,
                            "description": "商品ID",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "获取成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "product_id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "price": {"type": "number"},
                                            "category": {"type": "string"},
                                            "description": {"type": "string"},
                                            "images": {"type": "array", "items": {"type": "string"}},
                                            "stock": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "商品不存在"
                        }
                    }
                }
            },
            "/api/cart": {
                "get": {
                    "summary": "获取购物车",
                    "description": "获取当前用户的购物车内容",
                    "tags": ["购物车"],
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "获取成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "cart_id": {"type": "string"},
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "product_id": {"type": "string"},
                                                        "product_name": {"type": "string"},
                                                        "price": {"type": "number"},
                                                        "quantity": {"type": "integer"},
                                                        "subtotal": {"type": "number"}
                                                    }
                                                }
                                            },
                                            "total": {"type": "number"}
                                        }
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "未授权"
                        }
                    }
                },
                "post": {
                    "summary": "添加商品到购物车",
                    "description": "将商品添加到购物车",
                    "tags": ["购物车"],
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["product_id", "quantity"],
                                    "properties": {
                                        "product_id": {
                                            "type": "string",
                                            "description": "商品ID"
                                        },
                                        "quantity": {
                                            "type": "integer",
                                            "description": "数量",
                                            "minimum": 1
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "添加成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "cart_id": {"type": "string"},
                                            "message": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "请求参数错误"
                        },
                        "404": {
                            "description": "商品不存在"
                        }
                    }
                }
            },
            "/api/orders": {
                "get": {
                    "summary": "获取订单列表",
                    "description": "获取当前用户的订单列表",
                    "tags": ["订单"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "description": "订单状态",
                            "schema": {
                                "type": "string",
                                "enum": ["pending", "paid", "shipped", "delivered", "cancelled"]
                            }
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "description": "页码",
                            "schema": {"type": "integer", "default": 1}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "获取成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "orders": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "order_id": {"type": "string"},
                                                        "status": {"type": "string"},
                                                        "total_amount": {"type": "number"},
                                                        "created_at": {"type": "string", "format": "date-time"}
                                                    }
                                                }
                                            },
                                            "pagination": {
                                                "type": "object",
                                                "properties": {
                                                    "page": {"type": "integer"},
                                                    "limit": {"type": "integer"},
                                                    "total": {"type": "integer"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "未授权"
                        }
                    }
                },
                "post": {
                    "summary": "创建订单",
                    "description": "根据购物车内容创建订单",
                    "tags": ["订单"],
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["items"],
                                    "properties": {
                                        "items": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "product_id": {"type": "string"},
                                                    "quantity": {"type": "integer"},
                                                    "price": {"type": "number"}
                                                }
                                            }
                                        },
                                        "shipping_address": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "phone": {"type": "string"},
                                                "address": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "创建成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "order_id": {"type": "string"},
                                            "status": {"type": "string"},
                                            "total_amount": {"type": "number"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "请求参数错误"
                        }
                    }
                }
            },
            "/api/orders/{order_id}/cancel": {
                "post": {
                    "summary": "取消订单",
                    "description": "取消指定的订单",
                    "tags": ["订单"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "order_id",
                            "in": "path",
                            "required": True,
                            "description": "订单ID",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "取消成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "order_id": {"type": "string"},
                                            "status": {"type": "string"},
                                            "message": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "订单状态不允许取消"
                        },
                        "404": {
                            "description": "订单不存在"
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }


def create_sample_scenarios() -> List[APIScenario]:
    """创建示例场景"""
    return [
        APIScenario(
            scenario_id="user_auth_scenario",
            scenario_name="用户注册登录场景",
            description="用户注册、登录、获取个人信息的完整流程",
            api_endpoints=["/api/auth/register", "/api/auth/login", "/api/user/profile"],
            test_steps=[
                {
                    "step": 1,
                    "description": "用户注册",
                    "api": "/api/auth/register",
                    "method": "POST",
                    "function": "register",
                    "parameters": [
                        {"name": "username", "type": "string", "required": True},
                        {"name": "password", "type": "string", "required": True},
                        {"name": "email", "type": "string", "format": "email", "required": True}
                    ],
                    "exceptions": [
                        {"type": "invalid_username", "description": "用户名格式不正确"},
                        {"type": "invalid_password", "description": "密码格式不正确"},
                        {"type": "invalid_email", "description": "邮箱格式不正确"},
                        {"type": "duplicate_user", "description": "用户名或邮箱已存在"}
                    ]
                },
                {
                    "step": 2,
                    "description": "用户登录",
                    "api": "/api/auth/login",
                    "method": "POST",
                    "function": "login",
                    "parameters": [
                        {"name": "username", "type": "string", "required": True},
                        {"name": "password", "type": "string", "required": True}
                    ],
                    "exceptions": [
                        {"type": "invalid_credentials", "description": "用户名或密码错误"}
                    ]
                },
                {
                    "step": 3,
                    "description": "获取用户信息",
                    "api": "/api/user/profile",
                    "method": "GET",
                    "function": "get_profile",
                    "exceptions": [
                        {"type": "unauthorized", "description": "未授权访问"}
                    ]
                }
            ],
            tags=["authentication", "user"],
            priority="high",
            business_value="high"
        ),
        APIScenario(
            scenario_id="shopping_scenario",
            scenario_name="商品浏览购买场景",
            description="用户浏览商品、添加购物车、创建订单的完整流程",
            api_endpoints=["/api/products", "/api/products/{product_id}", "/api/cart", "/api/orders"],
            test_steps=[
                {
                    "step": 1,
                    "description": "获取商品列表",
                    "api": "/api/products",
                    "method": "GET",
                    "function": "browse_products",
                    "parameters": [
                        {"name": "page", "type": "integer", "default": 1},
                        {"name": "limit", "type": "integer", "default": 10},
                        {"name": "category", "type": "string"}
                    ]
                },
                {
                    "step": 2,
                    "description": "获取商品详情",
                    "api": "/api/products/{product_id}",
                    "method": "GET",
                    "function": "get_product_detail",
                    "parameters": [
                        {"name": "product_id", "type": "string", "required": True}
                    ],
                    "exceptions": [
                        {"type": "product_not_found", "description": "商品不存在"}
                    ]
                },
                {
                    "step": 3,
                    "description": "添加商品到购物车",
                    "api": "/api/cart",
                    "method": "POST",
                    "function": "add_to_cart",
                    "parameters": [
                        {"name": "product_id", "type": "string", "required": True},
                        {"name": "quantity", "type": "integer", "required": True, "minimum": 1}
                    ],
                    "exceptions": [
                        {"type": "product_not_found", "description": "商品不存在"},
                        {"type": "insufficient_stock", "description": "库存不足"}
                    ]
                },
                {
                    "step": 4,
                    "description": "创建订单",
                    "api": "/api/orders",
                    "method": "POST",
                    "function": "create_order",
                    "parameters": [
                        {"name": "items", "type": "array", "required": True},
                        {"name": "shipping_address", "type": "object"}
                    ],
                    "exceptions": [
                        {"type": "invalid_items", "description": "商品信息无效"},
                        {"type": "invalid_address", "description": "收货地址无效"}
                    ]
                }
            ],
            tags=["e-commerce", "shopping"],
            priority="high",
            business_value="high"
        ),
        APIScenario(
            scenario_id="order_management_scenario",
            scenario_name="订单管理场景",
            description="用户查看订单、取消订单的流程",
            api_endpoints=["/api/orders", "/api/orders/{order_id}/cancel"],
            test_steps=[
                {
                    "step": 1,
                    "description": "获取订单列表",
                    "api": "/api/orders",
                    "method": "GET",
                    "function": "view_orders",
                    "parameters": [
                        {"name": "status", "type": "string", "enum": ["pending", "paid", "shipped", "delivered", "cancelled"]},
                        {"name": "page", "type": "integer", "default": 1}
                    ]
                },
                {
                    "step": 2,
                    "description": "取消订单",
                    "api": "/api/orders/{order_id}/cancel",
                    "method": "POST",
                    "function": "cancel_order",
                    "parameters": [
                        {"name": "order_id", "type": "string", "required": True}
                    ],
                    "exceptions": [
                        {"type": "order_not_found", "description": "订单不存在"},
                        {"type": "invalid_status", "description": "订单状态不允许取消"}
                    ]
                }
            ],
            tags=["e-commerce", "order"],
            priority="medium",
            business_value="medium"
        )
    ]


def run_platform_demo():
    """运行智能自动化平台演示"""
    print("=" * 60)
    print("智能自动化平台演示")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("smart_auto_demo")
    output_dir.mkdir(exist_ok=True)
    
    # 1. 解析API文档
    print("\n1. 解析API文档...")
    api_docs = create_sample_api_docs()
    
    # 创建一个临时文件来存储API文档
    import tempfile
    import json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(api_docs, f)
        temp_file_path = f.name
    
    # 使用SwaggerParser解析API文档
    parser = SwaggerParser(temp_file_path)
    api_endpoints = parser.parse_apis()
    
    # 删除临时文件
    os.unlink(temp_file_path)
    
    print(f"解析完成，共发现 {len(api_endpoints)} 个API端点")
    for endpoint in api_endpoints[:3]:  # 只显示前3个
        print(f"  - {endpoint.method} {endpoint.path}: {endpoint.summary}")
    
    # 2. 分析接口依赖关系
    print("\n2. 分析接口依赖关系...")
    
    # 将APIEndpoint对象转换为字典格式，以适配DependencyAnalyzer
    apis_dict = []
    for endpoint in api_endpoints:
        api_dict = {
            'path': endpoint.path,
            'method': endpoint.method,
            'operationId': endpoint.operation_id,
            'parameters': endpoint.parameters,
            'request_body': endpoint.request_body,
            'success_response': endpoint.success_response,
            'tags': endpoint.tags,
            'summary': endpoint.summary
        }
        apis_dict.append(api_dict)
    
    dependency_analyzer = DependencyAnalyzer(apis_dict)
    dependency_analyzer.analyze_dependencies()
    dependencies = dependency_analyzer.data_dependencies
    business_flows = dependency_analyzer.business_flows
    
    print(f"发现 {len(dependencies)} 个依赖关系")
    print(f"识别出 {len(business_flows)} 个业务流程")
    
    # 3. 创建场景
    print("\n3. 创建测试场景...")
    scenarios = create_sample_scenarios()
    print(f"创建了 {len(scenarios)} 个测试场景")
    for scenario in scenarios:
        print(f"  - {scenario.scenario_name}: {scenario.description}")
    
    # 4. 自动生成测试用例
    print("\n4. 自动生成测试用例...")
    
    # 创建一个临时文件来存储API文档，使用OpenAPI格式
    import tempfile
    import json
    
    # 创建符合OpenAPI格式的文档结构
    openapi_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "智能自动化平台API文档",
            "version": "1.0.0",
            "description": "由智能自动化平台生成的API文档"
        },
        "servers": [
            {
                "url": "http://localhost:8080",
                "description": "本地服务器"
            }
        ],
        "paths": {}
    }
    
    # 将APIEndpoint对象转换为OpenAPI格式
    for endpoint in api_endpoints:
        path_item = {
            endpoint.method.lower(): {
                "summary": endpoint.summary,
                "description": endpoint.summary,
                "operationId": endpoint.operation_id,
                "tags": endpoint.tags,
                "parameters": endpoint.parameters,
                "requestBody": endpoint.request_body,
                "responses": {
                    "200": {
                        "description": "成功响应",
                        "content": {
                            "application/json": {
                                "schema": endpoint.success_response.get('schema', {}) if endpoint.success_response else {}
                            }
                        }
                    }
                }
            }
        }
        openapi_doc["paths"][endpoint.path] = path_item
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(openapi_doc, f)
        temp_file_path = f.name
    
    test_generator = TestCaseGenerator(temp_file_path)
    assertion_generator = AssertionGenerator()
    data_preparation = DataPreparation()
    
    # 生成测试用例
    all_test_suites = test_generator.generate_test_cases()
    
    # 删除临时文件
    os.unlink(temp_file_path)
    
    test_cases_by_scenario = {}
    
    # 为每个测试用例生成断言
    for test_suite in all_test_suites:
        for test_case in test_suite.test_cases:
            # 构建API信息字典，以符合AssertionGenerator的期望
            api_info = {
                'path': test_case.api_path,
                'method': test_case.api_method,
                'response_codes': [200],  # 默认成功状态码
                'success_response': test_case.assert_data.get('schema', {}) if test_case.assert_data else {}
            }
            
            test_case.assertions = assertion_generator.generate_assertions(
                api_info, test_case.data
            )
    
    # 准备测试数据
    test_data = data_preparation.prepare_test_data({})
    
    # 转换为覆盖度评分器需要的格式
    test_cases_data = []
    for test_suite in all_test_suites:
        for test_case in test_suite.test_cases:
            test_case_data = {
                "id": test_case.case_id,
                "name": test_case.case_name,
                "functions": [test_case.api_path],
                "parameters": [
                    {"name": k, "value": v} for k, v in test_case.data.items()
                ],
                "exceptions": [],
                "business_flow": test_suite.suite_name
            }
            test_cases_data.append(test_case_data)
    
    test_cases_by_scenario["all"] = test_cases_data
    
    print(f"生成了 {sum(len(suite.test_cases) for suite in all_test_suites)} 个测试用例")
    
    # 5. 评估测试覆盖度
    print("\n5. 评估测试覆盖度...")
    coverage_scorer = CoverageScorer()
    coverage_report = coverage_scorer.score_all_scenarios(scenarios, test_cases_by_scenario)
    
    print(f"总体覆盖度: {coverage_report.overall_coverage:.1f}% ({coverage_report.overall_level.value.upper()})")
    for coverage in coverage_report.test_coverages:
        print(f"  - {coverage.scenario_name}: {coverage.total_coverage:.1f}% ({coverage.coverage_level.value.upper()})")
    
    # 6. 生成测试报告
    print("\n6. 生成测试报告...")
    report_generator = ReportGenerator(str(output_dir / "reports"))
    
    # 创建测试执行器并模拟测试执行
    test_executor = TestExecutor()
    report_id = test_executor.start_report(
        "智能自动化平台演示报告",
        environment_info={
            "platform": "智能自动化平台",
            "version": "1.0.0",
            "python_version": "3.8.10"
        }
    )
    
    # 模拟执行测试用例
    for test_suite in all_test_suites:
        suite_name = test_suite.suite_name
        test_executor.start_suite(suite_name)
        
        for test_case in test_suite.test_cases:
            # 模拟测试执行
            start_time = datetime.datetime.now()
            # 模拟测试执行时间
            time.sleep(0.1)
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 随机生成测试结果（80%通过率）
            status = TestStatus.PASSED if random.random() < 0.8 else TestStatus.FAILED
            error_message = None if status == TestStatus.PASSED else "模拟的断言失败"
            
            test_executor.add_test_result(
                test_id=test_case.case_id,
                test_name=test_case.case_name,
                test_case_id=test_case.case_id,
                status=status,
                duration=duration,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                assertion_results=[
                    {
                        "assertion": str(assertion),
                        "passed": status == TestStatus.PASSED
                    } for assertion in test_case.assertions
                ],
                request_data=test_case.data,
                response_data={"status": "success"} if status == TestStatus.PASSED else {"status": "error"},
                tags=test_case.tags if hasattr(test_case, 'tags') else []
            )
        
        test_executor.end_suite()
    
    # 结束报告
    test_report = test_executor.end_report()
    
    # 生成HTML和JSON报告
    json_report = report_generator.generate_json_report(test_report)
    html_report = report_generator.generate_html_report(test_report)
    
    print(f"测试报告已生成:")
    print(f"  - JSON报告: {json_report}")
    print(f"  - HTML报告: {html_report}")
    
    # 7. 生成覆盖度报告
    print("\n7. 生成覆盖度报告...")
    from utils.smart_auto.coverage_scorer import CoverageReporter
    coverage_reporter = CoverageReporter(str(output_dir / "coverage"))
    
    # 设置报告生成时间
    coverage_report.generated_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    json_coverage = coverage_reporter.generate_json_report(coverage_report)
    html_coverage = coverage_reporter.generate_html_report(coverage_report)
    
    print(f"覆盖度报告已生成:")
    print(f"  - JSON报告: {json_coverage}")
    print(f"  - HTML报告: {html_coverage}")
    
    # 8. 生成智能建议报告
    print("\n8. 生成智能建议报告...")
    suggestion_generator = TestSuggestionGenerator(api_endpoints)
    suggestion_reporter = SuggestionReporter(str(output_dir / "suggestions"))
    
    # 生成智能建议
    suggestion_report = suggestion_generator.generate_suggestions(
        scenarios, coverage_report, api_endpoints, test_cases_data
    )
    
    # 生成建议报告
    json_suggestion = suggestion_reporter.generate_json_report(suggestion_report)
    html_suggestion = suggestion_reporter.generate_html_report(suggestion_report)
    
    print(f"智能建议报告已生成:")
    print(f"  - JSON报告: {json_suggestion}")
    print(f"  - HTML报告: {html_suggestion}")
    
    # 9. 生成测试用例文件
    print("\n9. 生成测试用例文件...")
    from utils.read_files_tools.testcase_template import write_testcase_file
    
    test_cases_dir = output_dir / "test_cases"
    test_cases_dir.mkdir(exist_ok=True)
    
    for test_suite in all_test_suites:
        test_file_path = test_cases_dir / f"test_{test_suite.suite_name.replace(' ', '_').lower()}.py"
        
        # 提取测试用例ID列表
        case_ids = [test_case.case_id for test_case in test_suite.test_cases]
        
        # 调用write_testcase_file，使用关键字参数
        write_testcase_file(
            allure_epic="智能自动化平台",
            allure_feature=test_suite.suite_name,
            class_title=test_suite.suite_name.replace(' ', '_').title(),
            func_title=test_suite.suite_name.replace(' ', '_').lower(),
            case_path=str(test_file_path),
            case_ids=case_ids,
            file_name=test_file_path.name,
            allure_story=test_suite.suite_name
        )
        print(f"  - {test_file_path}")
    
    print("\n" + "=" * 60)
    print("智能自动化平台演示完成!")
    print("=" * 60)
    print(f"所有输出文件已保存到: {output_dir.absolute()}")
    print("\n主要文件:")
    print(f"  - 测试报告: {html_report}")
    print(f"  - 覆盖度报告: {html_coverage}")
    print(f"  - 智能建议报告: {html_suggestion}")
    print(f"  - 测试用例: {test_cases_dir.absolute()}")
    
    return {
        "api_endpoints": len(api_endpoints),
        "scenarios": len(scenarios),
        "test_cases": sum(len(suite.test_cases) for suite in all_test_suites),
        "overall_coverage": coverage_report.overall_coverage,
        "test_report": html_report,
        "coverage_report": html_coverage,
        "suggestion_report": html_suggestion,
        "test_cases_dir": str(test_cases_dir.absolute())
    }


if __name__ == "__main__":
    # 运行演示
    result = run_platform_demo()
    
    print("\n演示结果摘要:")
    for key, value in result.items():
        if key not in ["test_report", "coverage_report", "test_cases_dir"]:
            print(f"  {key}: {value}")