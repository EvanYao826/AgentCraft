from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.parser import DocumentParser
from core.vector_store import vector_store
from core.llm import LLMService
from core.mysql_client import mysql_client
from workflows import RouterAgent
import os
import re
import logging
import json
import time

# 配置结构化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化 RouterAgent
router_agent = RouterAgent()

# 问题类型判断器 - 判断问题是否应该返回文档引用
def should_return_sources(question: str) -> bool:
    """
    判断用户问题是否应该返回文档引用

    规则：
    1. 技术类、专业类、知识类问题 - 返回文档引用（优先匹配）
    2. 生活类、聊天类、娱乐类问题 - 不返回文档引用
    3. 基于关键词和问题模式判断
    """
    lower_question = question.lower()

    # 1. 技术类、专业类、知识类问题 - 返回文档引用（优先匹配）
    # 这些关键词表示可能需要专业知识
    knowledge_keywords = [
        # 技术相关 - 精确匹配模式
        "什么是", "如何", "怎么", "为什么", "原理", "机制", "工作",
        "定义", "概念", "术语", "解释", "说明",
        "步骤", "流程", "方法", "技巧", "策略",
        "优势", "缺点", "优缺点", "特点", "特性",
        "比较", "对比", "区别", "差异",
        "应用", "用途", "使用场景", "案例",
        "发展", "历史", "趋势", "未来",
        "标准", "规范", "协议", "框架",

        # 专业领域
        "编程", "代码", "算法", "数据结构", "数据库",
        "网络", "安全", "加密", "协议",
        "人工智能", "机器学习", "深度学习", "神经网络",
        "大数据", "云计算", "物联网", "区块链",
        "数学", "物理", "化学", "生物", "医学",
        "经济", "金融", "商业", "管理", "营销",
        "法律", "法规", "政策", "制度",
        "教育", "学习", "培训", "课程",

        # 文档相关
        "文档", "资料", "文件", "报告", "论文", "研究",
        "根据", "参考", "依据", "来源",
    ]

    for keyword in knowledge_keywords:
        # 检查关键词是否在问题中
        if keyword in lower_question:
            # 特殊处理"什么是"和"是什么"的歧义
            if keyword == "什么是":
                # "什么是"应该匹配"什么是一级封锁协议"，但不匹配"是什么地方"
                # 检查"什么是"是否出现在问题开头或前面有边界
                if lower_question.startswith("什么是"):
                    logger.info(f"Question starts with '什么是': {question} - will return sources if found")
                    return True
                # 检查"什么是"是否作为独立词出现
                pattern = r'(^|\s|[,.!?;:])什么是($|\s|[,.!?;:])'
                if re.search(pattern, lower_question):
                    logger.info(f"Question contains '什么是' as separate word: {question} - will return sources if found")
                    return True
            else:
                # 对于其他关键词，简单匹配
                logger.info(f"Question classified as knowledge-related (keyword: '{keyword}'): {question} - will return sources if found")
                return True

    # 2. 生活类、聊天类、娱乐类问题 - 不返回文档引用
    life_chat_keywords = [
        # 问候聊天
        "你好", "您好", "hello", "hi", "早上好", "下午好", "晚上好",
        "最近好吗", "最近怎么样", "在干嘛", "在做什么",
        "谢谢", "感谢", "再见", "拜拜",

        # 知道/了解类闲聊
        "知道", "了解", "认识", "听说过", "听过",
        "你觉得", "你认为", "你怎么看", "你怎么想",

        # 日常生活
        "今天天气", "天气预报", "天气怎么样",
        "现在几点", "现在时间", "今天日期", "今天是",
        "有什么好吃的", "好吃", "美食", "餐厅", "饭店",
        "好玩", "旅游", "景点", "去哪里玩",
        "电影", "电视剧", "音乐", "歌曲", "娱乐",
        "购物", "买什么", "哪里买",
        "健康", "健身", "运动", "减肥",
        "感情", "恋爱", "爱情", "婚姻", "家庭",

        # 个人相关
        "你叫什么", "你是谁", "你是什么", "你的名字",
        "我帅吗", "我漂亮吗", "我聪明吗", "我怎么样",

        # 娱乐闲聊
        "讲个笑话", "说个故事", "唱首歌", "猜谜语",
        "星座", "运势", "算命", "占卜",

        # 询问意见/建议
        "可以吗", "行吗", "好吗", "对不对", "是不是",
        "能不能", "会不会", "要不要", "该不该",

        # 简单事实查询（可能不需要文档引用）
        "在哪里", "是什么地方", "哪个城市", "哪个国家",
        "多少钱", "价格", "贵不贵",
        "怎么去", "路线", "交通",
    ]

    for keyword in life_chat_keywords:
        if keyword in lower_question:
            # 特殊处理"是什么地方"的歧义
            if keyword == "是什么地方":
                # "是什么地方"应该匹配"北京是什么地方"，但不匹配"什么是一级封锁协议"
                # 检查"是什么地方"是否出现在问题中
                if "是什么地方" in lower_question:
                    logger.info(f"Question contains '是什么地方': {question} - will not return sources")
                    return False
            else:
                # 对于其他生活类关键词，简单匹配
                logger.info(f"Question classified as life/chat (keyword: '{keyword}'): {question} - will not return sources")
                return False

    # 3. 默认：对于不确定的问题，保守起见不返回文档引用
    # 只有明确的技术问题才返回引用，闲聊问题不返回
    logger.info(f"Question classification uncertain: {question} - will NOT return sources by default")
    return False

# 初始化核心服务
try:
    logger.info("Initializing DocumentParser...")
    parser = DocumentParser()
    logger.info("Using shared VectorStoreManager singleton...")
    logger.info("Initializing LLMService...")
    llm_service = LLMService()
    logger.info("Services initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing services: {e}")
    # Consider whether to exit or just log, depending on whether the app can run partially.
    # For now, we'll let it run, but requests might fail.

class ParseRequest(BaseModel):
    file_path: str
    doc_id: int

class ChatRequest(BaseModel):
    question: str
    context: str = "" # Optional, if context is passed directly (not used here)
    conversation_id: str = None # Optional, for conversation memory
    username: str = None # Optional, if username is provided
    is_admin: bool = False # Optional, whether user is admin

class SummaryRequest(BaseModel):
    question: str

# 移除中间件，改用在每个路由中记录请求时间
# APIRouter 不支持 middleware 方法，中间件只能添加到 FastAPI 应用实例

@router.post("/parse")
async def parse_document(request: ParseRequest):
    """
    解析文档并存入向量库
    """
    start_time = time.time()
    try:
        # 判断 file_path 是 URL 还是本地路径
        is_url = request.file_path.startswith('http://') or request.file_path.startswith('https://')
        
        if not is_url and not os.path.exists(request.file_path):
            logger.warning(f"File not found: {request.file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")

        logger.info(f"Parsing document: {request.file_path}")
        # Parse the document
        chunks = parser.parse(request.file_path)
        
        # Add metadata
        for chunk in chunks:
            chunk.metadata["doc_id"] = request.doc_id
            chunk.metadata["source"] = request.file_path

        logger.info(f"Generated {len(chunks)} chunks. Adding to vector store...")
        try:
            vector_store.add_documents(chunks)
        except Exception as ve:
            logger.error(f"Vector store add_documents failed: {type(ve).__name__}: {ve}", exc_info=True)
            raise ve
        
        logger.info(f"Saving chunks to MySQL database...")
        mysql_client.insert_chunks(request.doc_id, [
            {"page_content": chunk.page_content, "chunk_index": chunk.metadata.get("chunk_index", i)}
            for i, chunk in enumerate(chunks)
        ])
        
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/parse",
                "status_code": 200,
                "process_time": process_time
            })
        )
        return {"status": "success", "chunks_count": len(chunks)}
    except HTTPException as e:
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/parse",
                "status_code": e.status_code,
                "process_time": process_time
            })
        )
        raise
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error parsing document: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/parse",
                "status_code": 500,
                "process_time": process_time
            })
        )
        # 不返回具体错误信息，避免泄露内部实现细节
        raise HTTPException(status_code=500, detail="文档解析失败")

@router.post("/ask")
async def ask_question(request: ChatRequest):
    """
    问答接口 - 使用 RouterAgent 进行任务路由
    """
    start_time = time.time()
    try:
        logger.info(f"Received question: {request.question}, username: {request.username}, is_admin: {request.is_admin}")
        
        # 处理身份相关问题
        lower_question = request.question.lower()
        identity_keywords = ["我是谁", "我叫什么", "我的名字", "我的身份"]
        if any(keyword in lower_question for keyword in identity_keywords) and request.username:
            logger.info(f"Answering identity question for user: {request.username}")
            answer = f"你是 {request.username}，是本系统的注册用户。"
            response = {"answer": answer, "sources": [], "task_type": "chitchat"}
        else:
            # 使用 RouterAgent 进行任务路由
            result = router_agent.route(
                input_text=request.question,
                conversation_id=request.conversation_id,
                context=request.context,
                username=request.username,
                is_admin=request.is_admin
            )
            
            # 构建响应
            response = {
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "task_type": result.get("task_type", "unknown")
            }
        
        logger.info(f"Response generated successfully, task_type: {response.get('task_type')}")
        
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/ask",
                "status_code": 200,
                "process_time": process_time
            })
        )
        return response
    except HTTPException as e:
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/ask",
                "status_code": e.status_code,
                "process_time": process_time
            })
        )
        raise
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error processing question: {str(e)}")
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/ask",
                "status_code": 500,
                "process_time": process_time
            })
        )
        # 不返回具体错误信息，避免泄露内部实现细节
        raise HTTPException(status_code=500, detail="问答处理失败")

@router.post("/ask/stream")
async def ask_question_stream(request: ChatRequest):
    """
    流式问答接口 (Server-Sent Events) - 使用 RouterAgent
    """
    start_time = time.time()

    async def event_generator():
        try:
            logger.info(f"Streaming question: {request.question}, username: {request.username}, is_admin: {request.is_admin}")

            # 处理身份相关问题
            lower_question = request.question.lower()
            identity_keywords = ["我是谁", "我叫什么", "我的名字", "我的身份"]
            if any(keyword in lower_question for keyword in identity_keywords) and request.username:
                logger.info(f"Streaming identity answer for user: {request.username}")
                answer = f"你是 {request.username}，是本系统的注册用户。"
                # 流式返回身份回答
                for char in answer:
                    yield f"data: {json.dumps({'type': 'token', 'content': char})}\n\n"
                yield f"data: {json.dumps({'type': 'end', 'content': answer, 'task_type': 'chitchat'})}\n\n"
                return

            # 使用 RouterAgent 进行流式任务路由
            for event_data in router_agent.route_stream(
                input_text=request.question,
                context=request.context,
                username=request.username,
                is_admin=request.is_admin
            ):
                yield f"data: {event_data}\n\n"

            process_time = time.time() - start_time
            logger.info(
                json.dumps({
                    "method": "POST",
                    "path": "/api/ask/stream",
                    "status_code": 200,
                    "process_time": process_time
                })
            )

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Error in streaming question: {str(e)}")
            logger.info(
                json.dumps({
                    "method": "POST",
                    "path": "/api/ask/stream",
                    "status_code": 500,
                    "process_time": process_time
                })
            )
            yield f"data: {json.dumps({'type': 'error', 'content': '流式问答处理失败'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
        }
    )

@router.post("/delete")
async def delete_document(request: ParseRequest):
    """
    删除文档的向量索引
    """
    start_time = time.time()
    try:
        if request.doc_id:
            logger.info(f"Deleting document with doc_id: {request.doc_id}")
            vector_store.delete_document(request.doc_id)
            
            process_time = time.time() - start_time
            logger.info(
                json.dumps({
                    "method": "POST",
                    "path": "/api/delete",
                    "status_code": 200,
                    "process_time": process_time
                })
            )
            return {"status": "success", "message": f"Document {request.doc_id} deleted"}
        else:
             logger.warning("doc_id is required")
             raise HTTPException(status_code=400, detail="doc_id is required")
    except HTTPException as e:
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/delete",
                "status_code": e.status_code,
                "process_time": process_time
            })
        )
        raise
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error deleting document: {str(e)}")
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/delete",
                "status_code": 500,
                "process_time": process_time
            })
        )
        # 不返回具体错误信息，避免泄露内部实现细节
        raise HTTPException(status_code=500, detail="文档删除失败")

@router.post("/summary")
async def generate_summary(request: SummaryRequest):
    """
    生成会话标题
    """
    start_time = time.time()
    try:
        title = llm_service.generate_title(request.question)
        logger.info(f"Generated summary: {title}")

        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/summary",
                "status_code": 200,
                "process_time": process_time
            })
        )
        return {"title": title}
    except HTTPException as e:
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/summary",
                "status_code": e.status_code,
                "process_time": process_time
            })
        )
        raise
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error generating summary: {str(e)}")
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/summary",
                "status_code": 500,
                "process_time": process_time
            })
        )
        # 不返回具体错误信息，避免泄露内部实现细节
        raise HTTPException(status_code=500, detail="标题生成失败")

@router.get("/vector-store/stats")
async def get_vector_store_stats():
    """
    获取向量库统计信息
    """
    start_time = time.time()
    try:
        stats = vector_store.get_stats()

        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "GET",
                "path": "/api/vector-store/stats",
                "status_code": 200,
                "process_time": process_time
            })
        )
        return stats
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error getting vector store stats: {str(e)}")
        logger.info(
            json.dumps({
                "method": "GET",
                "path": "/api/vector-store/stats",
                "status_code": 500,
                "process_time": process_time
            })
        )
        raise HTTPException(status_code=500, detail="获取向量库统计信息失败")

@router.post("/vector-store/migrate")
async def migrate_to_milvus():
    """
    将FAISS数据迁移到Milvus
    """
    start_time = time.time()
    try:
        if not vector_store.use_milvus:
            raise HTTPException(status_code=400, detail="当前未使用Milvus，无法迁移")

        success = vector_store.migrate_faiss_to_milvus()

        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/vector-store/migrate",
                "status_code": 200,
                "process_time": process_time
            })
        )

        if success:
            return {"status": "success", "message": "数据迁移成功"}
        else:
            return {"status": "partial", "message": "迁移完成但可能有部分数据未迁移"}

    except HTTPException as e:
        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/vector-store/migrate",
                "status_code": e.status_code,
                "process_time": process_time
            })
        )
        raise
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error migrating to Milvus: {str(e)}")
        logger.info(
            json.dumps({
                "method": "POST",
                "path": "/api/vector-store/migrate",
                "status_code": 500,
                "process_time": process_time
            })
        )
        raise HTTPException(status_code=500, detail="数据迁移失败")

@router.delete("/vector-store/collection")
async def delete_vector_collection():
    """
    删除整个向量库（慎用）
    """
    start_time = time.time()
    try:
        # 添加确认机制（实际生产环境需要更严格的权限控制）
        vector_store.delete_collection()

        process_time = time.time() - start_time
        logger.info(
            json.dumps({
                "method": "DELETE",
                "path": "/api/vector-store/collection",
                "status_code": 200,
                "process_time": process_time
            })
        )
        return {"status": "success", "message": "向量库已删除"}
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error deleting vector collection: {str(e)}")
        logger.info(
            json.dumps({
                "method": "DELETE",
                "path": "/api/vector-store/collection",
                "status_code": 500,
                "process_time": process_time
            })
        )
        raise HTTPException(status_code=500, detail="删除向量库失败")
