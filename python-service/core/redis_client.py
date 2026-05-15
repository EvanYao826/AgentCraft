import redis
import json
import time
import logging
from core.config import config

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis 客户端，用于会话记忆存储"""

    def __init__(self):
        """初始化Redis连接池"""
        self.pool = redis.ConnectionPool(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
            db=config.REDIS_DB,
            decode_responses=True,
            max_connections=20
        )
        self.client = redis.Redis(connection_pool=self.pool)
        logger.info(f"Redis client initialized: {config.REDIS_HOST}:{config.REDIS_PORT}")

    def add_message(self, conversation_id: str, role: str, content: str):
        """追加消息到会话"""
        key = f"conversation:{conversation_id}:messages"
        message = json.dumps({
            "role": role,
            "content": content,
            "timestamp": time.time()
        }, ensure_ascii=False)
        self.client.rpush(key, message)
        self.client.expire(key, 86400)  # 24小时过期
        logger.debug(f"Added message to conversation {conversation_id}: {role}")

    def get_messages(self, conversation_id: str, limit: int = 10) -> list:
        """获取最近 N 条消息"""
        key = f"conversation:{conversation_id}:messages"
        messages = self.client.lrange(key, -limit, -1)
        return [json.loads(m) for m in messages]

    def get_all_messages(self, conversation_id: str) -> list:
        """获取所有消息"""
        key = f"conversation:{conversation_id}:messages"
        messages = self.client.lrange(key, 0, -1)
        return [json.loads(m) for m in messages]

    def get_message_count(self, conversation_id: str) -> int:
        """获取消息总数"""
        key = f"conversation:{conversation_id}:messages"
        return self.client.llen(key)

    def clear_conversation(self, conversation_id: str):
        """清空会话"""
        key = f"conversation:{conversation_id}:messages"
        summary_key = f"conversation:{conversation_id}:summary"
        self.client.delete(key)
        self.client.delete(summary_key)
        logger.info(f"Cleared conversation {conversation_id}")

    def get_summary(self, conversation_id: str) -> str:
        """获取会话摘要"""
        summary_key = f"conversation:{conversation_id}:summary"
        return self.client.get(summary_key)

    def set_summary(self, conversation_id: str, summary: str, expire: int = 3600):
        """设置会话摘要"""
        summary_key = f"conversation:{conversation_id}:summary"
        self.client.setex(summary_key, expire, summary)
        logger.debug(f"Set summary for conversation {conversation_id}")

# 创建全局实例
redis_client = RedisClient()
