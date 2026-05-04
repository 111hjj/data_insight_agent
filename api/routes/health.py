"""
健康检查路由
============
用于监控服务是否正常运行
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "数据洞察 Agent",
        "version": "v1.0.0"
    }
