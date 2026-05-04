"""应用生命周期管理"""
from utils.logger import logger

async def lifespan(app):
    """应用启动和关闭时的处理"""
    logger.info("=== 数据洞察 Agent 启动 ===")
    
    yield
    
    logger.info("=== 数据洞察 Agent 关闭 ===")