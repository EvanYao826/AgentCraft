from typing import Dict, Any, Optional, Generator, List
from core.mysql_client import mysql_client
import logging
import json

logger = logging.getLogger(__name__)


class OpsAgent:
    """
    Ops Agent - 负责运营分析与后台建议

    功能：
    1. 自动分析日志
    2. 自动提示知识缺口
    3. 自动生成后台建议
    """

    def __init__(self):
        self.analysis_types = {
            "knowledge_gap": "知识缺口分析",
            "qa_trend": "问答趋势分析",
            "user_activity": "用户活跃度分析",
            "full_report": "完整运营报告"
        }

    def analyze(self, analysis_type: str = "full_report", **kwargs) -> Dict[str, Any]:
        """
        执行运营分析

        Args:
            analysis_type: 分析类型（knowledge_gap/qa_trend/user_activity/full_report）
            **kwargs: 其他参数

        Returns:
            分析结果与建议
        """
        logger.info(f"[OpsAgent] Starting analysis: {analysis_type}")

        try:
            if analysis_type == "knowledge_gap":
                return self._analyze_knowledge_gap()
            elif analysis_type == "qa_trend":
                return self._analyze_qa_trend()
            elif analysis_type == "user_activity":
                return self._analyze_user_activity()
            elif analysis_type == "full_report":
                return self._generate_full_report()
            else:
                return {
                    "success": False,
                    "error": f"Unknown analysis type: {analysis_type}",
                    "available_types": list(self.analysis_types.keys())
                }

        except Exception as e:
            logger.error(f"[OpsAgent] Analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def analyze_stream(self, analysis_type: str = "full_report", **kwargs) -> Generator[str, None, None]:
        """流式执行运营分析"""
        logger.info(f"[OpsAgent] Starting streaming analysis: {analysis_type}")

        try:
            yield json.dumps({"type": "analysis_started", "analysis_type": analysis_type})

            result = self.analyze(analysis_type, **kwargs)

            yield json.dumps({"type": "analysis_progress", "step": "log_analysis", "status": "completed"})
            yield json.dumps({"type": "analysis_progress", "step": "knowledge_gap_identification", "status": "completed"})
            yield json.dumps({"type": "analysis_progress", "step": "suggestion_generation", "status": "completed"})

            yield json.dumps({"type": "analysis_completed", "result": result})

        except Exception as e:
            logger.error(f"[OpsAgent] Stream analysis failed: {e}", exc_info=True)
            yield json.dumps({"type": "error", "error": str(e)})

    def _analyze_knowledge_gap(self) -> Dict[str, Any]:
        """分析知识缺口 - P4-3核心功能"""
        logger.info("[OpsAgent] Analyzing knowledge gap")

        # 查询未命中问题
        unanswered_query = """
            SELECT question, count, create_time 
            FROM qa_unanswered 
            ORDER BY count DESC 
            LIMIT 20
        """
        unanswered_questions = mysql_client.fetch_all(unanswered_query) or []

        # 查询最近的QA日志
        qa_log_query = """
            SELECT question, answer, create_time 
            FROM qa_log 
            ORDER BY create_time DESC 
            LIMIT 50
        """
        recent_qa = mysql_client.fetch_all(qa_log_query) or []

        # 分析知识缺口
        knowledge_gaps = []
        for qa in unanswered_questions:
            question = qa.get("question", "")
            count = qa.get("count", 0)

            # 简单分类
            gap_type = self._classify_gap(question)
            knowledge_gaps.append({
                "question": question,
                "count": count,
                "gap_type": gap_type,
                "priority": "high" if count > 5 else "medium" if count > 2 else "low"
            })

        # 生成建议
        suggestions = self._generate_gap_suggestions(knowledge_gaps)

        answer = f"""🔍 知识缺口分析报告

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 未命中问题概览：
- 高优先级（>5次）：{len([g for g in knowledge_gaps if g["priority"] == "high"])}
- 中优先级（2-5次）：{len([g for g in knowledge_gaps if g["priority"] == "medium"])}
- 低优先级（1-2次）：{len([g for g in knowledge_gaps if g["priority"] == "low"])}

━━━━━━━━━━━━━━━━━━━━━━━━━

📋 TOP 未命中问题：
"""
        for i, gap in enumerate(knowledge_gaps[:10], 1):
            answer += f"{i}. [{gap['priority']}] {gap['question']} ({gap['count']}次)\n"

        answer += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━

💡 建议：
"""
        for i, suggestion in enumerate(suggestions[:5], 1):
            answer += f"{i}. {suggestion}\n"

        return {
            "success": True,
            "answer": answer,
            "data": {
                "knowledge_gaps": knowledge_gaps,
                "suggestions": suggestions,
                "unanswered_count": len(unanswered_questions),
                "recent_qa_count": len(recent_qa)
            },
            "task_type": "ops_analysis"
        }

    def _analyze_qa_trend(self) -> Dict[str, Any]:
        """分析问答趋势"""
        logger.info("[OpsAgent] Analyzing QA trend")

        # 查询最近7天的QA数量
        trend_query = """
            SELECT 
                DATE(create_time) as log_date,
                COUNT(*) as question_count
            FROM qa_log
            WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(create_time)
            ORDER BY log_date DESC
        """
        qa_trend = mysql_client.fetch_all(trend_query) or []

        # 查询今日统计
        today_query = """
            SELECT COUNT(*) as today_count
            FROM qa_log
            WHERE DATE(create_time) = DATE(NOW())
        """
        today_stats = mysql_client.fetch_one(today_query) or {}

        answer = f"""📈 问答趋势分析

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 今日问答：
- 今日问答次数：{today_stats.get('today_count', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━

📅 近7天趋势：
"""
        for i, daily in enumerate(qa_trend, 1):
            log_date = str(daily.get('log_date', ''))
            count = daily.get('question_count', 0)
            answer += f"{log_date}: {count} 次问答\n"

        return {
            "success": True,
            "answer": answer,
            "data": {
                "qa_trend": qa_trend,
                "today_count": today_stats.get('today_count', 0)
            },
            "task_type": "ops_analysis"
        }

    def _analyze_user_activity(self) -> Dict[str, Any]:
        """分析用户活跃度"""
        logger.info("[OpsAgent] Analyzing user activity")

        # 查询活跃用户
        user_query = """
            SELECT 
                userId as user_id,
                COUNT(*) as qa_count,
                MAX(create_time) as last_active
            FROM qa_log
            WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY userId
            ORDER BY qa_count DESC
            LIMIT 20
        """
        active_users = mysql_client.fetch_all(user_query) or []

        # 查询总用户
        user_count_query = "SELECT COUNT(*) as user_count FROM users"
        user_count = mysql_client.fetch_one(user_count_query) or {}

        answer = f"""👥 用户活跃度分析

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 总用户：{user_count.get('user_count', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 活跃用户 TOP 10：
"""
        for i, user in enumerate(active_users[:10], 1):
            user_id = user.get('user_id', 'N/A')
            qa_count = user.get('qa_count', 0)
            last_active = str(user.get('last_active', ''))
            answer += f"{i}. 用户 {user_id}: {qa_count} 次问答 (最后活跃: {last_active})\n"

        return {
            "success": True,
            "answer": answer,
            "data": {
                "active_users": active_users,
                "total_users": user_count.get('user_count', 0)
            },
            "task_type": "ops_analysis"
        }

    def _generate_full_report(self) -> Dict[str, Any]:
        """生成完整运营报告"""
        logger.info("[OpsAgent] Generating full report")

        gap_result = self._analyze_knowledge_gap()
        trend_result = self._analyze_qa_trend()
        activity_result = self._analyze_user_activity()

        # 整合建议
        suggestions = []
        if gap_result.get("data", {}).get("knowledge_gaps", []):
            suggestions.append("建议优先补充高频未命中问题的知识")
        if activity_result.get("data", {}).get("active_users", []):
            suggestions.append("可以关注活跃用户的问题需求")
        suggestions.append("定期进行知识巡检保证知识库质量")

        answer = f"""📋 完整运营分析报告

━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ 知识缺口分析
{gap_result.get('answer', '').split('━━━━━━━━━━━━━━━━━━━━━━━━━')[1].split('💡 建议')[0]}

━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ 问答趋势分析
{trend_result.get('answer', '').split('━━━━━━━━━━━━━━━━━━━━━━━━━')[1]}

━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ 用户活跃度分析
{activity_result.get('answer', '').split('━━━━━━━━━━━━━━━━━━━━━━━━━')[1]}

━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 运营建议：
"""
        for i, suggestion in enumerate(suggestions, 1):
            answer += f"{i}. {suggestion}\n"

        return {
            "success": True,
            "answer": answer,
            "data": {
                "knowledge_gap": gap_result.get("data"),
                "qa_trend": trend_result.get("data"),
                "user_activity": activity_result.get("data"),
                "suggestions": suggestions
            },
            "task_type": "ops_analysis"
        }

    def _classify_gap(self, question: str) -> str:
        """分类知识缺口类型"""
        lower_q = question.lower()

        tech_keywords = ["python", "java", "sql", "database", "算法", "编程", "代码"]
        for kw in tech_keywords:
            if kw in lower_q:
                return "技术知识"

        business_keywords = ["流程", "制度", "规定", "流程", "审批"]
        for kw in business_keywords:
            if kw in lower_q:
                return "业务知识"

        return "通用知识"

    def _generate_gap_suggestions(self, knowledge_gaps: List[Dict]) -> List[str]:
        """生成知识缺口建议"""
        suggestions = []

        if knowledge_gaps:
            high_priority = [g for g in knowledge_gaps if g.get("priority") == "high"]
            if high_priority:
                suggestions.append(f"优先补充高频问题：{high_priority[0].get('question', '')}")

            tech_gaps = [g for g in knowledge_gaps if g.get("gap_type") == "技术知识"]
            if tech_gaps:
                suggestions.append("建议完善技术知识库")

            suggestions.append("可以创建一个新的知识分类来整理这些未覆盖的知识")

        return suggestions

    def get_analysis_options(self) -> Dict[str, Any]:
        """获取可执行的分析选项"""
        return {
            "available_analysis": self.analysis_types,
            "usage": {
                "knowledge_gap": "分析知识缺口和未命中问题",
                "qa_trend": "分析问答趋势和统计",
                "user_activity": "分析用户活跃度",
                "full_report": "生成完整运营报告（推荐）"
            }
        }


# 全局实例
ops_agent = OpsAgent()
