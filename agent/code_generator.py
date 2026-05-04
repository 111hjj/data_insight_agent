"""
代码生成器（规则匹配）
======================
当 LLM 不可用时的降级方案，基于正则表达式匹配用户查询，
生成对应的 Pandas 分析代码。

优点：
- 不依赖外部 API，离线可用
- 响应速度快
- 结果稳定可控

缺点：
- 只能处理预定义的查询模式
- 无法理解复杂的自然语言
"""

import re
import pandas as pd
from typing import Optional, Dict


class CodeGenerator:
    """基于规则的代码生成器"""
    
    def __init__(self):
        self.patterns = [
            (r"画.*可视化图表|数据可视化图表|可视化.*图表|生成图表", r"df.plot(kind='bar'); plt.title('数据可视化图表')"),
            (r"折线图|趋势图", r"df.plot(kind='line'); plt.title('折线图')"),
            (r"柱状图|条形图", r"df.plot(kind='bar'); plt.title('柱状图')"),
            (r"饼图", r"df.sum(numeric_only=True).plot(kind='pie'); plt.title('饼图')"),
            (r"直方图", r"df.hist(); plt.suptitle('直方图')"),
            (r"散点图", r"df.plot(kind='scatter', x='销售额', y='利润'); plt.title('散点图')"),
            (r"最高的前(\d+)个", r"result = df.sort_values('销售额', ascending=False).head(%s)"),
            (r"最高的(\d+)个", r"result = df.sort_values('销售额', ascending=False).head(%s)"),
            (r"最低的前(\d+)个", r"result = df.sort_values('销售额', ascending=True).head(%s)"),
            (r"最低的(\d+)个", r"result = df.sort_values('销售额', ascending=True).head(%s)"),
            (r"最低的是哪个", r"result = df.sort_values('销售额', ascending=True).head(1)"),
            (r"最高的是哪个", r"result = df.sort_values('销售额', ascending=False).head(1)"),
            (r"销售额最低", r"result = df.sort_values('销售额', ascending=True).head(1)"),
            (r"销售额最高", r"result = df.sort_values('销售额', ascending=False).head(1)"),
            (r"平均|均值", r"result = df.mean(numeric_only=True)"),
            (r"总和|总计", r"result = df.sum(numeric_only=True)"),
            (r"描述统计|统计信息", r"result = df.describe()"),
            (r"相关系数", r"result = df.corr(numeric_only=True)"),
            (r"空值|缺失值", r"result = df.isnull().sum()"),
            (r"前(\d+)行", r"result = df.head(%s)"),
            (r"数据预览", r"result = df.head(10)"),
            (r"列名|字段名", r"result = df.columns.tolist()"),
            (r"数据类型", r"result = df.dtypes"),
        ]
        
        self.multi_patterns = [
            (r"对比|比较|差异|区别", "multi_compare"),
            (r"合并|merge|join", "multi_merge"),
            (r"汇总|总览|概览", "multi_overview"),
        ]
    
    def generate_code(self, query: str, df: pd.DataFrame) -> str:
        """根据查询生成代码（单文件）"""
        for pattern, code_template in self.patterns:
            if re.search(pattern, query):
                match = re.search(pattern, query)
                if match and match.groups():
                    return code_template % match.groups()
                return code_template
        return "result = df.describe()"
    
    def generate_multi_code(self, query: str, dfs: Dict[str, pd.DataFrame]) -> str:
        """根据查询生成代码（多文件）"""
        for pattern, action in self.multi_patterns:
            if re.search(pattern, query):
                if action == "multi_compare":
                    return self._multi_compare_code(dfs)
                elif action == "multi_merge":
                    return self._multi_merge_code(dfs)
                elif action == "multi_overview":
                    return self._multi_overview_code(dfs)
        
        for pattern, code in self.patterns:
            if re.search(pattern, query):
                if '多少行|行数|记录数' in pattern:
                    lines = ["total_rows = 0"]
                    for name in dfs.keys():
                        lines.append(f"total_rows += len({name})")
                    lines.append(f"result = f'共 {len(dfs)} 个数据集，总计 {{total_rows}} 行记录'")
                    return '\n'.join(lines)
                elif '多少列|列数|字段数' in pattern:
                    lines = ["total_cols = 0"]
                    for name in dfs.keys():
                        lines.append(f"total_cols += len({name}.columns)")
                    lines.append(f"result = f'共 {len(dfs)} 个数据集，总计 {{total_cols}} 列字段'")
                    return '\n'.join(lines)
                else:
                    first_df_name = list(dfs.keys())[0]
                    return code.replace('df', first_df_name)
        
        return self._multi_overview_code(dfs)
    
    def _multi_compare_code(self, dfs):
        lines = ["results = []"]
        for name, df in dfs.items():
            lines.append(f"results.append('{name}: ' + str(len({name})) + '行')")
        lines.append("result = '\\n'.join(results)")
        return '\n'.join(lines)
    
    def _multi_merge_code(self, dfs):
        df_names = list(dfs.keys())
        if len(df_names) < 2:
            return "result = '至少需要两个文件才能合并'"
        common_cols = set(dfs[df_names[0]].columns)
        for name in df_names[1:]:
            common_cols = common_cols & set(dfs[name].columns)
        if common_cols:
            col = list(common_cols)[0]
            code = f"merged = {df_names[0]}\n"
            for name in df_names[1:]:
                code += f"merged = merged.merge({name}, on='{col}', how='outer')\n"
            code += "result = f'合并完成: {len(merged)}行, {len(merged.columns)}列'"
            return code
        return "result = '文件之间没有共同列，无法自动合并'"
    
    def _multi_overview_code(self, dfs):
        lines = ["results = []", "results.append('📊 多文件数据概览')"]
        for name, df in dfs.items():
            lines.append(f"results.append(f'\\n📁 {name}: 行数={{len({name})}}, 列数={{len({name}.columns)}}')")
        lines.append("result = '\\n'.join(results)")
        return '\n'.join(lines)


code_generator = CodeGenerator()
