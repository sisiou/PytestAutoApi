#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据飞书文档生成 MessageSend.json 文件

用于"发送消息"接口的 Swagger JSON 定义
"""

import json
from pathlib import Path


def generate_message_send_json():
    """生成 MessageSend.json 文件"""
    
    message_send_data = {
        "title": "发送消息",
        "description": "调用该接口向指定用户或者群聊发送消息。支持发送的消息类型包括文本、富文本、卡片、群名片、个人名片、图片、视频、音频、文件以及表情包等。",
        "request": {
            "url": "https://open.feishu.cn/open-apis/im/v1/messages",
            "method": "POST",
            "rate_limit": {
                "type": "special",
                "doc": "https://open.feishu.cn/document/ukTMukTMukTM/uUzN04SN3QjL1cDN"
            },
            "app_types": [
                "Custom App",
                "Store App"
            ],
            "permissions": {
                "required": [
                    "im:message",
                    "im:message:send_as_bot",
                    "im:message:send"
                ],
                "field_level": [
                    "contact:user.employee_id:readonly"
                ]
            },
            "headers": [
                {
                    "name": "Authorization",
                    "in": "header",
                    "required": True,
                    "type": "string",
                    "description": "tenant_access_token，格式为 \"Bearer access_token\"。",
                    "example": "Bearer t-7f1bcd13fc57d46bac21793a18e560"
                },
                {
                    "name": "Content-Type",
                    "in": "header",
                    "required": True,
                    "type": "string",
                    "description": "固定值：application/json; charset=utf-8",
                    "example": "application/json; charset=utf-8"
                }
            ]
        },
        "response": {
            "schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "int",
                        "description": "错误码，非 0 表示失败"
                    },
                    "msg": {
                        "type": "string",
                        "description": "错误描述"
                    },
                    "data": {
                        "$ref": "#/components/schemas/Message"
                    }
                }
            }
        },
        "paths": {
            "/open-apis/im/v1/messages": {
                "post": {
                    "summary": "发送消息",
                    "description": "调用该接口向指定用户或者群聊发送消息。支持发送的消息类型包括文本、富文本、卡片、群名片、个人名片、图片、视频、音频、文件以及表情包等。",
                    "tags": ["消息"],
                    "operationId": "sendMessage",
                    "parameters": [
                        {
                            "name": "receive_id_type",
                            "in": "query",
                            "required": True,
                            "description": "消息接收者 ID 类型。支持 open_id/union_id/user_id/email/chat_id",
                            "schema": {
                                "type": "string",
                                "enum": ["open_id", "union_id", "user_id", "email", "chat_id"],
                                "example": "open_id"
                            }
                        },
                        {
                            "name": "Authorization",
                            "in": "header",
                            "required": True,
                            "description": "tenant_access_token，格式为 \"Bearer access_token\"。",
                            "schema": {
                                "type": "string",
                                "example": "Bearer t-7f1bcd13fc57d46bac21793a18e560"
                            }
                        },
                        {
                            "name": "Content-Type",
                            "in": "header",
                            "required": True,
                            "description": "固定值：application/json; charset=utf-8",
                            "schema": {
                                "type": "string",
                                "example": "application/json; charset=utf-8"
                            }
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SendMessageRequest"
                                },
                                "example": {
                                    "receive_id": "ou_7d8a6e6df7621556ce0d21922b676706ccs",
                                    "msg_type": "text",
                                    "content": "{\"text\":\"test content\"}",
                                    "uuid": "a0d69e20-1dd1-458b-k525-dfeca4015204"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功响应或业务错误",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SendMessageResponse"
                                    },
                                    "example": {
                                        "code": 0,
                                        "msg": "success",
                                        "data": {
                                            "message_id": "om_dc13264520392913993dd051dba21dcf",
                                            "root_id": "om_40eb06e7b84dc71c03e009ad3c754195",
                                            "parent_id": "om_d4be107c616aed9c1da8ed8068570a9f",
                                            "thread_id": "omt_d4be107c616a",
                                            "msg_type": "text",
                                            "create_time": "1615380573411",
                                            "update_time": "1615380573411",
                                            "deleted": False,
                                            "updated": False,
                                            "chat_id": "oc_5ad11d72b830411d72b836c20",
                                            "sender": {
                                                "id": "cli_9f427eec54ae901b",
                                                "id_type": "app_id",
                                                "sender_type": "app",
                                                "tenant_key": "736588c9260f175e"
                                            },
                                            "body": {
                                                "content": "{\"text\":\"test content\"}"
                                            },
                                            "mentions": []
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "SendMessageRequest": {
                    "type": "object",
                    "required": ["receive_id", "msg_type", "content"],
                    "properties": {
                        "receive_id": {
                            "type": "string",
                            "description": "消息接收者的 ID，ID 类型与查询参数 receive_id_type 的取值一致。",
                            "example": "ou_7d8a6e6df7621556ce0d21922b676706ccs"
                        },
                        "msg_type": {
                            "type": "string",
                            "description": "消息类型。可选值：text/post/image/file/audio/media/sticker/interactive/share_chat/share_user/system",
                            "enum": ["text", "post", "image", "file", "audio", "media", "sticker", "interactive", "share_chat", "share_user", "system"],
                            "example": "text"
                        },
                        "content": {
                            "type": "string",
                            "description": "消息内容，JSON 结构序列化后的字符串。该参数的取值与 msg_type 对应。",
                            "example": "{\"text\":\"test content\"}"
                        },
                        "uuid": {
                            "type": "string",
                            "description": "自定义设置的唯一字符串序列，用于在发送消息时请求去重。持有相同 uuid 的请求，在 1 小时内至多成功发送一条消息。",
                            "maxLength": 50,
                            "example": "a0d69e20-1dd1-458b-k525-dfeca4015204"
                        }
                    }
                },
                "SendMessageResponse": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "integer",
                            "description": "错误码，非 0 表示失败",
                            "example": 0
                        },
                        "msg": {
                            "type": "string",
                            "description": "错误描述",
                            "example": "success"
                        },
                        "data": {
                            "$ref": "#/components/schemas/Message"
                        }
                    }
                },
                "Message": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "消息 ID。成功发送消息后，由系统生成的唯一 ID 标识。",
                            "example": "om_dc13264520392913993dd051dba21dcf"
                        },
                        "root_id": {
                            "type": "string",
                            "description": "根消息 ID，仅在回复消息场景会有返回值。",
                            "example": "om_40eb06e7b84dc71c03e009ad3c754195"
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "父消息 ID，仅在回复消息场景会有返回值。",
                            "example": "om_d4be107c616aed9c1da8ed8068570a9f"
                        },
                        "thread_id": {
                            "type": "string",
                            "description": "消息所属的话题 ID，仅在话题场景会有返回值。",
                            "example": "omt_d4be107c616a"
                        },
                        "msg_type": {
                            "type": "string",
                            "description": "消息类型。",
                            "example": "text"
                        },
                        "create_time": {
                            "type": "string",
                            "description": "消息生成的时间戳。单位：毫秒",
                            "example": "1615380573411"
                        },
                        "update_time": {
                            "type": "string",
                            "description": "消息更新的时间戳。单位：毫秒",
                            "example": "1615380573411"
                        },
                        "deleted": {
                            "type": "boolean",
                            "description": "消息是否被撤回。发送消息时只会返回 false。",
                            "example": False
                        },
                        "updated": {
                            "type": "boolean",
                            "description": "消息是否被更新。发送消息时只会返回 false。",
                            "example": False
                        },
                        "chat_id": {
                            "type": "string",
                            "description": "消息所属的群 ID。",
                            "example": "oc_5ad11d72b830411d72b836c20"
                        },
                        "sender": {
                            "$ref": "#/components/schemas/Sender"
                        },
                        "body": {
                            "$ref": "#/components/schemas/MessageBody"
                        },
                        "mentions": {
                            "type": "array",
                            "description": "发送的消息内，被 @ 的用户列表。",
                            "items": {
                                "$ref": "#/components/schemas/Mention"
                            }
                        },
                        "upper_message_id": {
                            "type": "string",
                            "description": "合并转发消息中，上一层级的消息 ID，仅在合并转发场景会有返回值。",
                            "example": "om_40eb06e7b84dc71c03e009ad3c754195"
                        }
                    }
                },
                "Sender": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "发送者的 ID。",
                            "example": "cli_9f427eec54ae901b"
                        },
                        "id_type": {
                            "type": "string",
                            "description": "发送者的 ID 类型。可能值：open_id、app_id",
                            "example": "app_id"
                        },
                        "sender_type": {
                            "type": "string",
                            "description": "发送者类型。可能值：user、app、anonymous、unknown",
                            "example": "app"
                        },
                        "tenant_key": {
                            "type": "string",
                            "description": "租户唯一标识。",
                            "example": "736588c9260f175e"
                        }
                    }
                },
                "MessageBody": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "消息内容，JSON 结构序列化后的字符串。",
                            "example": "{\"text\":\"test content\"}"
                        }
                    }
                },
                "Mention": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "被 @ 的用户序号。例如，第 3 个被 @ 到的成员，取值为 @_user_3。",
                            "example": "@_user_1"
                        },
                        "id": {
                            "type": "string",
                            "description": "被 @ 的用户的 open_id。",
                            "example": "ou_155184d1e73cbfb8973e5a9e698e74f2"
                        },
                        "id_type": {
                            "type": "string",
                            "description": "被 @ 的用户的 ID 类型，目前仅支持 open_id。",
                            "example": "open_id"
                        },
                        "name": {
                            "type": "string",
                            "description": "被 @ 的用户姓名。",
                            "example": "Tom"
                        },
                        "tenant_key": {
                            "type": "string",
                            "description": "租户唯一标识。",
                            "example": "736588c9260f175e"
                        }
                    }
                }
            }
        }
    }
    
    # 保存到文件
    output_path = Path("interfacetest/MessageSend.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(message_send_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ MessageSend.json 已生成: {output_path.resolve()}")
    return output_path


if __name__ == "__main__":
    generate_message_send_json()

