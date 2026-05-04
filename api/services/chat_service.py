"""
聊天服务
========
处理聊天请求，调用 agent 进行分析

职责：
- 管理当前选择的文件
- 根据文件数量选择单文件/多文件分析
- 格式化返回结果
"""

import json
from typing import Dict, Any, List, Optional
from api.services.analysis_service import analysis_service


class ChatService:
    """聊天服务"""
    
    def __init__(self):
        self.current_file_id = None
        self.current_file_ids = []
    
    def chat(self, query: str, file_id: str = None, file_ids: List[str] = None, conv_id: str = None) -> Dict[str, Any]:
        """处理聊天请求"""
        if file_ids and len(file_ids) > 0:
            self.current_file_ids = file_ids
            self.current_file_id = file_ids[0]
        elif file_id:
            self.current_file_id = file_id
            self.current_file_ids = [file_id]
        
        if not self.current_file_ids:
            return {'success': False, 'content': "", 'error': "请先上传数据文件"}
        
        if len(self.current_file_ids) == 1:
            return analysis_service.analyze(self.current_file_ids[0], query)
        else:
            dfs = {}
            for i, fid in enumerate(self.current_file_ids):
                df = analysis_service._load_dataframe(fid)
                if df is not None:
                    dfs[f"df{i+1}"] = df
            if not dfs:
                return {'success': False, 'content': "", 'error': "无法加载任何数据文件"}
            return analysis_service.analyze_multi(query, dfs)


chat_service = ChatService()
