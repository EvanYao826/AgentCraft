from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量 (确保加载当前目录下的 .env 文件)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from api.routes import router
from api.agent_routes import router as agent_router
import tools

app = FastAPI(title="AI Knowledge System - Python Service")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# 注册路由
app.include_router(router, prefix="/api")
app.include_router(agent_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "AI Knowledge System Python Service is running"}

# 健康检查端点
@app.get("/health")
async def health_check():
    import os
    # 检查环境变量
    has_api_key = os.getenv("DASHSCOPE_API_KEY") is not None
    use_milvus = os.getenv("USE_MILVUS", "true").lower() == "true"
    milvus_host = os.getenv("MILVUS_HOST", "localhost")
    milvus_port = os.getenv("MILVUS_PORT", "19530")

    # 检查向量存储
    vector_store_info = {}
    if use_milvus:
        vector_store_info = {
            "type": "Milvus",
            "host": milvus_host,
            "port": milvus_port,
            "status": "configured"
        }
    else:
        vector_store_dir = os.path.join(os.getcwd(), "faiss_index")
        vector_store_exists = os.path.exists(vector_store_dir)
        vector_store_info = {
            "type": "FAISS",
            "exists": vector_store_exists,
            "directory": vector_store_dir
        }

    return {
        "status": "healthy",
        "environment": {
            "has_dashscope_api_key": has_api_key,
            "use_milvus": use_milvus
        },
        "vector_store": vector_store_info
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
