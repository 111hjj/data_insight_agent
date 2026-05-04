"""
API 模块
========
后端 API 层，负责：
- 路由定义和请求处理
- 业务服务编排
- 中间件配置

这一层只做"搬运工"，核心分析逻辑在 agent/ 模块
"""

from api.services.analysis_service import analysis_service
from api.services.chat_service import chat_service
from api.services.document_service import document_service
