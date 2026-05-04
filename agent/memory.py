"""
对话记忆服务
============
管理多轮对话的上下文信息，让 Agent 能理解之前的对话内容。

实现方式：
- 内存存储（简单直接，适合单机部署）
- 每个对话有唯一 ID
- 支持获取上下文用于 LLM 生成

注意：如果需要多实例部署，可以替换为 Redis 实现
"""

from typing import List, Dict, Optional
from datetime import datetime
import uuid


class MemoryService:
    """对话记忆管理器"""
    
    def __init__(self):
        self._conversations = {}
    
    def create_conversation(self) -> str:
        conv_id = str(uuid.uuid4())
        self._conversations[conv_id] = {
            "id": conv_id,
            "title": "未命名对话",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return conv_id
    
    def add_message(self, conv_id: str, role: str, content: str, file_id: str = None):
        if conv_id not in self._conversations:
            self.create_conversation()
        self._conversations[conv_id]["messages"].append({
            "role": role,
            "content": content,
            "file_id": file_id,
            "timestamp": datetime.now().isoformat()
        })
        self._conversations[conv_id]["updated_at"] = datetime.now().isoformat()
        if role == "user" and len(self._conversations[conv_id]["messages"]) <= 3:
            self._conversations[conv_id]["title"] = content[:30] + "..." if len(content) > 30 else content
    
    def get_context(self, conv_id: str, file_id: str, limit: int = None) -> str:
        if conv_id not in self._conversations:
            return ""
        messages = self._conversations[conv_id]["messages"]
        if limit is not None:
            messages = messages[-limit:]
        context = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            context.append(f"{role}: {msg['content']}")
        return "\n".join(context)
    
    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        return self._conversations.get(conv_id)
    
    def list_conversations(self) -> List[Dict]:
        convs = list(self._conversations.values())
        convs.sort(key=lambda x: x["updated_at"], reverse=True)
        return convs
    
    def delete_conversation(self, conv_id: str) -> bool:
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            return True
        return False


memory_service = MemoryService()
