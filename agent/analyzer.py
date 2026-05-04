"""
数据分析引擎
============
Agent 的核心模块，负责：
1. 意图识别 - 理解用户想做什么
2. 代码执行 - 安全运行分析代码
3. 图表生成 - 生成可视化图表
4. 报告生成 - 生成完整分析报告
5. 异常检测 - 识别数据中的异常值
6. 趋势分析 - 分析数据变化趋势
7. 预测分析 - 基于历史数据预测

设计思路：
- 意图识别用正则匹配（简单高效，适合应届生项目）
- 代码执行有白名单机制和超时保护（安全第一）
- 图表用 Matplotlib 生成，保存为 PNG 文件
"""

import os
import uuid
import re
import json
import threading
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.logger import logger
from agent.memory import memory_service
from agent.llm_client import llm_client


class TimeoutException(Exception):
    """代码执行超时"""
    pass


class CodeExecutor:
    """
    安全代码执行器
    
    通过白名单机制限制可用的函数和库，
    用独立线程+超时防止死循环，
    确保用户生成的代码不会造成安全风险
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._result = None
        self._exception = None
    
    def _run_code(self, code, allowed_globals, local_vars):
        try:
            exec(code, allowed_globals, local_vars)
            self._result = local_vars
        except Exception as e:
            self._exception = e
    
    def execute(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        result = {
            'success': False,
            'output': '',
            'chart_path': None,
            'error': None
        }
        
        local_vars = {'df': df.copy()}
        code = self._sanitize_code(code)
        
        if not code:
            result['error'] = "代码为空或包含危险操作"
            return result
        
        self._result = None
        self._exception = None
        
        allowed_globals = {
            'pd': pd,
            'np': np,
            'plt': plt,
            'sns': sns,
            '__builtins__': {
                'abs': abs, 'all': all, 'any': any, 'bool': bool,
                'float': float, 'int': int, 'len': len, 'list': list,
                'range': range, 'str': str, 'sum': sum, 'zip': zip,
            }
        }
        
        thread = threading.Thread(
            target=self._run_code,
            args=(code, allowed_globals, local_vars)
        )
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            result['error'] = f"代码执行超时（超过{self.timeout}秒）"
            plt.close('all')
            return result
        
        if self._exception:
            result['error'] = f"执行错误: {str(self._exception)}"
            plt.close('all')
            return result
        
        if self._result:
            local_vars.update(self._result)
        
        try:
            if 'result' in local_vars:
                output = local_vars['result']
                if isinstance(output, pd.DataFrame):
                    result['output'] = output.to_string(max_rows=20, max_cols=10)
                elif isinstance(output, pd.Series):
                    result['output'] = output.to_string(max_rows=20)
                else:
                    result['output'] = str(output)
            elif plt.get_fignums():
                chart_path = self._save_chart()
                result['chart_path'] = chart_path
                result['output'] = "图表已生成"
            else:
                result['output'] = "代码执行成功，无输出"
            
            result['success'] = True
        except Exception as e:
            result['error'] = f"处理结果时出错: {str(e)}"
        finally:
            plt.close('all')
        
        return result
    
    def _sanitize_code(self, code: str) -> Optional[str]:
        """代码安全检查 - 过滤危险操作"""
        dangerous = [
            'import os', 'import subprocess', 'import sys',
            'open\\(', 'file\\(', 'exec\\(', 'eval\\(', 'compile\\(',
            'os\\.', 'subprocess\\.', 'sys\\.', '__import__',
            '__builtins__', 'globals\\(', 'locals\\(',
            'rm ', 'del ', 'shutil\\.', 'socket\\.', 'urllib\\.', 'requests\\.'
        ]
        for pattern in dangerous:
            if re.search(pattern, code, re.IGNORECASE):
                return None
        return code.strip()
    
    def _save_chart(self) -> str:
        os.makedirs("charts", exist_ok=True)
        chart_id = str(uuid.uuid4())[:8]
        chart_path = f"charts/chart_{chart_id}.png"
        plt.savefig(chart_path, bbox_inches='tight', dpi=150)
        plt.close('all')
        return chart_path


class DataAnalyzer:
    """
    数据分析引擎 - Agent 的核心
    
    工作流程：
    用户问题 → 意图识别 → 选择处理方式 → 返回结果
    
    支持的意图类型：
    - report: 生成完整报告
    - chart: 生成可视化图表
    - anomaly: 异常检测
    - trend: 趋势分析
    - predict: 预测分析
    - correlation: 相关性分析
    - describe: 描述统计
    - preview: 数据预览
    - analysis: 通用分析（调用LLM）
    """
    
    def __init__(self):
        self.executor = CodeExecutor(timeout=30)
    
    def detect_intent(self, query: str) -> str:
        """识别用户的查询意图"""
        if re.search(r'报告|总结|完整分析|分析.*数据集|分析.*数据', query):
            return 'report'
        elif re.search(r'画个|做个|弄个|生成.*图|制作.*图|创建.*图|图表', query):
            return 'chart'
        elif re.search(r'异常|问题|检查|错误|不对劲', query):
            return 'anomaly'
        elif re.search(r'趋势|变化|增长|下降|波动|规律', query):
            return 'trend'
        elif re.search(r'预测|未来|下一期', query):
            return 'predict'
        elif re.search(r'相关|关联|关系', query):
            return 'correlation'
        elif re.search(r'描述|统计|均值|平均|总和', query):
            return 'describe'
        elif re.search(r'预览|查看|前几行|结构', query):
            return 'preview'
        elif re.search(r'刚问啥|刚说啥|刚才问|刚才说|对话历史|历史记录', query):
            return 'history'
        else:
            return 'analysis'
    
    def is_data_question(self, query: str, columns: list) -> bool:
        """判断是否属于数据分析问题"""
        data_keywords = [
            '分析', '统计', '图表', '图', '表', '数据', '行', '列', '字段',
            '数值', '均值', '平均', '总和', '总计', '最大', '最小', '趋势',
            '相关', '异常', '预测', '分布', '描述', '预览', '类型', '缺失',
            '空值', '检测', '报告', '销售额', '利润', '数量', '占比', '对比',
            '看看', '怎么样', '帮我', '给我', '查看', '显示', '列出', '计算',
            '做个', '弄个', '生成', '画个', '有没有', '什么问题', '检查',
            '变化', '增长', '下降', '波动', '规律'
        ]
        greeting_keywords = [
            '你好', '您好', '嗨', 'hello', 'hi', '你是谁', '介绍',
            '帮助', '能做什么', '天气', '新闻', '聊天', '讲个', '故事', '笑话'
        ]
        for kw in greeting_keywords:
            if kw in query:
                return False
        for kw in data_keywords:
            if kw in query:
                return True
        for col in columns:
            if col in query:
                return True
        return False
    
    def generate_chart(self, df, y_column=None, chart_type='bar', x_column=None) -> str:
        """生成图表并保存为PNG"""
        os.makedirs("charts", exist_ok=True)
        chart_id = str(uuid.uuid4())[:8]
        chart_path = f"charts/chart_{chart_id}.png"
        
        plt.figure(figsize=(10, 6))
        try:
            if chart_type == 'bar':
                if x_column and y_column:
                    df.plot(x=x_column, y=y_column, kind='bar')
                elif y_column:
                    df[y_column].value_counts().plot(kind='bar')
                else:
                    df.iloc[:, 0].value_counts().plot(kind='bar')
            elif chart_type == 'line':
                if x_column and y_column:
                    df.plot(x=x_column, y=y_column, kind='line')
                elif y_column:
                    df[y_column].plot(kind='line')
                else:
                    df.iloc[:, 0].plot(kind='line')
            elif chart_type == 'hist':
                if y_column:
                    df[y_column].hist()
                else:
                    df.iloc[:, 0].hist()
            elif chart_type == 'pie':
                if y_column:
                    df[y_column].value_counts().plot(kind='pie', autopct='%1.1f%%')
                else:
                    df.iloc[:, 0].value_counts().plot(kind='pie', autopct='%1.1f%%')
            else:
                if y_column:
                    df[y_column].value_counts().plot(kind='bar')
                else:
                    df.iloc[:, 0].value_counts().plot(kind='bar')
            
            if x_column and y_column:
                plt.title(f'{y_column} vs {x_column} - {chart_type} chart')
            elif y_column:
                plt.title(f'{y_column} - {chart_type} chart')
            plt.savefig(chart_path, bbox_inches='tight', dpi=150)
        finally:
            plt.close('all')
        
        return chart_path
    
    def detect_anomalies(self, df, numeric_cols):
        """异常检测（IQR方法）"""
        anomaly_results = []
        all_anomalies = []
        
        for col in numeric_cols:
            if col not in df.columns:
                continue
            data = df[col].dropna()
            if len(data) < 4:
                continue
            
            q1 = data.quantile(0.25)
            q3 = data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            outliers = data[(data < lower) | (data > upper)]
            if len(outliers) > 0:
                col_anomalies = []
                for idx, val in outliers.head(5).items():
                    col_anomalies.append({
                        'row': idx + 1, 'value': val,
                        'lower_bound': lower, 'upper_bound': upper,
                        'is_high': val > upper,
                        'deviation': abs(val - (q1 + q3) / 2) / iqr if iqr != 0 else 0
                    })
                all_anomalies.extend(col_anomalies)
                explanation = self._anomaly_explanation(col, col_anomalies, data)
                anomaly_results.append(explanation)
        
        if not anomaly_results:
            return "✅ **数据质量良好**\n\n未检测到明显异常值，数据分布较为正常。"
        
        summary = "## 🔍 异常检测结果\n\n"
        summary += "\n".join(anomaly_results)
        summary += "\n\n" + self._anomaly_recommendations(all_anomalies)
        return summary
    
    def _anomaly_explanation(self, col, anomalies, data):
        mean_val = data.mean()
        lines = [f"### 🚨 {col}", f"- 异常数量: {len(anomalies)} 个", f"- 字段均值: {mean_val:.2f}"]
        if anomalies:
            a = anomalies[0]
            direction = "高于" if a['is_high'] else "低于"
            lines.append(f"- 首个异常: 第{a['row']}行，值={a['value']:.2f}，{direction}正常范围")
        return "\n".join(lines)
    
    def _anomaly_recommendations(self, anomalies):
        if not anomalies:
            return ""
        recs = ["## 💡 处理建议", ""]
        high = [a for a in anomalies if a['deviation'] >= 2]
        if high:
            recs.append(f"- **优先检查**: 有 {len(high)} 个严重偏离的值，建议人工核实原始数据")
        recs.append("- **数据验证**: 检查数据采集和录入流程是否存在问题")
        recs.append("- **业务确认**: 确认这些异常是否对应特殊业务事件")
        recs.append("- **处理方式**: 可考虑删除、替换或标记为异常")
        return "\n".join(recs)
    
    def trend_analysis(self, df, numeric_cols):
        """趋势分析"""
        trends = []
        for col in numeric_cols:
            if col not in df.columns:
                continue
            data = df[col].dropna()
            if len(data) < 3:
                continue
            values = data.values
            changes = []
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    changes.append((values[i] - values[i-1]) / abs(values[i-1]) * 100)
            if changes:
                avg_change = sum(changes) / len(changes)
                trend = "📈 上升趋势" if avg_change > 10 else "📉 下降趋势" if avg_change < -10 else "➡️ 平稳"
                trends.append(f"- {col}: {trend}（平均变化率: {avg_change:.2f}%）")
        return "\n".join(trends) if trends else "无法进行趋势分析（数据量不足）"
    
    def predict_analysis(self, df, numeric_cols):
        """预测分析（简单移动平均）"""
        predictions = []
        for col in numeric_cols:
            if col not in df.columns:
                continue
            data = df[col].dropna()
            if len(data) < 5:
                continue
            values = data.values
            recent = values[-3:]
            avg_recent = sum(recent) / len(recent)
            growth = (recent[-1] - recent[0]) / recent[0] * 100 if recent[0] != 0 else 0
            next_val = avg_recent * (1 + growth / 100)
            predictions.append(f"- {col}: 预测下一期值为 {next_val:.2f}（基于最近3期数据，增长率: {growth:.2f}%）")
        return "\n".join(predictions) if predictions else "无法进行预测（数据量不足，至少需要5条数据）"
    
    def generate_report(self, df, numeric_cols, anomalies, trends, predictions):
        """生成完整分析报告"""
        report = [
            "# 📊 数据洞察分析报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**数据概览**: {len(df)} 行 × {len(df.columns)} 列",
            "",
            "## 📈 趋势分析", trends, "",
            "## ⚠️ 异常检测", anomalies, "",
            "## 🔮 预测分析", predictions, "",
            "## 💡 智能建议"
        ]
        
        suggestions = []
        if "销售额" in numeric_cols:
            sales_data = df["销售额"].dropna()
            if len(sales_data) > 0 and sales_data.max() > sales_data.mean() * 1.5:
                suggestions.append("• 建议关注销售额峰值时期的营销活动，分析成功因素")
        if "利润" in numeric_cols:
            profit_data = df["利润"].dropna()
            if len(profit_data) > 0 and profit_data.min() < 0:
                suggestions.append("• 存在负利润记录，建议分析成本结构")
        if not suggestions:
            suggestions.append("• 当前数据质量良好，建议继续保持")
        
        report.append("\n".join(suggestions))
        report.append("")
        report.append("---")
        report.append("*此报告由数据洞察 Agent 自动生成*")
        return "\n".join(report)
    
    def save_report(self, content: str, file_id: str) -> str:
        """保存报告到Markdown文件"""
        os.makedirs("reports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"reports/report_{file_id}_{ts}.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"报告已保存: {filepath}")
        return filepath
    
    def execute_code(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """执行分析代码"""
        return self.executor.execute(code, df)
    
    def generate_code_with_llm(self, query: str, df: pd.DataFrame, context: str = "") -> Optional[str]:
        """通过LLM生成分析代码"""
        return llm_client.generate_code(query, df, context)


analyzer = DataAnalyzer()
