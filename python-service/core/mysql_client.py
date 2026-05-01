import os
import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MySQLClient:
    """MySQL 数据库客户端"""
    
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST", "localhost")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.database = os.getenv("MYSQL_DATABASE", "ai_knowledge_db")
        self.username = os.getenv("MYSQL_USERNAME", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "123456")
        self.connection = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            if self.connection.is_connected():
                logger.info("Successfully connected to MySQL database")
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")
    
    def insert_chunks(self, doc_id: int, chunks: List[Dict[str, Any]]):
        """批量插入 chunks 到 knowledge_chunk 表"""
        if not chunks:
            return 0
        
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # 先删除该文档已有的 chunks（避免重复）
            delete_sql = "DELETE FROM knowledge_chunk WHERE doc_id = %s"
            cursor.execute(delete_sql, (doc_id,))
            
            # 批量插入新 chunks
            insert_sql = """
                INSERT INTO knowledge_chunk (doc_id, chunk_index, chunk_text, create_time)
                VALUES (%s, %s, %s, NOW())
            """
            
            data = [
                (doc_id, chunk.get('chunk_index', i), chunk.get('page_content', ''),)
                for i, chunk in enumerate(chunks)
            ]
            
            cursor.executemany(insert_sql, data)
            self.connection.commit()
            
            inserted_count = cursor.rowcount
            logger.info(f"Inserted {inserted_count} chunks for doc_id {doc_id}")
            
            cursor.close()
            return inserted_count
        
        except Error as e:
            logger.error(f"Error inserting chunks: {e}")
            if self.connection:
                self.connection.rollback()
            return 0
    
    def get_chunk_count(self, doc_id: int = None) -> int:
        """获取 chunk 数量"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            if doc_id:
                sql = "SELECT COUNT(*) FROM knowledge_chunk WHERE doc_id = %s"
                cursor.execute(sql, (doc_id,))
            else:
                sql = "SELECT COUNT(*) FROM knowledge_chunk"
                cursor.execute(sql)
            
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else 0
        
        except Error as e:
            logger.error(f"Error getting chunk count: {e}")
            return 0

# 创建全局实例
mysql_client = MySQLClient()
