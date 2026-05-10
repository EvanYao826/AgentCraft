from typing import Dict, Any, Optional, Generator
from enum import Enum
from workflows.knowledge_qa_agent import KnowledgeQAAgent
from workflows.chitchat_agent import ChitChatAgent
from workflows.admin_copilot_agent import AdminCopilotAgent
from workflows.inspection_agent import InspectionAgent
from workflows.retrieval_agent import RetrievalAgent
from agent.planner import IntentType
import logging
import json
import re

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举"""
    CHITCHAT = "chitchat"
    KNOWLEDGE_QA = "knowledge_qa"
    ADMIN_COPILOT = "admin_copilot"
    KNOWLEDGE_INSPECTION = "knowledge_inspection"
    UNKNOWN = "unknown"


class RouterAgent:
    """路由Agent - 负责将用户请求路由到合适的工作流"""

    def __init__(self):
        self.knowledge_qa_agent = KnowledgeQAAgent()
        self.chitchat_agent = ChitChatAgent()
        self.admin_copilot_agent = AdminCopilotAgent()
        self.inspection_agent = InspectionAgent()
        self.retrieval_agent = RetrievalAgent()

        # 闲聊关键词库（只包含明确的闲聊词汇）
        self.chitchat_keywords = [
            # 问候类
            "你好", "您好", "hello", "hi", "早上好", "下午好", "晚上好", "嗨", "嘿",
            # 告别类
            "谢谢", "感谢", "多谢", "再见", "拜拜", "拜拜咯", "下次见",
            # 身份询问类（针对系统）
            "你叫什么", "你是谁", "你是什么", "你的名字", "你从哪来",
            # 日常闲聊类
            "讲个笑话", "说个故事", "聊聊天", "有空吗", "最近怎么样", "最近如何",
            "在干嘛", "在做什么", "忙吗", "累不累",
            # 时间天气类（无法获取真实数据）
            "天气", "下雨", "晴天", "温度", "几点", "现在几点", "时间", "日期", "今天几号",
            # 娱乐类
            "笑话", "搞笑", "有趣", "好玩", "电影", "音乐", "歌曲",
            # 生活类
            "好吃", "美食", "餐厅", "好玩", "旅游", "景点",
            # 情感类
            "开心", "高兴", "难过", "伤心", "郁闷", "不爽",
            # 确认类
            "可以吗", "行吗", "好吗", "对不对", "是不是", "会不会",
        ]

        # 管理助手关键词库
        self.admin_keywords = [
            "管理", "后台", "运营", "统计", "报表", "仪表盘",
            "用户", "会员", "注册", "活跃", "用户分析",
            "未命中", "没有答案", "回答不了", "未知问题",
            "知识巡检", "文档检查", "质量检测", "过期",
            "热门问题", "问答统计", "使用率",
            # P4-3 Ops Agent新增
            "知识缺口", "缺口分析", "运营报告", "运营分析",
            "日志分析", "运营建议", "后台建议",
            "活跃用户", "活跃度", "用户活动",
        ]

        # 知识巡检关键词库
        self.inspection_keywords = [
            "巡检", "检查", "检测", "审查",
            "重复文档", "重复", "一样", "相同",
            "低质量", "质量差", "片段", "内容短", "内容长",
            "过期", "陈旧", "太久", "未更新",
            "无人访问", "没人看", "没人查", "访问量",
            "知识库健康", "知识库状态", "文档状态",
        ]

        # 专业问答关键词库（扩展版）
        self.knowledge_qa_keywords = [
            # 数据库相关（重要！）
            "mysql", "oracle", "postgresql", "mongodb", "redis", "elasticsearch",
            "sql", "nosql", "关系型", "非关系型", "数据表", "索引", "事务", "锁", "并发",
            "封锁协议", "一级封锁协议", "二级封锁协议", "三级封锁协议",
            "并发控制", "隔离级别", "可重复读", "脏读", "不可重复读", "丢失修改",
            # 疑问词
            "什么", "怎么", "如何", "为什么", "哪个", "哪里", "谁", "多少", "几", "何时", "怎样",
            # 技术类
            "编程", "代码", "算法", "数据结构", "数据库", "网络", "安全", "加密", "协议",
            "人工智能", "机器学习", "深度学习", "神经网络", "大模型", "LLM", "RAG", "AGI",
            "java", "python", "javascript", "js", "c++", "go", "rust", "typescript", "php", "ruby",
            "spring", "django", "flask", "react", "vue", "angular", "nodejs", "node.js",
            # 概念类
            "原理", "机制", "工作原理", "实现原理", "概念", "定义", "术语", "解释", "说明",
            "是什么", "什么意思", "指什么",
            # 方法类
            "步骤", "流程", "方法", "技巧", "策略", "方案", "思路",
            "怎么做", "如何实现", "如何处理", "如何解决",
            # 比较类
            "比较", "对比", "区别", "差异", "不同", "优势", "缺点", "优缺点",
            "哪个好", "有什么区别", "有什么不同",
            # 应用类
            "应用", "用途", "使用场景", "案例", "例子", "实例",
            "可以用在", "适用于", "用于",
            # 技术概念
            "架构", "设计模式", "微服务", "分布式", "集群", "容器", "docker", "k8s", "kubernetes",
            "缓存", "队列", "消息", "api", "rest", "rpc", "grpc", "websocket",
            "前端", "后端", "全栈", "运维", "DevOps", "CI/CD",
            # 其他技术领域
            "区块链", "物联网", "云计算", "边缘计算", "5G", "大数据", "数据分析",
            "机器视觉", "自然语言处理", "NLP", "CV", "语音识别",
        ]

        # 情感分析词汇（帮助识别闲聊倾向）
        self.emotion_keywords = [
            "哈哈", "呵呵", "嘿嘿", "开心", "高兴", "难过", "伤心", "郁闷", "烦",
            "累", "困", "饿", "渴", "舒服", "不爽", "真好", "太棒了", "不错",
        ]

    def route(self, input_text: str, conversation_id: Optional[str] = None,
              user_id: Optional[str] = None, context: str = "",
              is_admin: bool = False, **kwargs) -> Dict[str, Any]:
        """
        路由并执行任务

        Args:
            input_text: 用户输入
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            is_admin: 是否为管理员
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        task_type = self.classify_task(input_text, is_admin)
        logger.info(f"[RouterAgent] Routing to: {task_type.value} for input: {input_text[:50]}...")

        try:
            if task_type == TaskType.CHITCHAT:
                return self.chitchat_agent.chat(
                    input_text, conversation_id, user_id, context, **kwargs
                )

            elif task_type == TaskType.KNOWLEDGE_QA:
                return self.knowledge_qa_agent.ask(
                    input_text, conversation_id, user_id, context, **kwargs
                )

            elif task_type == TaskType.ADMIN_COPILOT:
                return self.admin_copilot_agent.handle(
                    input_text, conversation_id, user_id, context, **kwargs
                )

            elif task_type == TaskType.KNOWLEDGE_INSPECTION:
                # 从输入中解析巡检类型
                inspection_type = self._parse_inspection_type(input_text)
                return self.inspection_agent.inspect(
                    inspection_type, conversation_id, user_id, context, **kwargs
                )

            else:
                return self.knowledge_qa_agent.ask(
                    input_text, conversation_id, user_id, context, **kwargs
                )
        except Exception as e:
            logger.error(f"[RouterAgent] Route error: {str(e)}")
            return {
                "answer": "抱歉，服务暂时不可用，请稍后再试。",
                "sources": [],
                "has_sources": False,
                "task_type": task_type.value,
                "error": True,
                "error_message": str(e)
            }

    def route_stream(self, input_text: str, conversation_id: Optional[str] = None,
                     user_id: Optional[str] = None, context: str = "",
                     is_admin: bool = False, **kwargs) -> Generator[str, None, None]:
        """
        流式路由并执行任务

        Args:
            input_text: 用户输入
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            is_admin: 是否为管理员
            **kwargs: 其他参数

        Yields:
            JSON格式的事件流
        """
        task_type = self.classify_task(input_text, is_admin)
        logger.info(f"[RouterAgent] Streaming route to: {task_type.value}")

        try:
            yield json.dumps({
                "type": "routed",
                "task_type": task_type.value
            })

            if task_type == TaskType.CHITCHAT:
                for event in self.chitchat_agent.chat_stream(
                    input_text, conversation_id, user_id, context, **kwargs
                ):
                    yield event

            elif task_type == TaskType.KNOWLEDGE_QA:
                for event in self.knowledge_qa_agent.ask_stream(
                    input_text, conversation_id, user_id, context, **kwargs
                ):
                    yield event

            elif task_type == TaskType.ADMIN_COPILOT:
                for event in self.admin_copilot_agent.handle_stream(
                    input_text, conversation_id, user_id, context, **kwargs
                ):
                    yield event

            elif task_type == TaskType.KNOWLEDGE_INSPECTION:
                inspection_type = self._parse_inspection_type(input_text)
                for event in self.inspection_agent.inspect_stream(
                    inspection_type, conversation_id, user_id, context, **kwargs
                ):
                    yield event

            else:
                for event in self.knowledge_qa_agent.ask_stream(
                    input_text, conversation_id, user_id, context, **kwargs
                ):
                    yield event

        except Exception as e:
            logger.error(f"[RouterAgent] Stream route error: {str(e)}")
            yield json.dumps({
                "type": "error",
                "content": str(e)
            })

    def classify_task(self, input_text: str, is_admin: bool = False) -> TaskType:
        """
        分类任务类型（基于关键词权重）

        Args:
            input_text: 用户输入
            is_admin: 是否为管理员

        Returns:
            任务类型
        """
        lower_text = input_text.lower()

        # 去除中英文标点符号，避免 "你是谁？" 中 "？" 干扰分类
        clean_text = re.sub(r'[，。！？、；：""''【】《》（）\(\)\[\]\{\}<>\?\!\.\,\;\:\"\'\-\—\…\~\`]', '', lower_text)

        # 计算各类关键词命中数量（使用去除标点后的文本）
        chitchat_score = sum(1 for kw in self.chitchat_keywords if kw in clean_text)
        knowledge_score = sum(1 for kw in self.knowledge_qa_keywords if kw in clean_text)
        admin_score = sum(1 for kw in self.admin_keywords if kw in clean_text)
        inspection_score = sum(1 for kw in self.inspection_keywords if kw in clean_text)
        emotion_score = sum(1 for kw in self.emotion_keywords if kw in clean_text)

        logger.debug(f"[RouterAgent] Scores - chitchat:{chitchat_score}, knowledge:{knowledge_score}, admin:{admin_score}, inspection:{inspection_score}")

        # 管理员模式：优先处理管理相关任务
        if is_admin:
            # 知识巡检优先级最高
            if inspection_score > 0:
                return TaskType.KNOWLEDGE_INSPECTION
            # 管理助手
            if admin_score > 0:
                # 如果技术词汇更多，可能是知识问答
                if knowledge_score >= admin_score:
                    return TaskType.KNOWLEDGE_QA
                return TaskType.ADMIN_COPILOT

        # 知识巡检（管理员和普通用户都可以触发）
        if inspection_score > 0 and inspection_score >= knowledge_score:
            return TaskType.KNOWLEDGE_INSPECTION

        # 技术问题优先判定为知识问答
        if knowledge_score >= 2:
            return TaskType.KNOWLEDGE_QA

        # 闲聊判断（基于多个因素）
        if chitchat_score > 0 or emotion_score > 0:
            # 如果文本较短且包含闲聊词汇
            if len(input_text.strip()) < 15:
                # 包含技术词汇则优先知识问答（技术词汇权重更高）
                if knowledge_score > chitchat_score:
                    return TaskType.KNOWLEDGE_QA
                return TaskType.CHITCHAT
            # 长文本：如果闲聊词和技术词都多，取分值高的
            if knowledge_score > chitchat_score:
                return TaskType.KNOWLEDGE_QA
            return TaskType.CHITCHAT

        # 短文本处理（没有任何关键词命中）
        if len(input_text.strip()) < 10:
            # 检查是否包含疑问词
            question_words = ["什么", "怎么", "如何", "为什么", "哪个", "哪里", "谁", "多少", "?", "？"]
            if any(kw in clean_text for kw in question_words):
                return TaskType.KNOWLEDGE_QA
            # 纯问候
            return TaskType.CHITCHAT

        # 有一个技术关键词就判定为知识问答
        if knowledge_score >= 1:
            return TaskType.KNOWLEDGE_QA

        # 默认是知识问答
        return TaskType.KNOWLEDGE_QA

    def _parse_inspection_type(self, input_text: str) -> str:
        """从输入中解析巡检类型"""
        lower_text = input_text.lower()

        if "重复" in lower_text:
            return "duplicate"
        elif "低质量" in lower_text or "质量" in lower_text or "片段" in lower_text:
            return "low_quality"
        elif "过期" in lower_text or "陈旧" in lower_text:
            return "stale"
        elif "无人访问" in lower_text or "没人看" in lower_text or "访问" in lower_text:
            return "unpopular"
        else:
            return "full"

    def get_agent(self, task_type: TaskType):
        """获取对应的Agent"""
        agent_map = {
            TaskType.CHITCHAT: self.chitchat_agent,
            TaskType.KNOWLEDGE_QA: self.knowledge_qa_agent,
            TaskType.ADMIN_COPILOT: self.admin_copilot_agent,
            TaskType.KNOWLEDGE_INSPECTION: self.inspection_agent,
        }
        return agent_map.get(task_type, self.knowledge_qa_agent)

    def get_task_stats(self) -> Dict[str, int]:
        """获取各类关键词数量统计（用于调试和分析）"""
        return {
            "chitchat_keywords": len(self.chitchat_keywords),
            "knowledge_qa_keywords": len(self.knowledge_qa_keywords),
            "admin_keywords": len(self.admin_keywords),
            "inspection_keywords": len(self.inspection_keywords),
            "emotion_keywords": len(self.emotion_keywords),
        }
