"""
请求日志中间件
==============
记录每个HTTP请求的方法、路径和耗时
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.2f}s")
        return response


def log_requests(request, call_next):
    """兼容旧版中间件接口"""
    start_time = time.time()
    response = call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.2f}s")
    return response
