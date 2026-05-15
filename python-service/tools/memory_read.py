from typing import Dict, Any, List
from tools.base import Tool, ToolSchema, SchemaProperty, ToolMetadata
from core.config import config
from core.redis_client import redis_client
from core.llm import LLMService

# 压缩阈值配置
COMPRESS_THRESHOLD = 10  # 超过10轮触发压缩
KEEP_RECENT = 5          # 保留最近5轮完整对话


class ConversationMemoryReadTool(Tool):
    """对话记忆读取工具（含上下文压缩）"""

    def __init__(self):
        input_schema = ToolSchema(
            properties={
                "conversation_id": SchemaProperty(
                    type="string",
                    description="对话ID",
                    required=True
                ),
                "limit": SchemaProperty(
                    type="number",
                    description="返回消息数量限制",
                    required=False,
                    default=10
                )
            },
            type="object"
        )

        output_schema = ToolSchema(
            properties={
                "messages": SchemaProperty(
                    type="array",
                    description="对话消息列表",
                    required=True
                ),
                "conversation_id": SchemaProperty(
                    type="string",
                    description="对话ID",
                    required=True
                ),
                "total_count": SchemaProperty(
                    type="number",
                    description="总消息数量",
                    required=True
                ),
                "compressed": SchemaProperty(
                    type="boolean",
                    description="是否已压缩",
                    required=False
                )
            },
            type="object"
        )

        metadata = ToolMetadata(
            timeout_ms=10000,  # 压缩可能需要更长时间
            max_retries=1,
            permission="user",
            description="读取对话记忆"
        )

        super().__init__(
            name="conversation_memory_read",
            description="读取对话记忆",
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata
        )

        self.llm_service = LLMService()

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行对话记忆读取（含上下文压缩）"""
        conversation_id = parameters.get("conversation_id")
        limit = int(parameters.get("limit", 10))

        config.logger.info(f"Reading conversation memory for ID: {conversation_id}")

        # 获取消息总数
        total_count = redis_client.get_message_count(conversation_id)

        if total_count == 0:
            # 没有消息，返回空列表
            return {
                "messages": [],
                "conversation_id": conversation_id,
                "total_count": 0,
                "compressed": False
            }

        if total_count <= COMPRESS_THRESHOLD:
            # 消息不多，直接返回最近的
            messages = redis_client.get_messages(conversation_id, limit)
            return {
                "messages": messages,
                "conversation_id": conversation_id,
                "total_count": total_count,
                "compressed": False
            }

        # 超过阈值，触发压缩
        # 保留最近 N 轮完整对话
        recent_messages = redis_client.get_messages(conversation_id, KEEP_RECENT)

        # 检查是否已有缓存的摘要
        cached_summary = redis_client.get_summary(conversation_id)

        if cached_summary:
            summary = cached_summary
            config.logger.info(f"Using cached summary for conversation {conversation_id}")
        else:
            # 获取早期消息用于压缩
            all_messages = redis_client.get_all_messages(conversation_id)
            early_messages = all_messages[:-KEEP_RECENT]
            summary = self._compress_history(early_messages, conversation_id)
            # 缓存摘要
            redis_client.set_summary(conversation_id, summary)
            config.logger.info(f"Compressed {len(early_messages)} messages into summary")

        # 返回：摘要 + 最近5轮
        return {
            "messages": [
                {"role": "system", "content": f"[历史对话摘要] {summary}"}
            ] + recent_messages,
            "conversation_id": conversation_id,
            "total_count": total_count,
            "compressed": True,
            "original_count": total_count
        }

    def _compress_history(self, messages: List[Dict], conversation_id: str) -> str:
        """用 LLM 压缩早期对话为摘要"""
        if not messages:
            return "无历史对话记录。"

        history_text = "\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
        ])

        prompt = f"""请将以下对话压缩成简短摘要，保留关键信息：
1. 用户问了什么问题
2. AI 回答了什么要点
3. 用户的偏好或关注点

对话内容：
{history_text}

请用 2-3 句话概括，不要遗漏重要信息。"""

        try:
            summary = self.llm_service.chat(prompt)
            return summary
        except Exception as e:
            config.logger.warning(f"Failed to compress history: {e}")
            # 压缩失败时，返回简化版本
            return f"用户进行了 {len(messages)} 轮对话，讨论了相关知识问题。"
