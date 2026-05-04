"""
聊天路由
========
提供聊天对话的API接口

接口列表：
- POST /completions - 同步聊天
- POST /stream      - 流式聊天
- GET  /conversations - 对话列表
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from api.services.chat_service import chat_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    file_id: Optional[str] = None
    file_ids: Optional[List[str]] = None
    use_deep_analysis: Optional[bool] = False
    conv_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    content: str
    code: Optional[str] = None
    chart_base64: Optional[str] = None
    error: Optional[str] = None


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """与数据洞察 Agent 对话"""
    try:
        user_message = request.messages[-1].content if request.messages else ""
        if not user_message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        result = chat_service.chat(user_message, file_id=request.file_id, file_ids=request.file_ids, conv_id=request.conv_id)
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations():
    """获取对话列表"""
    return []
