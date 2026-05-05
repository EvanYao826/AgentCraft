from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from core.config import config


@dataclass
class Citation:
    """引用信息"""
    document_id: str
    chunk_id: Optional[int]
    content: str
    score: float
    doc_title: Optional[str] = None
    doc_category: Optional[str] = None
    position: int = 0


class CitationIntegrator:
    """引用整合器 - 负责整合检索结果与生成答案的引用"""

    def __init__(self):
        self.min_citation_score = 0.3
        self.max_citations = 5

    def integrate(
        self,
        answer: str,
        documents: List[Dict[str, Any]],
        scores: Optional[List[float]] = None,
        query: str = ""
    ) -> Dict[str, Any]:
        """
        整合答案与引用

        Args:
            answer: 生成的回答
            documents: 检索到的文档列表
            scores: 各文档的相关性分数
            query: 原始查询（用于引用匹配）

        Returns:
            包含答案和引用信息的字典
        """
        if not documents:
            return {
                "answer": answer,
                "sources": [],
                "has_sources": False,
                "citation_count": 0
            }

        citations = self._extract_citations(documents, scores, query)
        formatted_sources = self._format_sources(citations)

        return {
            "answer": answer,
            "sources": formatted_sources,
            "has_sources": len(citations) > 0,
            "citation_count": len(citations)
        }

    def _extract_citations(
        self,
        documents: List[Dict[str, Any]],
        scores: Optional[List[float]],
        query: str
    ) -> List[Citation]:
        """从文档中提取引用信息"""
        citations = []
        seen_contents = set()

        for i, doc in enumerate(documents):
            if i < len(documents):
                doc_data = documents[i] if isinstance(documents[i], dict) else {"content": getattr(documents[i], "page_content", str(documents[i])), "metadata": getattr(documents[i], "metadata", {})}

                content = doc_data.get("content", "")
                if not content:
                    continue

                content_hash = hash(content[:100])
                if content_hash in seen_contents and len(seen_contents) > 0:
                    continue
                seen_contents.add(content_hash)

                score = scores[i] if scores and i < len(scores) else doc_data.get("score", 0.5)

                if score < self.min_citation_score:
                    continue

                metadata = doc_data.get("metadata", {})
                citation = Citation(
                    document_id=metadata.get("doc_id", metadata.get("doc_id", f"doc_{i}")),
                    chunk_id=metadata.get("chunk_id"),
                    content=self._truncate_content(content),
                    score=score,
                    doc_title=metadata.get("doc_title", metadata.get("title")),
                    doc_category=metadata.get("category"),
                    position=i
                )
                citations.append(citation)

            if len(citations) >= self.max_citations:
                break

        return citations

    def _truncate_content(self, content: str, max_length: int = 200) -> str:
        """截断内容"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _format_sources(self, citations: List[Citation]) -> List[Dict[str, Any]]:
        """格式化引用来源"""
        sources = []
        for i, citation in enumerate(citations):
            source = {
                "index": i + 1,
                "document_id": citation.document_id,
                "chunk_id": citation.chunk_id,
                "content": citation.content,
                "score": round(citation.score, 4),
                "title": citation.doc_title or f"文档{citation.document_id}",
                "category": citation.doc_category or "未分类"
            }
            sources.append(source)
        return sources

    def extract_citations_from_text(
        self,
        text: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        从文本中提取被引用的内容片段

        Args:
            text: 生成的回答文本
            documents: 检索到的文档列表

        Returns:
            被引用的文档列表
        """
        cited_docs = []

        for doc in documents:
            doc_content = doc.get("content", "")
            if not doc_content:
                continue

            if doc_content[:50] in text or any(sent in text for sent in self._split_sentences(doc_content)[:3]):
                cited_docs.append({
                    "document_id": doc.get("metadata", {}).get("doc_id", "unknown"),
                    "content": doc_content,
                    "metadata": doc.get("metadata", {})
                })

        return cited_docs

    def _split_sentences(self, text: str) -> List[str]:
        """简单分句"""
        import re
        sentences = re.split(r'[。！？\n]', text)
        return [s.strip() for s in sentences if s.strip()]

    def create_citation_reference(
        self,
        question: str,
        answer: str,
        documents: List[Dict[str, Any]],
        scores: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        创建完整的引用参考

        Args:
            question: 用户问题
            answer: 生成的回答
            documents: 检索到的文档
            scores: 相关性分数

        Returns:
            包含问题和答案的完整引用信息
        """
        result = self.integrate(answer, documents, scores, question)

        result["question"] = question
        result["retrieved_docs_count"] = len(documents)
        result["cited_docs_count"] = len(result["sources"])

        return result


class CitationTracker:
    """引用追踪器 - 追踪答案中引用的来源"""

    def __init__(self):
        self.tracked_citations: List[Dict[str, Any]] = []

    def track(
        self,
        query: str,
        rewritten_query: str,
        retrieved_docs: List[Dict[str, Any]],
        reranked_docs: List[Dict[str, Any]],
        final_answer: str
    ) -> Dict[str, Any]:
        """
        追踪完整的检索和引用链路

        Args:
            query: 原始问题
            rewritten_query: 改写后的问题
            retrieved_docs: 检索到的文档
            reranked_docs: 重排后的文档
            final_answer: 最终答案

        Returns:
            追踪信息
        """
        integrator = CitationIntegrator()

        return {
            "query": {
                "original": query,
                "rewritten": rewritten_query
            },
            "retrieval": {
                "initial_count": len(retrieved_docs),
                "reranked_count": len(reranked_docs),
                "top_scores": [doc.get("score", 0) for doc in reranked_docs[:3]] if reranked_docs else []
            },
            "citation": integrator.create_citation_reference(
                question=query,
                answer=final_answer,
                documents=reranked_docs
            ),
            "answer_length": len(final_answer)
        }

    def get_citation_stats(self) -> Dict[str, Any]:
        """获取引用统计信息"""
        if not self.tracked_citations:
            return {
                "total_queries": 0,
                "avg_citations": 0,
                "avg_answer_length": 0
            }

        total_citations = sum(c.get("citation_count", 0) for c in self.tracked_citations)
        total_length = sum(c.get("answer_length", 0) for c in self.tracked_citations)

        return {
            "total_queries": len(self.tracked_citations),
            "total_citations": total_citations,
            "avg_citations": round(total_citations / len(self.tracked_citations), 2),
            "avg_answer_length": round(total_length / len(self.tracked_citations), 2)
        }