"""
数据分析路由
============
提供数据分析相关的API接口

接口列表：
- POST /analyze          - 快速分析
- GET  /file/{id}/info   - 文件信息
- GET  /file/{id}/preview - 文件预览
- POST /deep-analysis    - 深度分析（SSE流式）
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from api.services.analysis_service import analysis_service
import json

router = APIRouter()


class AnalyzeRequest(BaseModel):
    query: str
    file_id: str


class AnalyzeResponse(BaseModel):
    success: bool
    output: Optional[str] = None
    code: Optional[str] = None
    chart_path: Optional[str] = None
    error: Optional[str] = None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_data(request: AnalyzeRequest):
    """快速分析接口"""
    try:
        result = analysis_service.analyze(request.file_id, request.query)
        if result.get("chart_path"):
            result["chart_path"] = f"/charts/{result['chart_path'].split('/')[-1]}"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}/info")
async def get_file_info(file_id: str):
    """获取文件基本信息"""
    try:
        info = analysis_service.get_file_info(file_id)
        if not info:
            raise HTTPException(status_code=404, detail="文件不存在")
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}/preview")
async def get_file_preview(file_id: str):
    """获取文件预览数据"""
    try:
        info = analysis_service.get_file_info(file_id)
        if not info:
            raise HTTPException(status_code=404, detail="文件不存在")
        return {
            'success': True,
            'rows': info['rows'],
            'columns': info['columns'],
            'dtypes': info['dtypes'],
            'sample': info['sample']
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DeepAnalysisRequest(BaseModel):
    message: str
    file_id: Optional[str] = None
    file_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None


async def deep_analysis_stream(request: DeepAnalysisRequest):
    """流式深度分析"""
    try:
        if request.file_ids and len(request.file_ids) > 0:
            file_ids = request.file_ids
        elif request.file_id:
            file_ids = [request.file_id]
        else:
            yield json.dumps({'type': 'error', 'error': '请选择至少一个数据文件'}) + '\n'
            return
        
        is_multi_file_task = len(file_ids) > 1
        
        if len(file_ids) == 1 or not is_multi_file_task:
            primary_file_id = file_ids[0]
            df = analysis_service._load_dataframe(primary_file_id)
            if df is None:
                yield json.dumps({'type': 'error', 'error': '无法加载数据文件'}) + '\n'
                return
            
            for chunk in analysis_service.deep_analyze(primary_file_id, request.message, request.conversation_id):
                yield chunk + '\n'
        else:
            dfs = {}
            for i, fid in enumerate(file_ids):
                df = analysis_service._load_dataframe(fid)
                if df is not None:
                    dfs[f"df{i+1}"] = df
            
            if not dfs:
                yield json.dumps({'type': 'error', 'error': '无法加载任何数据文件'}) + '\n'
                return
            
            result = analysis_service.analyze_multi(request.message, dfs)
            
            if result.get('success'):
                content = result.get('output', '')
                yield json.dumps({'type': 'agent_result', 'content': content}) + '\n'
            else:
                yield json.dumps({'type': 'error', 'error': result.get('error', '分析失败')}) + '\n'
            
            yield json.dumps({'type': 'done'}) + '\n'
        
    except Exception as e:
        yield json.dumps({'type': 'error', 'error': str(e)}) + '\n'


@router.post("/deep-analysis")
async def deep_analysis(request: DeepAnalysisRequest):
    """深度分析接口（SSE流式响应）"""
    return StreamingResponse(
        deep_analysis_stream(request),
        media_type="text/event-stream"
    )
