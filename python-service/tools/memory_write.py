from typing import Dict, Any
from tools.base import Tool, ToolSchema, SchemaProperty, ToolMetadata
from core.config import config
from core.redis_client import redis_client
import uuid


class ConversationMemoryWriteTool(Tool):
    """对话记忆写入工具（真实存储）"""

    def __init__(self):
        input_schema = ToolSchema(
            properties={
                "conversation_id": SchemaProperty(
                    type="string",
                    description="对话ID",
                    required=True
                ),
                "role": SchemaProperty(
                    type="string",
                    description="角色 (user 或 assistant)",
                    required=True
                ),
                "content": SchemaProperty(
                    type="string",
                    description="消息内容",
                    required=True
                )
            },
            type="object"
        )

        output_schema = ToolSchema(
            properties={
                "success": SchemaProperty(
                    type="boolean",
                    description="是否成功",
                    required=True
                ),
                "message_id": SchemaProperty(
                    type="string",
                    description="消息ID",
                    required=True
                ),
                "conversation_id": SchemaProperty(
                    type="string",
                    description="对话ID",
                    required=True
                )
            },
            type="object"
        )

        metadata = ToolMetadata(
            timeout_ms=5000,
            max_retries=1,
            permission="user",
            description="写入对话记忆"
        )

        super().__init__(
            name="conversation_memory_write",
            description="写入对话记忆",
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata
        )

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行对话记忆写入（真实存储到Redis）"""
        conversation_id = parameters.get("conversation_id")
        role = parameters.get("role")
        content = parameters.get("content")

        # 验证角色
        if role not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {role}, must be 'user' or 'assistant'")

        # 生成消息ID
        message_id = str(uuid.uuid4())

        config.logger.info(f"Writing message to conversation {conversation_id}: role={role}")

        # 写入Redis
        redis_client.add_message(conversation_id, role, content)

        # 如果对话轮数超过阈值，清除旧摘要（让它在下次读取时重新生成）
        message_count = redis_client.get_message_count(conversation_id)
        if message_count > 10:
            summary = redis_client.get_summary(conversation_id)
            if summary:
                redis_client.client.delete(f"conversation:{conversation_id}:summary")
                config.logger.info(f"Cleared stale summary for conversation {conversation_id}")

        return {
            "success": True,
            "message_id": message_id,
            "conversation_id": conversation_id
        }
