"""
文档管理路由
============
提供文件上传、列表、删除等API接口

接口列表：
- POST   /upload         - 上传文件
- GET    /list           - 文件列表
- GET    /{document_id}  - 文件详情
- DELETE /{document_id}  - 删除文件
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List
from api.services.document_service import document_service

router = APIRouter()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    size: int
    status: str
    rows: int
    columns: List[str]
    created_at: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传数据文件（CSV/Excel）"""
    try:
        result = await document_service.upload_and_process(file)
        return {"message": "文件上传成功", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(page: int = 1, page_size: int = 20):
    """获取文件列表"""
    try:
        documents = document_service.list_documents(page, page_size)
        return DocumentListResponse(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(document_id: str):
    """获取文件详情"""
    try:
        document = document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="文件不存在")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """删除文件"""
    try:
        success = document_service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="文件不存在")
        return {"message": "文件删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
