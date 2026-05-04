"""
文档服务
========
处理文件上传、列表、删除等操作

职责：
- 接收上传的 CSV/Excel 文件
- 解析文件内容，提取元数据
- 管理文件的生命周期
"""

import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import UploadFile
import pandas as pd
from utils.logger import logger


class DocumentService:
    """文档管理服务"""
    
    def __init__(self):
        self._documents = {}
    
    async def upload_and_process(self, file: UploadFile) -> Dict[str, Any]:
        """上传并处理数据文件"""
        file_id = str(uuid.uuid4())
        filename = file.filename
        content = await file.read()
        size = len(content)
        
        try:
            file_ext = filename.split(".")[-1].lower()
            if file_ext not in ["csv", "xlsx", "xls"]:
                raise ValueError("只支持 CSV 和 Excel 文件")
            
            file_path = os.path.join("uploads", f"{file_id}.{file_ext}")
            os.makedirs("uploads", exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"文件已保存: {file_path}")
            
            if file_ext == "csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            logger.info(f"文件读取成功，行数: {len(df)}, 列数: {len(df.columns)}")
            
            self._documents[file_id] = {
                "id": file_id,
                "filename": filename,
                "size": size,
                "status": "processed",
                "rows": len(df),
                "columns": df.columns.tolist(),
                "created_at": datetime.now().isoformat()
            }
            
            sample_data = df.head(3).to_dict("records")
            sample_clean = [{k: (v if pd.notna(v) else None) for k, v in row.items()} for row in sample_data]
            
            return {
                "file_id": file_id,
                "filename": filename,
                "rows": len(df),
                "columns": df.columns.tolist(),
                "sample": sample_clean
            }
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            raise
    
    def list_documents(self, page: int, page_size: int) -> List[Dict]:
        docs = list(self._documents.values())
        docs.sort(key=lambda x: x["created_at"], reverse=True)
        offset = (page - 1) * page_size
        return docs[offset:offset + page_size]
    
    def get_document(self, file_id: str) -> Dict:
        return self._documents.get(file_id)
    
    def delete_document(self, file_id: str) -> bool:
        if file_id not in self._documents:
            return False
        doc = self._documents.pop(file_id)
        for ext in ["csv", "xlsx", "xls"]:
            file_path = os.path.join("uploads", f"{file_id}.{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                break
        logger.info(f"文件已删除: {doc['filename']}")
        return True


document_service = DocumentService()
