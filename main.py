"""
数据洞察 Agent
================
一个基于自然语言的数据分析工具，支持多文件分析、图表生成和智能报告

作者: [你的名字]
日期: 2024-05
用途: 课程设计/毕业设计/个人项目展示

项目结构：
- agent/     : AI Agent 核心模块（意图识别、代码生成、图表、记忆）
- api/       : 后端 API 模块（路由、服务、中间件）
- utils/     : 通用工具（日志、生命周期）
- web/       : 前端单页应用
"""

import warnings
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from api.routes import data_analysis, chat, documents, health
from utils.logger import logger
from utils.lifespan import lifespan
from api.middleware.logging_middleware import log_requests

warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

# 加载环境变量
env_mode = os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV", "development")
base_dir = os.path.dirname(__file__)

if env_mode == "production":
    env_file = ".env.production"
else:
    env_file = ".env.development"

env_path = os.path.join(base_dir, env_file)
loaded_file = None
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    loaded_file = env_path
else:
    default_env_path = os.path.join(base_dir, ".env")
    if os.path.exists(default_env_path):
        load_dotenv(default_env_path, override=True)
        loaded_file = default_env_path
    else:
        load_dotenv()
        loaded_file = "默认环境变量"


app = FastAPI(
    title="数据洞察 Agent",
    description="基于自然语言的数据分析与可视化助手",
    version="v1.0.0",
    lifespan=lifespan
)

# CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 请求日志
app.middleware("http")(log_requests)

# 静态文件服务
uploads_dir = os.path.join(base_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

charts_dir = os.path.join(base_dir, "charts")
os.makedirs(charts_dir, exist_ok=True)
app.mount("/charts", StaticFiles(directory=charts_dir), name="charts")

reports_dir = os.path.join(base_dir, "reports")
os.makedirs(reports_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")

web_dir = os.path.join(base_dir, "web")
if os.path.exists(web_dir):
    app.mount("/web", StaticFiles(directory=web_dir), name="web")

# 注册路由
app.include_router(chat.router, prefix="/api/chat", tags=["聊天"])
app.include_router(documents.router, prefix="/api/documents", tags=["文档管理"])
app.include_router(data_analysis.router, prefix="/api/data-analysis", tags=["数据分析"])
app.include_router(health.router, tags=["健康检查"])


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    index_path = os.path.join(base_dir, "web", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "数据洞察 Agent - 基于自然语言的数据分析与可视化助手", "version": "v1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(
        f"未处理的异常: {str(exc)}",
        exc_info=True,
        extra={"path": str(request.url.path), "method": request.method}
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    is_production = env_mode == "production"
    env_name = "生产环境" if is_production else "开发环境"
    print(f"\n环境: {env_name}")
    print(f"环境变量文件: {loaded_file}\n")
    
    if is_production:
        workers = int(os.getenv("UVICORN_WORKERS", "8"))
        print(f"Worker数量: {workers}")
    else:
        workers = 1
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        workers=workers if is_production else None,
        reload=not is_production,
        log_config=None,
        timeout_keep_alive=900,
        limit_concurrency=2000,
    )
