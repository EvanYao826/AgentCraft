import os
import shutil
from typing import List, Optional, Dict, Any
from langchain_community.vectorstores import FAISS, Milvus
from langchain_community.embeddings import DashScopeEmbeddings, HuggingFaceEmbeddings
from langchain_core.documents import Document
from pymilvus import connections, utility
from core.reranker import create_reranker, BaseReranker
from core.config import config


class VectorStoreManager:
    def __init__(self, persist_directory=None, use_milvus=None):
        """
        初始化向量存储管理器

        Args:
            persist_directory: FAISS持久化目录（仅当use_milvus=False时使用）
            use_milvus: 是否使用Milvus（默认从环境变量读取，默认值为True）
        """
        # 从环境变量读取持久化目录，默认值为./faiss_index
        self.persist_directory = persist_directory or config.VECTOR_STORE_PERSIST_DIR
        # 从环境变量读取use_milvus配置，如果未设置则默认为True
        if use_milvus is None:
            use_milvus = config.USE_MILVUS
        self.use_milvus = use_milvus
        # 从环境变量读取集合名称，默认值为ai_knowledge_collection
        self.collection_name = config.VECTOR_STORE_COLLECTION_NAME
        self.vector_store = None

        # 初始化Reranker
        self._init_reranker()

        # 根据 EMBEDDING_MODEL 配置选择 Embedding 模型
        embedding_model = config.EMBEDDING_MODEL.lower()

        if embedding_model == "local":
            # 使用本地中文 Embedding 模型（如 BAAI/bge-small-zh-v1.5）
            local_model = config.LOCAL_EMBEDDING_MODEL
            config.logger.info(f"Using local HuggingFace Embeddings ({local_model})")
            self.embeddings = HuggingFaceEmbeddings(model_name=local_model)
        else:
            # 默认使用阿里云 DashScope Embeddings (text-embedding-v1)
            api_key = config.DASHSCOPE_API_KEY
            if api_key:
                config.logger.info("Using DashScope Embeddings (text-embedding-v1)")
                self.embeddings = DashScopeEmbeddings(
                    model="text-embedding-v1",
                    dashscope_api_key=api_key
                )
            else:
                config.logger.warning("DASHSCOPE_API_KEY not found. Falling back to local HuggingFace Embeddings.")
                self.embeddings = HuggingFaceEmbeddings(model_name=config.LOCAL_EMBEDDING_MODEL)

        # 根据配置选择向量数据库
        if self.use_milvus:
            self._init_milvus()
        else:
            self._init_faiss()

    def _init_reranker(self):
        """初始化Reranker"""
        reranker_type = config.RERANKER_TYPE
        if reranker_type == "none":
            self.reranker = None
            config.logger.info("Reranker is disabled")
            return

        try:
            self.reranker = create_reranker(reranker_type)
            config.logger.info(f"Reranker initialized: {reranker_type}")
        except Exception as e:
            config.logger.error(f"Failed to initialize reranker: {e}")
            self.reranker = None

    def _init_milvus(self):
        """初始化Milvus连接和集合"""
        try:
            # Milvus连接配置
            milvus_host = config.MILVUS_HOST
            milvus_port = config.MILVUS_PORT

            config.logger.info(f"Connecting to Milvus at {milvus_host}:{milvus_port}")
            connections.connect(alias="default", host=milvus_host, port=milvus_port)

            # 检查连接
            if not connections.has_connection("default"):
                raise ConnectionError("Failed to connect to Milvus")

            config.logger.info("Successfully connected to Milvus")

            # 初始化Milvus向量存储
            self.vector_store = Milvus(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                connection_args={
                    "host": milvus_host,
                    "port": milvus_port,
                    "alias": "default"
                },
                # 自动创建集合（如果不存在）
                auto_id=True
            )

            config.logger.info(f"Milvus collection '{self.collection_name}' ready")

        except Exception as e:
            config.logger.error(f"Failed to initialize Milvus: {e}")
            config.logger.info("Falling back to FAISS...")
            self.use_milvus = False
            self._init_faiss()

    def _init_faiss(self):
        """
        初始化 FAISS 向量存储（作为 Milvus 的 fallback）
        """
        config.logger.info("Using FAISS vector store (fallback mode)")
        if os.path.exists(self.persist_directory):
            try:
                self.vector_store = FAISS.load_local(self.persist_directory, self.embeddings, allow_dangerous_deserialization=True)
                config.logger.info(f"Loaded existing FAISS index from {self.persist_directory}")
            except Exception as e:
                config.logger.error(f"Error loading existing FAISS index: {e}")
                config.logger.info("This may be caused by embedding model change (dimension mismatch). Re-initializing empty FAISS vector store...")
                # Backup old index just in case
                if os.path.exists(self.persist_directory + "_backup"):
                    shutil.rmtree(self.persist_directory + "_backup")
                shutil.move(self.persist_directory, self.persist_directory + "_backup")
                self.vector_store = None
        else:
            self.vector_store = None
            config.logger.info("No existing FAISS index found, will create new one when needed")

    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量数据库
        """
        if not documents:
            return

        if self.vector_store is None:
            if self.use_milvus:
                # Milvus会自动创建集合
                milvus_host = config.MILVUS_HOST
                milvus_port = config.MILVUS_PORT
                self.vector_store = Milvus.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    collection_name=self.collection_name,
                    connection_args={
                        "host": milvus_host,
                        "port": milvus_port,
                        "alias": "default"
                    }
                )
                config.logger.info(f"Created Milvus collection '{self.collection_name}' with {len(documents)} documents")
            else:
                # FAISS
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                self.vector_store.save_local(self.persist_directory)
                config.logger.info(f"Created FAISS index with {len(documents)} documents")
        else:
            # 添加文档到现有存储
            if self.use_milvus:
                # Milvus添加文档
                self.vector_store.add_documents(documents)
                config.logger.info(f"Added {len(documents)} documents to Milvus")
            else:
                # FAISS添加文档
                self.vector_store.add_documents(documents)
                self.vector_store.save_local(self.persist_directory)
                config.logger.info(f"Added {len(documents)} documents to FAISS")

    def search(self, query: str, k: int = 3, filter_dict: Optional[Dict[str, Any]] = None, similarity_threshold: float = 0.75, use_rerank: bool = True) -> List[Document]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件（仅Milvus支持）
            similarity_threshold: 相似度阈值，只有相似度大于此值的文档才返回（0.0-1.0）
            use_rerank: 是否使用Rerank进行结果重排序
        """
        import time
        start_time = time.time()
        
        if self.vector_store is None:
            config.logger.info(f"Search completed in {time.time() - start_time:.4f}s, no vector store available")
            return []

        try:
            # 初始检索数量应该比最终返回的多，以便Rerank有足够的候选
            initial_k = k * 3 if use_rerank and self.reranker else k

            search_start = time.time()
            if self.use_milvus and filter_dict:
                # Milvus支持过滤查询
                docs_with_scores = self.vector_store.similarity_search_with_score(query, k=initial_k, filter=filter_dict)
            else:
                # FAISS或无条件查询
                docs_with_scores = self.vector_store.similarity_search_with_score(query, k=initial_k)
            search_time = time.time() - search_start
            config.logger.info(f"Vector search completed in {search_time:.4f}s, found {len(docs_with_scores) if isinstance(docs_with_scores, list) else 0} documents")

            # 提取文档
            if isinstance(docs_with_scores, list):
                if len(docs_with_scores) > 0 and isinstance(docs_with_scores[0], tuple):
                    # (doc, score) 格式
                    docs = [doc for doc, score in docs_with_scores]
                else:
                    docs = docs_with_scores
            else:
                docs = docs_with_scores

            # 如果没有启用Rerank或没有Reranker，直接返回初步检索结果
            if not use_rerank or not self.reranker:
                # 过滤掉相似度低于阈值的文档
                filtered_docs = []
                for i, (doc, score) in enumerate(docs_with_scores):
                    if score >= similarity_threshold:
                        filtered_docs.append(doc)
                        config.logger.debug(f"Document similarity score: {score}")
                    else:
                        config.logger.debug(f"Document filtered out due to low similarity: {score}")
                config.logger.info(f"Search completed in {time.time() - start_time:.4f}s, returning {len(filtered_docs)} documents")
                return filtered_docs

            # 使用Rerank进行重排序
            try:
                rerank_start = time.time()
                rerank_results = self.reranker.rerank(query, docs, top_k=k)
                rerank_time = time.time() - rerank_start
                config.logger.info(f"Rerank completed in {rerank_time:.4f}s, top {len(rerank_results)} results")

                # 提取重排序后的文档
                reranked_docs = [r.document for r in rerank_results]

                # Rerank已经按相关性排序，这里不再应用similarity_threshold
                # 但如果需要可以在这里添加额外的过滤逻辑
                config.logger.info(f"Search completed in {time.time() - start_time:.4f}s, returning {len(reranked_docs)} documents")

                return reranked_docs

            except Exception as rerank_error:
                config.logger.error(f"Rerank failed: {rerank_error}, falling back to vector search")
                # Rerank失败时，回退到原始的向量搜索结果
                filtered_docs = []
                for doc, score in docs_with_scores:
                    if score >= similarity_threshold:
                        filtered_docs.append(doc)
                config.logger.info(f"Search completed in {time.time() - start_time:.4f}s (Rerank failed, fallback to vector search), returning {len(filtered_docs)} documents")
                return filtered_docs

        except Exception as e:
            config.logger.error(f"Search error: {e}")
            # 如果 similarity_search_with_score 失败，回退到普通搜索
            try:
                fallback_start = time.time()
                if self.use_milvus and filter_dict:
                    result = self.vector_store.similarity_search(query, k=k, filter=filter_dict)
                else:
                    result = self.vector_store.similarity_search(query, k=k)
                fallback_time = time.time() - fallback_start
                config.logger.info(f"Fallback search completed in {fallback_time:.4f}s, returning {len(result)} documents")
                return result
            except Exception as e2:
                config.logger.error(f"Fallback search also failed: {e2}")
                config.logger.info(f"Search completed in {time.time() - start_time:.4f}s (all searches failed), returning empty results")
                return []

    def delete_document(self, doc_id: int):
        """
        根据 doc_id 删除文档向量

        Milvus: 支持高效删除
        FAISS: 标记删除（实际需要重建索引）
        """
        if self.vector_store is None:
            config.logger.warning(f"No vector store available, cannot delete doc_id: {doc_id}")
            return

        if self.use_milvus:
            # Milvus删除逻辑
            try:
                config.logger.info(f"Deleting document with doc_id: {doc_id} from Milvus")

                # 构建删除表达式（使用类型转换确保安全性）
                if not isinstance(doc_id, int):
                    raise ValueError(f"doc_id must be an integer, got {type(doc_id)}")
                delete_expr = f'doc_id in [{doc_id}]'

                # 执行删除
                result = self.vector_store.delete(expr=delete_expr)
                config.logger.info(f"Milvus delete result: {result}")

                # 可选：压缩集合以释放空间
                # utility.compact(collection_name=self.collection_name)

                config.logger.info(f"Successfully deleted document {doc_id} from Milvus")

            except Exception as e:
                config.logger.error(f"Failed to delete document from Milvus: {e}")
                # 尝试其他删除方法
                self._delete_document_fallback(doc_id)

        else:
            # FAISS删除逻辑（效率较低）
            config.logger.info(f"Deleting document with doc_id: {doc_id} from FAISS")
            self._delete_document_faiss(doc_id)

    def _delete_document_fallback(self, doc_id: int):
        """备用删除方法：通过查询找到ID然后删除"""
        try:
            # 先搜索包含该doc_id的文档
            filter_dict = {"doc_id": doc_id}
            docs_to_delete = self.search("", k=1000, filter_dict=filter_dict)

            if not docs_to_delete:
                config.logger.info(f"No documents found with doc_id: {doc_id}")
                return

            # 提取文档ID（假设metadata中有唯一ID）
            ids_to_delete = []
            for doc in docs_to_delete:
                if 'chunk_id' in doc.metadata:
                    ids_to_delete.append(doc.metadata['chunk_id'])

            if ids_to_delete:
                # 执行删除
                self.vector_store.delete(ids=ids_to_delete)
                config.logger.info(f"Deleted {len(ids_to_delete)} chunks for doc_id {doc_id}")
            else:
                config.logger.info(f"No deletable chunks found for doc_id {doc_id}")

        except Exception as e:
            config.logger.error(f"Fallback delete failed: {e}")

    def _delete_document_faiss(self, doc_id: int):
        """FAISS删除实现（需要重建索引）"""
        try:
            # 找到所有 metadata['doc_id'] == doc_id 的 ID
            ids_to_delete = []
            for doc_uuid, doc in self.vector_store.docstore._dict.items():
                if doc.metadata.get('doc_id') == doc_id:
                    ids_to_delete.append(doc_uuid)

            if ids_to_delete:
                # FAISS的delete方法可能不彻底，这里尝试删除
                self.vector_store.delete(ids_to_delete)
                self.vector_store.save_local(self.persist_directory)
                config.logger.info(f"Deleted {len(ids_to_delete)} chunks for doc_id {doc_id}")

                # 建议：定期重建FAISS索引以提高效率
                if len(ids_to_delete) > 100:
                    config.logger.warning("Large deletion in FAISS. Consider rebuilding index for better performance.")
            else:
                config.logger.info(f"No chunks found for doc_id {doc_id}")

        except Exception as e:
            config.logger.error(f"Failed to delete document from FAISS: {e}")

    def delete_collection(self):
        """
        删除整个向量库 (慎用)
        """
        if self.use_milvus:
            try:
                # 删除Milvus集合
                utility.drop_collection(self.collection_name)
                config.logger.info(f"Successfully deleted Milvus collection '{self.collection_name}'")
            except Exception as e:
                config.logger.error(f"Failed to delete Milvus collection: {e}")
        else:
            # 删除FAISS目录
            if os.path.exists(self.persist_directory):
                shutil.rmtree(self.persist_directory)
            self.vector_store = None
            config.logger.info("Successfully deleted FAISS collection")

    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计信息"""
        stats = {
            "using_milvus": self.use_milvus,
            "collection_name": self.collection_name if self.use_milvus else None,
            "persist_directory": self.persist_directory if not self.use_milvus else None,
        }

        if self.use_milvus and self.vector_store:
            try:
                # 获取Milvus集合信息
                collection_stats = utility.get_collection_stats(self.collection_name)
                stats.update({
                    "row_count": collection_stats.get("row_count", 0),
                    "partitions": collection_stats.get("partitions", []),
                })
            except Exception as e:
                stats["error"] = f"Failed to get Milvus stats: {e}"
        elif not self.use_milvus and self.vector_store:
            # FAISS统计
            stats["doc_count"] = len(self.vector_store.docstore._dict) if hasattr(self.vector_store, 'docstore') else 0

        return stats

    def migrate_faiss_to_milvus(self):
        """将FAISS数据迁移到Milvus"""
        if not self.use_milvus or self.vector_store is None:
            config.logger.warning("Cannot migrate: not using Milvus or no vector store")
            return False

        try:
            config.logger.info("Starting migration from FAISS to Milvus...")

            # 1. 加载FAISS数据
            if os.path.exists(self.persist_directory):
                faiss_store = FAISS.load_local(self.persist_directory, self.embeddings, allow_dangerous_deserialization=True)

                # 2. 提取所有文档
                all_docs = []
                for doc_uuid, doc in faiss_store.docstore._dict.items():
                    all_docs.append(doc)

                # 3. 添加到Milvus
                if all_docs:
                    self.add_documents(all_docs)
                    config.logger.info(f"Migrated {len(all_docs)} documents from FAISS to Milvus")

                    # 4. 备份原FAISS数据
                    backup_dir = self.persist_directory + "_migrated_backup"
                    if os.path.exists(backup_dir):
                        shutil.rmtree(backup_dir)
                    shutil.move(self.persist_directory, backup_dir)
                    config.logger.info(f"Backed up FAISS data to {backup_dir}")

                    return True

            return False

        except Exception as e:
            config.logger.error(f"Migration failed: {e}")
            return False


# 创建单例实例
vector_store_manager = VectorStoreManager()

# 导出（保持兼容性，同时保留完整管理器）
vector_store = vector_store_manager
