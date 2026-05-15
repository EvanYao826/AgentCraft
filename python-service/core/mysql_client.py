import os
import json
import mysql.connector
from mysql.connector import Error, pooling
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
                password=self.password,
                use_unicode=True,
                charset='utf8mb4',
                time_zone='+08:00'
            )
            if self.connection.is_connected():
                logger.info("Successfully connected to MySQL database")
                # 设置会话时区
                cursor = self.connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
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

    def fetch_one(self, sql: str, params: tuple = None) -> Dict[str, Any]:
        """执行查询并返回单行结果"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            result = cursor.fetchone()
            cursor.close()
            return result
        
        except Error as e:
            logger.error(f"Error fetching one: {e}")
            return None

    def fetch_all(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询并返回所有结果"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            result = cursor.fetchall()
            cursor.close()
            return result
        
        except Error as e:
            logger.error(f"Error fetching all: {e}")
            return []

    def execute(self, sql: str, params: tuple = None) -> int:
        """执行SQL语句（INSERT/UPDATE/DELETE）"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            self.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        
        except Error as e:
            logger.error(f"Error executing SQL: {e}")
            if self.connection:
                self.connection.rollback()
            return 0

# 创建全局实例
mysql_client = MySQLClient()


class UserMemoryClient:
    """用户记忆客户端（连接池版本）"""

    _pool = None

    @classmethod
    def get_pool(cls):
        """获取连接池（懒初始化，单例）"""
        if cls._pool is None:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="user_memory_pool",
                pool_size=10,               # 连接池大小
                pool_reset_session=True,     # 归还连接时重置会话
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USERNAME", "root"),
                password=os.getenv("MYSQL_PASSWORD", "123456"),
                database=os.getenv("MYSQL_DATABASE", "ai_knowledge_db"),
                charset="utf8mb4",
                autocommit=True
            )
        return cls._pool

    def _get_connection(self):
        """从连接池获取连接"""
        return self.get_pool().get_connection()

    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """获取用户所有记忆"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT memory_key, memory_value FROM user_memory WHERE user_id = %s",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()  # 归还到连接池，不是真正关闭

        memory = {}
        for row in rows:
            try:
                memory[row["memory_key"]] = json.loads(row["memory_value"])
            except:
                memory[row["memory_key"]] = row["memory_value"]
        return memory

    def update_user_memory(self, user_id: str, key: str, value: Dict[str, Any],
                           source: str = "agent", confidence: float = 1.0):
        """更新用户记忆（upsert）"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memory (user_id, memory_key, memory_value, source, confidence)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    memory_value = VALUES(memory_value),
                    source = VALUES(source),
                    confidence = VALUES(confidence)
            """, (user_id, key, json.dumps(value, ensure_ascii=False), source, confidence))
            conn.commit()
            cursor.close()
        finally:
            conn.close()  # 归还到连接池

    def batch_get_user_memories(self, user_ids: list) -> Dict[str, Dict]:
        """批量获取多个用户的记忆（减少连接获取次数）"""
        if not user_ids:
            return {}

        conn = self._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            placeholders = ",".join(["%s"] * len(user_ids))
            cursor.execute(
                f"SELECT user_id, memory_key, memory_value FROM user_memory WHERE user_id IN ({placeholders})",
                user_ids
            )
            rows = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()

        result = {uid: {} for uid in user_ids}
        for row in rows:
            try:
                result[row["user_id"]][row["memory_key"]] = json.loads(row["memory_value"])
            except:
                result[row["user_id"]][row["memory_key"]] = row["memory_value"]
        return result


# 创建全局实例
user_memory_client = UserMemoryClient()
