"""Memory Agent - 独立的记忆管理Agent"""

from typing import Dict, Any, Optional, List
from tools.registry import tool_registry
from core.llm import LLMService
import logging
import json

logger = logging.getLogger(__name__)


class MemoryAgent:
    """独立的记忆管理 Agent - 主动管理记忆生命周期"""

    # 压缩配置
    COMPRESS_THRESHOLD = 10  # 超过10轮触发压缩
    KEEP_RECENT = 5          # 保留最近5轮完整对话

    def __init__(self):
        self.llm_service = LLMService()

    def load_memory(self, state) -> str:
        """加载记忆上下文（会话记忆 + 用户画像）"""
        context_parts = []

        # 1. 加载会话记忆
        if state.conversation_id and tool_registry.has_tool("conversation_memory_read"):
            try:
                history = tool_registry.invoke_tool(
                    "conversation_memory_read",
                    {
                        "conversation_id": state.conversation_id,
                        "limit": 10
                    },
                    run_id=state.run_id
                )
                messages = history.get("messages", [])
                if messages:
                    formatted = self._format_history(messages)
                    context_parts.append(formatted)
                    logger.info(f"[{state.run_id}] MemoryAgent loaded {len(messages)} messages"
                                f" (compressed: {history.get('compressed', False)})")
            except Exception as e:
                logger.warning(f"[{state.run_id}] MemoryAgent failed to load conversation: {e}")

        # 2. 加载用户画像（如果有 user_id）
        if state.user_id:
            user_profile = self._load_user_profile(state.user_id)
            if user_profile:
                context_parts.append(f"[用户画像] {json.dumps(user_profile, ensure_ascii=False)}")

        return "\n\n".join(context_parts) if context_parts else ""

    def save_memory(self, state, question: str, answer: str):
        """保存记忆（用户问题 + AI回答 + 提取偏好）"""
        if not state.conversation_id:
            return

        # 1. 写入用户问题
        if tool_registry.has_tool("conversation_memory_write"):
            try:
                tool_registry.invoke_tool(
                    "conversation_memory_write",
                    {
                        "conversation_id": state.conversation_id,
                        "role": "user",
                        "content": question
                    },
                    run_id=state.run_id
                )
            except Exception as e:
                logger.warning(f"[{state.run_id}] MemoryAgent failed to write user message: {e}")

        # 2. 写入 AI 回答
        if tool_registry.has_tool("conversation_memory_write"):
            try:
                tool_registry.invoke_tool(
                    "conversation_memory_write",
                    {
                        "conversation_id": state.conversation_id,
                        "role": "assistant",
                        "content": answer
                    },
                    run_id=state.run_id
                )
            except Exception as e:
                logger.warning(f"[{state.run_id}] MemoryAgent failed to write assistant message: {e}")

        # 3. 异步提取用户偏好（不阻塞主流程）
        if state.user_id:
            self._extract_user_preference(state, question, answer)

    def _load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """加载用户画像"""
        try:
            from core.mysql_client import user_memory_client
            return user_memory_client.get_user_memory(user_id)
        except Exception as e:
            logger.warning(f"Failed to load user profile: {e}")
            return None

    def _extract_user_preference(self, state, question: str, answer: str):
        """异步提取用户偏好"""
        try:
            from core.mysql_client import user_memory_client

            prompt = f"""分析以下问答，判断用户是否有明显的偏好特征。

用户问题：{question}
AI回答：{answer}

如果有，返回 JSON：{{"preference_style": "简洁/详细", "topics": ["主题1"]}}
如果没有明显偏好，返回：null
只返回 JSON 或 null，不要解释。"""

            result = self.llm_service.chat(prompt)
            if result and result.strip() != "null":
                # 清理 markdown 代码块
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                    cleaned = cleaned.rsplit("```", 1)[0]

                preference = json.loads(cleaned.strip())
                user_memory_client.update_user_memory(
                    state.user_id, "preference_style", preference,
                    source="agent", confidence=0.8
                )
                logger.info(f"[{state.run_id}] Extracted user preference: {preference}")
        except Exception as e:
            logger.debug(f"[{state.run_id}] Extract user preference failed: {e}")  # 静默失败

    def _format_history(self, messages: list) -> str:
        """格式化对话历史"""
        if not messages:
            return ""

        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                formatted.append(content)
            elif role == "user":
                formatted.append(f"用户: {content}")
            elif role == "assistant":
                formatted.append(f"AI: {content}")
            else:
                formatted.append(content)

        return "\n".join(formatted)
