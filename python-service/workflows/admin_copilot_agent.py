from typing import Dict, Any, Optional, Generator
from core.mysql_client import mysql_client
from workflows.ops_agent import ops_agent
import logging
import json

logger = logging.getLogger(__name__)


class AdminCopilotAgent:
    """管理助手Agent - 专门处理管理端运营分析的工作流"""

    def __init__(self):
        self.ops_agent = ops_agent
        self.admin_operations = {
            "stats": "统计分析",
            "knowledge_inspection": "知识巡检",
            "knowledge_gap": "知识缺口分析（P4-3）",
            "unanswered_analysis": "未命中分析",
            "user_activity": "用户活跃度分析",
            "full_ops_report": "完整运营报告（P4-3）",
        }

    def handle(self, question: str, conversation_id: Optional[str] = None,
               user_id: Optional[str] = None, context: str = "",
               **kwargs) -> Dict[str, Any]:
        """
        处理管理助手请求

        Args:
            question: 用户问题
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            **kwargs: 其他参数

        Returns:
            包含answer和sources的字典
        """
        logger.info(f"[AdminCopilotAgent] Processing admin request: {question[:50]}...")

        try:
            operation = self._parse_operation(question)
            result = self._execute_operation(operation, question)

            return result

        except Exception as e:
            logger.error(f"[AdminCopilotAgent] Error: {e}", exc_info=True)
            return {
                "answer": f"抱歉，处理管理请求时出错：{str(e)}",
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "error": True
            }

    def handle_stream(self, question: str, conversation_id: Optional[str] = None,
                     user_id: Optional[str] = None, context: str = "",
                     **kwargs) -> Generator[str, None, None]:
        """流式处理管理助手请求"""
        logger.info(f"[AdminCopilotAgent] Stream admin request: {question[:50]}...")

        try:
            operation = self._parse_operation(question)

            if operation in ["knowledge_gap", "full_ops_report"]:
                yield from self.ops_agent.analyze_stream(
                    "knowledge_gap" if operation == "knowledge_gap" else "full_report"
                )
                return

            result = self.handle(question, conversation_id, user_id, context, **kwargs)
            answer = result.get("answer", "")

            for char in answer:
                yield json.dumps({"type": "token", "content": char})

            yield json.dumps({"type": "end", "content": result})

        except Exception as e:
            logger.error(f"[AdminCopilotAgent] Stream error: {e}", exc_info=True)
            yield json.dumps({"type": "error", "error": str(e)})

    def _parse_operation(self, question: str) -> str:
        """解析操作类型"""
        lower_question = question.lower()

        if any(kw in lower_question for kw in ["知识缺口", "缺口", "未命中", "知识缺口分析"]):
            return "knowledge_gap"
        if any(kw in lower_question for kw in ["运营报告", "完整报告", "全报告", "运营分析"]):
            return "full_ops_report"
        if any(kw in lower_question for kw in ["用户", "活跃度", "活跃用户"]):
            return "user_activity"
        if any(kw in lower_question for kw in ["统计", "报表", "数据", "分析", "多少", "数量"]):
            return "stats"
        if any(kw in lower_question for kw in ["知识", "文档", "巡检", "检查", "质量"]):
            return "knowledge_inspection"

        return "stats"

    def _execute_operation(self, operation: str, question: str) -> Dict[str, Any]:
        """执行管理操作"""
        try:
            if operation == "stats":
                return self._get_stats()
            elif operation == "knowledge_inspection":
                return self._knowledge_inspection()
            elif operation == "knowledge_gap":
                return self._analyze_knowledge_gap()
            elif operation == "user_activity":
                return self._analyze_user_activity()
            elif operation == "full_ops_report":
                return self._generate_full_ops_report()
            else:
                return {
                    "answer": "抱歉，我暂时无法处理这类管理请求。",
                    "sources": [],
                    "has_sources": False,
                    "task_type": "admin_copilot"
                }
        except Exception as e:
            logger.error(f"[AdminCopilotAgent] Operation error: {e}", exc_info=True)
            return {
                "answer": f"执行操作时出错：{str(e)}",
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "error": True
            }

    def _get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        try:
            doc_count = mysql_client.fetch_one("SELECT COUNT(*) as count FROM knowledge_docs") or {}
            chunk_count = mysql_client.fetch_one("SELECT COUNT(*) as count FROM knowledge_chunks") or {}
            qa_count = mysql_client.fetch_one("SELECT COUNT(*) as count FROM qa_log") or {}
            user_count = mysql_client.fetch_one("SELECT COUNT(*) as count FROM users") or {}
            unanswered_count = mysql_client.fetch_one("SELECT COUNT(*) as count FROM qa_unanswered") or {}

            answer = f"""📊 系统统计信息

━━━━━━━━━━━━━━━━━━━━━━━━━

📚 知识库：
- 文档数量：{doc_count.get('count', 0)}
- 知识片段：{chunk_count.get('count', 0)}

💬 问答系统：
- 总问答次数：{qa_count.get('count', 0)}
- 未命中问题：{unanswered_count.get('count', 0)}

👥 用户管理：
- 注册用户：{user_count.get('count', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 提示：
- 说"知识缺口分析"可以查看知识缺口（P4-3功能）
- 说"完整运营报告"可以获取完整分析（P4-3功能）
"""

            return {
                "answer": answer,
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "data": {
                    "doc_count": doc_count.get('count', 0),
                    "chunk_count": chunk_count.get('count', 0),
                    "qa_count": qa_count.get('count', 0),
                    "user_count": user_count.get('count', 0),
                    "unanswered_count": unanswered_count.get('count', 0)
                }
            }
        except Exception as e:
            logger.error(f"[AdminCopilotAgent] Stats error: {e}", exc_info=True)
            return {
                "answer": "获取统计数据失败，请稍后重试。",
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "error": True
            }

    def _knowledge_inspection(self) -> Dict[str, Any]:
        """知识巡检 - 调用InspectionAgent"""
        from workflows.inspection_agent import InspectionAgent
        inspection_agent = InspectionAgent()
        return inspection_agent.inspect("full")

    def _analyze_knowledge_gap(self) -> Dict[str, Any]:
        """知识缺口分析 - P4-3功能 - 调用Ops Agent"""
        logger.info("[AdminCopilotAgent] Analyzing knowledge gap via Ops Agent")
        result = self.ops_agent.analyze("knowledge_gap")
        if result.get("success"):
            return {
                "answer": result.get("answer", ""),
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "data": result.get("data", {})
            }
        else:
            return {
                "answer": "知识缺口分析失败：" + str(result.get("error", "")),
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "error": True
            }

    def _analyze_user_activity(self) -> Dict[str, Any]:
        """用户活跃度分析 - 调用Ops Agent"""
        logger.info("[AdminCopilotAgent] Analyzing user activity via Ops Agent")
        result = self.ops_agent.analyze("user_activity")
        if result.get("success"):
            return {
                "answer": result.get("answer", ""),
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "data": result.get("data", {})
            }
        else:
            return {
                "answer": "用户活跃度分析失败：" + str(result.get("error", "")),
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "error": True
            }

    def _generate_full_ops_report(self) -> Dict[str, Any]:
        """生成完整运营报告 - P4-3功能 - 调用Ops Agent"""
        logger.info("[AdminCopilotAgent] Generating full ops report via Ops Agent")
        result = self.ops_agent.analyze("full_report")
        if result.get("success"):
            return {
                "answer": result.get("answer", ""),
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "data": result.get("data", {})
            }
        else:
            return {
                "answer": "完整运营报告生成失败：" + str(result.get("error", "")),
                "sources": [],
                "has_sources": False,
                "task_type": "admin_copilot",
                "error": True
            }
