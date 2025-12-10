
# 消息API请求参数要求

本节汇总了飞书消息服务中发送API请求的关键参数要求，包括创建、回复和更新消息的相关参数。

## 1. 创建消息 (create)

### 请求URL
```
POST /im/v1/messages
```

### 请求头参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| Authorization | string | 是 | 身份认证凭证，格式为 "Bearer {token}" |
| Content-Type | string | 是 | 内容类型，固定为 "application/json; charset=utf-8" |

### 请求体参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| receive_id | string | 是 | 接收者ID，根据receive_id_type的值而定 |
| receive_id_type | string | 是 | 接收者ID类型，可选值：open_id、user_id、union_id、chat_id |
| msg_type | string | 是 | 消息类型，如text、post、image、interactive等 |
| content | string | 是 | 消息内容，JSON字符串格式 |
| uuid | string | 否 | 消息唯一标识，用于幂等性校验 |
| reply_message_id | string | 否 | 用于回复消息的ID |

### 请求示例
```json
{
  "receive_id": "oc_xxx",
  "receive_id_type": "chat_id",
  "msg_type": "text",
  "content": "{"text":"这是一条测试消息"}"
}
```

## 2. 回复消息 (reply)

### 请求URL
```
POST /im/v1/messages/{message_id}/reply
```

### URL路径参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| message_id | string | 是 | 要回复的消息ID |

### 请求头参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| Authorization | string | 是 | 身份认证凭证，格式为 "Bearer {token}" |
| Content-Type | string | 是 | 内容类型，固定为 "application/json; charset=utf-8" |

### 请求体参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| msg_type | string | 是 | 消息类型，如text、post、image、interactive等 |
| content | string | 是 | 消息内容，JSON字符串格式 |
| uuid | string | 否 | 消息唯一标识，用于幂等性校验 |

### 请求示例
```json
{
  "msg_type": "text",
  "content": "{"text":"这是一条回复消息"}",
  "uuid": "test-uuid-123"
}
```

## 3. 更新消息 (update)

### 请求URL
```
PUT /im/v1/messages/{message_id}
```

### URL路径参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| message_id | string | 是 | 要更新的消息ID |

### 请求头参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| Authorization | string | 是 | 身份认证凭证，格式为 "Bearer {token}" |
| Content-Type | string | 是 | 内容类型，固定为 "application/json; charset=utf-8" |

### 请求体参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| content | string | 是 | 更新后的消息内容，JSON字符串格式 |
| msg_type | string | 否 | 消息类型，更新时必须与原消息类型一致 |

### 请求示例
```json
{
  "content": "{"text":"这是更新后的消息内容"}",
  "msg_type": "text"
}
```

## 4. 通用参数说明

### 身份验证
所有API请求都需要在请求头中包含有效的访问令牌，格式为：
```
Authorization: Bearer {access_token}
```

### 内容编码
- 消息内容（content字段）必须是经过JSON序列化的字符串
- 字符串中的特殊字符需要进行转义
- 确保内容编码为UTF-8

### 消息ID类型说明
- **open_id**：用户的开放ID，全局唯一
- **user_id**：用户在企业内的唯一标识
- **union_id**：用户的统一ID，跨应用唯一
- **chat_id**：群聊的唯一标识

## 5. 响应参数说明

### 成功响应
大多数成功的请求会返回以下结构：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "message_id": "om_xxx",
    "root_id": "om_root_xxx",  // 仅在回复消息时返回
    "parent_id": "om_parent_xxx",  // 仅在回复消息时返回
    "uuid": "test-uuid-123"  // 如果请求中提供了uuid
  }
}
```

### 错误响应
错误响应通常包含以下字段：
```json
{
  "code": 错误码,
  "msg": "错误描述",
  "data": {}
}
```

## 6. API调用最佳实践

1. **使用UUID确保幂等性**：发送重要消息时，提供uuid参数避免重复发送
2. **错误处理与重试**：捕获并处理常见错误码，实现合理的重试机制
3. **请求频率控制**：遵守飞书API的调用频率限制，避免触发限流
4. **消息内容检查**：发送前验证消息内容格式，确保符合飞书要求
5. **权限检查**：确保应用拥有足够的权限发送相应类型的消息
6. **日志记录**：记录关键API调用信息，便于问题排查
    