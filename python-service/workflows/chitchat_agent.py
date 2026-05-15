from typing import Dict, Any, Optional, Generator
from core.llm import llm
from tools.registry import tool_registry
import logging
import json

logger = logging.getLogger(__name__)


class ChitChatAgent:
    """闲聊Agent - 专门处理日常对话和闲聊的工作流"""

    def __init__(self):
        self.chitchat_prompts = {
            "greeting": [
                "你好！很高兴见到你，有什么我可以帮助你的吗？",
                "您好！今天过得怎么样？有什么想聊的吗？",
                "Hi！有什么可以为你效劳的？",
            ],
            "thanks": [
                "不客气！能帮到你我很开心！",
                "不用谢，这是我应该做的！",
                "不客气，随时为你服务！",
            ],
            "identity": [
                "我是你的AI知识助手，可以帮你回答问题、查阅资料，也可以陪你聊聊天。你想了解什么？",
                "我是AI知识库助手，专注于知识问答，同时也可以陪你聊聊日常。",
            ],
            "weather": [
                "很抱歉，我无法实时获取天气信息。不过你可以查看天气预报APP来了解天气情况。",
            ],
            "time": [
                f"很抱歉，我无法告诉你当前时间，请查看你的设备时钟。",
            ],
            "joke": [
                "程序员最讨厌的季节是什么？是秋天！因为秋高气爽（bug少），但也会有很多落叶（bug）！",
                "你知道为什么程序员总是分不清万圣节和圣诞节吗？因为Oct 31 = Dec 25！",
                "为什么程序员喜欢黑暗模式？因为 Light attracts bugs！",
            ],
            "default": [
                "哈哈，这个话题挺有意思的！你最近有什么新鲜事想分享吗？",
                "嗯嗯，我听着呢～还有什么想聊的吗？",
                "有意思！能跟我说说更多吗？",
            ]
        }

    def chat(self, question: str, conversation_id: Optional[str] = None,
             user_id: Optional[str] = None, context: str = "",
             **kwargs) -> Dict[str, Any]:
        """
        处理闲聊

        Args:
            question: 用户问题
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            **kwargs: 其他参数

        Returns:
            包含answer的字典
        """
        logger.info(f"[ChitChatAgent] Processing chitchat: {question[:50]}...")

        try:
            # 1. 读取会话记忆作为上下文
            conversation_history = ""
            if conversation_id and tool_registry.has_tool("conversation_memory_read"):
                try:
                    history = tool_registry.invoke_tool(
                        "conversation_memory_read",
                        {
                            "conversation_id": conversation_id,
                            "limit": 10
                        }
                    )
                    messages = history.get("messages", [])
                    if messages:
                        conversation_history = self._format_history(messages)
                        logger.info(f"[ChitChatAgent] Loaded {len(messages)} messages from memory")
                except Exception as e:
                    logger.warning(f"[ChitChatAgent] Failed to read conversation memory: {e}")

            # 2. 生成回复（带会话上下文）
            answer = self._generate_chitchat_response(question, conversation_history)

            # 3. 写入会话记忆
            self._save_to_memory(conversation_id, question, answer)

            return {
                "answer": answer,
                "sources": [],
                "has_sources": False,
                "task_type": "chitchat"
            }
        except Exception as e:
            logger.error(f"[ChitChatAgent] Error: {str(e)}")
            return {
                "answer": "抱歉，我现在状态不太好，稍后再聊吧。",
                "sources": [],
                "has_sources": False,
                "task_type": "chitchat",
                "error": True
            }

    def _format_history(self, messages: list) -> str:
        """格式化对话历史为上下文字符串"""
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

        return "\n".join(formatted)

    def _save_to_memory(self, conversation_id: str, question: str, answer: str):
        """保存对话到会话记忆"""
        if not conversation_id or not tool_registry.has_tool("conversation_memory_write"):
            return
        try:
            tool_registry.invoke_tool(
                "conversation_memory_write",
                {"conversation_id": conversation_id, "role": "user", "content": question}
            )
            tool_registry.invoke_tool(
                "conversation_memory_write",
                {"conversation_id": conversation_id, "role": "assistant", "content": answer}
            )
            logger.info(f"[ChitChatAgent] Saved conversation to memory")
        except Exception as e:
            logger.warning(f"[ChitChatAgent] Failed to write conversation memory: {e}")

    def chat_stream(self, question: str, conversation_id: Optional[str] = None,
                    user_id: Optional[str] = None, context: str = "",
                    **kwargs) -> Generator[str, None, None]:
        """
        流式处理闲聊

        Args:
            question: 用户问题
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            **kwargs: 其他参数

        Yields:
            JSON格式的事件流
        """
        logger.info(f"[ChitChatAgent] Stream chitchat: {question[:50]}...")

        try:
            answer = self._generate_chitchat_response(question)

            for char in answer:
                yield json.dumps({
                    "type": "token",
                    "content": char
                })

            yield json.dumps({
                "type": "end",
                "content": {
                    "answer": answer,
                    "sources": [],
                    "task_type": "chitchat"
                }
            })
        except Exception as e:
            logger.error(f"[ChitChatAgent] Stream error: {str(e)}")
            yield json.dumps({
                "type": "error",
                "content": str(e)
            })

    def _generate_chitchat_response(self, question: str, conversation_history: str = "") -> str:
        """
        生成闲聊回复

        简单场景走规则匹配（<1ms），需要理解能力的场景调LLM生成自然回复
        """
        lower_question = question.lower()

        # 问候类 — 简短直接，不需要LLM
        if any(kw in lower_question for kw in ["你好", "您好", "hello", "hi", "早上好", "下午好", "晚上好", "嗨", "嘿"]):
            return self.chitchat_prompts["greeting"][0]

        # 感谢类 — 简短直接，不需要LLM
        if any(kw in lower_question for kw in ["谢谢", "感谢", "多谢", "thanks", "thank you"]):
            return self.chitchat_prompts["thanks"][0]

        # 身份询问类 — 简短直接，不需要LLM
        if any(kw in lower_question for kw in ["你叫什么", "你是谁", "你是什么", "你的名字", "你是机器人", "你是AI"]):
            return self.chitchat_prompts["identity"][0]

        # 以下场景需要理解能力，调LLM生成自然回复

        # "你知道X吗" 类 — 用LLM给出有内容的回复，而不是机械重定向
        if any(kw in lower_question for kw in ["你知道", "你了解", "你认识", "听说过", "你听过"]):
            return self._llm_chitchat(question, conversation_history)

        # 天气类 — 用LLM给出更自然的回复
        if any(kw in lower_question for kw in ["天气", "下雨", "晴天", "温度"]):
            return self._llm_chitchat(question, conversation_history)

        # 时间类
        if any(kw in lower_question for kw in ["几点", "时间", "日期", "今天是"]):
            return self.chitchat_prompts["time"][0]

        # 笑话类 — 用LLM讲笑话，比预设的更有趣
        if any(kw in lower_question for kw in ["笑话", "讲个笑话", "笑", "搞笑"]):
            return self._llm_chitchat(question, conversation_history)

        # 日常闲聊类 — 用LLM自然回复
        if any(kw in lower_question for kw in ["在干嘛", "在做什么", "忙吗", "累不累", "无聊", "睡不着"]):
            return self._llm_chitchat(question, conversation_history)

        # 引导类 — 用LLM自然回复
        if any(kw in lower_question for kw in ["聊聊", "聊天", "陪我", "有空吗", "最近怎么样", "最近好吗"]):
            return self._llm_chitchat(question, conversation_history)

        # 情感类 — 用LLM给出有共情的回复
        if any(kw in lower_question for kw in ["开心", "高兴", "难过", "伤心", "郁闷", "烦", "累", "困", "饿"]):
            return self._llm_chitchat(question, conversation_history)

        # 确认/反问类
        if any(kw in lower_question for kw in ["可以吗", "行吗", "好吗", "对不对", "是不是", "会不会"]):
            return self._llm_chitchat(question, conversation_history)

        # 其他所有闲聊 — 调LLM生成自然回复
        return self._llm_chitchat(question, conversation_history)

    def _llm_chitchat(self, question: str, conversation_history: str = "") -> str:
        """调用LLM生成自然的闲聊回复"""
        try:
            # 构建上下文
            context_section = ""
            if conversation_history:
                context_section = f"""
对话历史：
{conversation_history}

请基于对话历史，理解上下文后回复用户。"""

            prompt = f"""你是一个友好、健谈的AI助手。请用自然、亲切的方式回复用户，就像朋友之间聊天一样。
回复要简短有趣，100字以内。不要说"你可以问我知识类问题"这种话。
{context_section}

用户说：{question}"""

            response = llm.generate(prompt, temperature=0.7, max_tokens=150)
            return response.strip()
        except:
            return self.chitchat_prompts["default"][0]
