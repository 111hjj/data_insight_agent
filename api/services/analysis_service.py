"""
数据分析服务（薄层）
====================
后端服务层，负责：
- 文件加载和管理
- 调用 agent 模块进行分析
- 结果格式化

核心智能逻辑在 agent/analyzer.py，这里只做调度
"""

import os
import json
import pandas as pd
from typing import Dict, Any, Optional, List
from utils.logger import logger
from agent.analyzer import analyzer
from agent.memory import memory_service
from agent.code_generator import code_generator


class AnalysisService:
    """数据分析服务 - 连接后端API和AI Agent"""
    
    def _load_dataframe(self, file_id: str) -> Optional[pd.DataFrame]:
        """根据文件ID加载数据"""
        for ext in [".csv", ".xlsx", ".xls"]:
            file_path = f"uploads/{file_id}{ext}"
            if os.path.exists(file_path):
                try:
                    if ext == ".csv":
                        return pd.read_csv(file_path)
                    else:
                        return pd.read_excel(file_path)
                except Exception as e:
                    logger.error(f"加载数据文件失败: {e}")
                    return None
        return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文件基本信息"""
        df = self._load_dataframe(file_id)
        if df is None:
            return None
        df_cleaned = df.fillna('').replace([float('inf'), float('-inf')], '')
        return {
            'file_id': file_id,
            'rows': len(df),
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'memory_usage': df.memory_usage().sum() / 1024 / 1024,
            'sample': df_cleaned.to_dict("records")
        }
    
    def analyze(self, file_id: str, query: str) -> Dict[str, Any]:
        """快速分析（单次查询，无上下文）"""
        df = self._load_dataframe(file_id)
        if df is None:
            return {'success': False, 'error': "文件不存在或无法加载"}
        
        code = analyzer.generate_code_with_llm(query, df)
        if not code:
            code = code_generator.generate_code(query, df)
        if not code:
            return {'success': False, 'error': "无法生成代码"}
        
        result = analyzer.execute_code(code, df)
        if result['success']:
            result['code'] = code
        return result
    
    def deep_analyze(self, file_id: str, query: str, conversation_id: Optional[str] = None):
        """深度分析（支持对话上下文，流式输出）"""
        if not conversation_id:
            conversation_id = memory_service.create_conversation()
        
        memory_service.add_message(conversation_id, "user", query, file_id)
        
        df = self._load_dataframe(file_id)
        if df is None:
            error_msg = '文件不存在或无法加载'
            memory_service.add_message(conversation_id, "assistant", error_msg, file_id)
            yield json.dumps({'type': 'error', 'error': error_msg})
            return
        
        context = memory_service.get_context(conversation_id, file_id)
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        intent = analyzer.detect_intent(query)
        
        if intent == 'chart':
            chart_type = 'bar'
            chart_name = '柱状图'
            x_column = None
            y_column = None
            
            if '折线' in query or '趋势' in query:
                chart_type = 'line'; chart_name = '折线图'
            elif '饼' in query:
                chart_type = 'pie'; chart_name = '饼图'
            elif '直方' in query or '分布' in query:
                chart_type = 'hist'; chart_name = '直方图'
            
            match = re.search(r'横轴[:：]\s*([^，,；;\s]+)', query)
            if match: x_column = match.group(1).strip()
            match = re.search(r'纵轴[:：]\s*([^，,；;\s]+)', query)
            if match: y_column = match.group(1).strip()
            if not y_column and numeric_cols:
                y_column = numeric_cols[0]
            
            yield json.dumps({'type': 'planning', 'analysis_type': '图表生成', 'reasoning': f'创建{chart_name}展示数据...'})
            chart_path = analyzer.generate_chart(df, y_column, chart_type, x_column)
            answer = f"📊 **图表已生成**\n\n![图表](/charts/{chart_path.split('/')[-1]})"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'agent_result', 'title': '📊 数据可视化图表', 'content': answer, 'chart_path': f"/charts/{chart_path.split('/')[-1]}"})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'report':
            yield json.dumps({'type': 'planning', 'analysis_type': '生成报告', 'reasoning': '正在进行全面的数据洞察分析...'})
            
            columns_info = "\n".join([f"- {col}: {str(df[col].dtype)}" for col in df.columns])
            yield json.dumps({'type': 'agent_result', 'title': '📋 数据结构分析', 'content': f"数据维度: {len(df)} 行 x {len(df.columns)} 列\n\n字段信息:\n{columns_info}"})
            
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            missing_counts = df.isnull().sum()
            missing_info = "\n".join([f"- {col}: {missing_counts[col]} 个缺失值" for col in df.columns if missing_counts[col] > 0])
            if not missing_info:
                missing_info = "无缺失值，数据完整性良好"
            
            quality = f"字段类型分析:\n- 数值型字段: {len(numeric_cols)} 个 ({', '.join(numeric_cols)})\n- 类别型字段: {len(categorical_cols)} 个 ({', '.join(categorical_cols)})\n\n缺失值检测:\n{missing_info}"
            yield json.dumps({'type': 'agent_result', 'title': '✅ 数据质量报告', 'content': quality})
            yield json.dumps({'type': 'agent_result', 'title': '📊 描述统计', 'content': df.describe().to_string()})
            
            if len(numeric_cols) >= 2:
                yield json.dumps({'type': 'agent_result', 'title': '🔗 相关性分析', 'content': f"数值字段相关系数矩阵:\n{df[numeric_cols].corr().to_string()}"})
            
            anomaly_report = analyzer.detect_anomalies(df, numeric_cols)
            yield json.dumps({'type': 'agent_result', 'title': '⚠️ 异常检测报告', 'content': anomaly_report})
            
            trend_report = analyzer.trend_analysis(df, numeric_cols)
            yield json.dumps({'type': 'agent_result', 'title': '📈 趋势分析', 'content': trend_report})
            
            predict_report = analyzer.predict_analysis(df, numeric_cols)
            yield json.dumps({'type': 'agent_result', 'title': '🔮 预测分析', 'content': predict_report})
            
            full_report = analyzer.generate_report(df, numeric_cols, anomaly_report, trend_report, predict_report)
            memory_service.add_message(conversation_id, "assistant", full_report, file_id)
            
            report_file_path = analyzer.save_report(full_report, file_id)
            report_filename = report_file_path.split("/")[-1]
            content_with_export = f"{full_report}\n\n---\n\n📥 **导出选项**\n\n您可以通过以下链接下载报告：\n- [下载 Markdown 报告](/reports/{report_filename})"
            yield json.dumps({'type': 'agent_result', 'title': '📋 综合分析报告', 'content': content_with_export, 'report_path': f"/reports/{report_filename}"})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'anomaly':
            answer = f"⚠️ **异常检测结果**\n\n{analyzer.detect_anomalies(df, numeric_cols)}"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'trend':
            answer = f"📈 **趋势分析结果**\n\n{analyzer.trend_analysis(df, numeric_cols)}"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'predict':
            answer = f"🔮 **预测分析结果**\n\n{analyzer.predict_analysis(df, numeric_cols)}"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'correlation':
            if len(numeric_cols) >= 2:
                answer = f"🔗 **相关性分析**\n\n数值字段相关系数矩阵:\n{df[numeric_cols].corr().to_string()}"
            else:
                answer = "相关性分析需要至少2个数值字段"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'describe':
            answer = f"📊 **描述统计**\n\n{df.describe().to_string()}"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'preview':
            answer = f"👀 **数据预览**\n\n数据维度: {len(df)} 行 × {len(df.columns)} 列\n\n{df.head().to_string()}"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        if intent == 'history':
            conv = memory_service.get_conversation(conversation_id)
            if conv and len(conv["messages"]) > 1:
                user_qs = [f"- {msg['content']}" for msg in conv["messages"][:-1] if msg["role"] == "user"]
                answer = f"📜 您之前问过:\n\n" + "\n".join(user_qs) if user_qs else "还没有找到您之前的问题记录。"
            else:
                answer = "这是您的第一个问题，还没有对话历史。"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        # 通用分析：行数、列数等简单查询
        simple_patterns = [
            (r'多少行|行数|记录数', f"数据集中包含 {len(df)} 行记录"),
            (r'多少列|列数|字段数', f"数据集中包含 {len(df.columns)} 列字段"),
            (r'行.*列|数据维度', f"数据维度: {len(df)} 行 × {len(df.columns)} 列"),
            (r'列名|字段名|有哪些列', "字段列表:\n" + "\n".join([f"- {col}" for col in df.columns])),
            (r'数据类型|字段类型', "字段类型:\n" + "\n".join([f"- {col}: {str(df[col].dtype)}" for col in df.columns])),
            (r'空值|缺失值', "缺失值检测:\n" + ("\n".join([f"- {col}: {df[col].isnull().sum()} 个缺失值" for col in df.columns if df[col].isnull().sum() > 0]) or "无缺失值，数据完整性良好")),
        ]
        
        for pattern, answer in simple_patterns:
            if re.search(pattern, query):
                memory_service.add_message(conversation_id, "assistant", answer, file_id)
                yield json.dumps({'type': 'direct_answer', 'content': answer})
                yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
                return
        
        if not analyzer.is_data_question(query, df.columns.tolist()):
            answer = f"我是数据洞察 Agent，专注于数据分析任务。您的问题「{query}」似乎不是数据分析相关的问题。\n\n我可以帮助您进行：数据预览、描述统计、图表生成、异常检测、趋势分析、预测分析、生成报告等。"
            memory_service.add_message(conversation_id, "assistant", answer, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': answer})
            yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
            return
        
        code = analyzer.generate_code_with_llm(query, df, context)
        if not code:
            code = code_generator.generate_code(query, df)
        result = analyzer.execute_code(code, df)
        
        if result['success']:
            content = result.get('output', '')
            if result.get('chart_path'):
                content += '\n\n![图表](/charts/' + result['chart_path'].split('/')[-1] + ')'
            content += '\n\n执行代码:\n' + code
            memory_service.add_message(conversation_id, "assistant", content, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': content})
        else:
            content = f"执行错误: {result.get('error', '未知错误')}"
            memory_service.add_message(conversation_id, "assistant", content, file_id)
            yield json.dumps({'type': 'direct_answer', 'content': content})
        
        yield json.dumps({'type': 'done', 'conversation_id': conversation_id})
    
    def analyze_multi(self, query: str, dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """多文件分析"""
        if not dfs:
            return {'success': False, 'error': '没有提供任何数据文件'}
        
        if '对比' in query or '比较' in query or '差异' in query:
            return self._compare_dfs(dfs)
        elif '合并' in query or 'merge' in query.lower():
            return self._merge_dfs(dfs)
        else:
            return self._overview_dfs(dfs)
    
    def _compare_dfs(self, dfs):
        results = ['## 📊 多文件数据对比']
        for name, df in dfs.items():
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            stats = "; ".join([f'{col}: 均值={df[col].mean():.1f}' for col in numeric_cols[:3]]) if numeric_cols else "无数值列"
            results.append(f'\n### 📁 {name}\n- 数据规模: {len(df)}行 × {len(df.columns)}列\n- 数值统计: {stats}')
        return {'success': True, 'output': '\n'.join(results)}
    
    def _merge_dfs(self, dfs):
        df_names = list(dfs.keys())
        if len(df_names) < 2:
            return {'success': False, 'error': '至少需要两个文件才能合并'}
        common_cols = set(dfs[df_names[0]].columns)
        for name in df_names[1:]:
            common_cols = common_cols & set(dfs[name].columns)
        if common_cols:
            col = list(common_cols)[0]
            merged = dfs[df_names[0]]
            for name in df_names[1:]:
                merged = merged.merge(dfs[name], on=col, how='outer', suffixes=(f'_{df_names[df_names.index(name)-1]}', f'_{name}'))
            return {'success': True, 'output': f'合并完成: {len(merged)}行, {len(merged.columns)}列\n\n合并后数据预览:\n{merged.head(3).to_string()}'}
        return {'success': False, 'error': '文件之间没有共同列，无法自动合并'}
    
    def _overview_dfs(self, dfs):
        import numpy as np
        total_rows = sum(len(df) for df in dfs.values())
        total_cols = sum(len(df.columns) for df in dfs.values())
        results = [f'📊 多文件数据概览\n{"=" * 40}\n\n📈 总体统计:\n  文件数量: {len(dfs)}\n  总行数: {total_rows}\n  总列数: {total_cols}']
        for name, df in dfs.items():
            results.append(f'\n📁 {name}:\n  行数: {len(df)}, 列数: {len(df.columns)}\n  列名: {", ".join(df.columns.tolist())}\n  缺失值总数: {df.isnull().sum().sum()}')
        return {'success': True, 'output': '\n'.join(results)}


import re
import numpy as np

analysis_service = AnalysisService()
