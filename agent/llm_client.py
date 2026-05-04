"""
LLM 客户端
===========
对接大语言模型（OpenAI / Ollama），用于：
- 根据自然语言生成 Pandas 分析代码
- 支持对话上下文理解

支持两种模式：
1. Ollama 本地模型（默认，免费）
2. OpenAI API（需要 API Key）

降级策略：
如果 LLM 不可用，自动切换到 code_generator 的规则匹配
"""

import os
import re
import pandas as pd
from typing import Optional
from utils.logger import logger

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

MODEL_TYPE = os.getenv("MODEL_TYPE", "ollama").lower()


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self):
        self.client = None
        self.model = None
        self._init_client()
    
    def _init_client(self):
        if MODEL_TYPE == "ollama":
            self._init_ollama()
        else:
            self._init_openai()
    
    def _init_ollama(self):
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
        self.base_url = f"{ollama_url}/v1"
        
        try:
            self.client = OpenAI(base_url=self.base_url, api_key="ollama")
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=10
            )
            logger.info(f"成功连接 Ollama: {self.model}")
        except Exception as e:
            logger.warning(f"Ollama 连接失败: {e}")
            self.client = None
    
    def _init_openai(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your-api-key-here":
            try:
                import httpx
                base_url = os.getenv("OPENAI_BASE_URL")
                self.client = OpenAI(api_key=api_key, base_url=base_url, http_client=httpx.Client(proxies=None))
                self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                logger.info("成功连接 OpenAI API")
            except Exception as e:
                logger.error(f"连接 OpenAI API 失败: {e}")
    
    def generate_code(self, query: str, df: pd.DataFrame, context: str = "") -> Optional[str]:
        """用大语言模型生成 Pandas 代码"""
        if not self.client:
            logger.warning("未配置大语言模型，使用规则匹配")
            return None
        
        column_info = "\n".join([f"- {col} ({str(df[col].dtype)})" for col in df.columns])
        
        context_section = ""
        if context:
            context_section = f"\n对话历史：\n{context}\n"
        
        prompt = f"""
你是一个专业的数据可视化和分析代码生成器。将中文查询转换为 Python 代码。

规则：
1. 仅输出一行 Python 代码，无其他内容
2. DataFrame 变量名为 df
3. 分析查询用 result = ... 赋值
4. 画图查询直接调用 df.plot()，不要赋值给 result
5. 不要用 print，不要加注释
6. 注意参考对话历史，理解用户的指代（如"它"、"这个"、"之前提到的"等）
{context_section}
列名：{df.columns.tolist()}

图表类型选择：
- 趋势/时序数据 → 折线图: df.groupby('分类列')['数值列'].sum().plot(kind='line')
- 分类数据对比 → 柱状图: df.groupby('分类列')['数值列'].sum().plot(kind='bar')
- 占比/百分比 → 饼图: df.groupby('分类列')['数值列'].sum().plot(kind='pie', autopct='%1.1f%%')
- 数值分布 → 直方图: df['数值列'].hist()
- 变量关系 → 散点图: df.plot(kind='scatter', x='列1', y='列2')

示例：
中文：各地区销售额 → result = df.groupby('地区')['销售额'].sum()
中文：每月销售额趋势 → df.groupby('月份')['销售额'].sum().plot(kind='line')
中文：各品类销售额对比 → df.groupby('品类')['销售额'].sum().plot(kind='bar')
中文：各品类销售额占比 → df.groupby('品类')['销售额'].sum().plot(kind='pie', autopct='%1.1f%%')
中文：利润分布 → df['利润'].hist()
中文：销售额与利润关系 → df.plot(kind='scatter', x='销售额', y='利润')

现在转换：{query}
"""
        
        try:
            messages = [
                {"role": "system", "content": "你是一个专业的数据分析助手，根据对话历史理解用户的问题，并只输出有效的 Python Pandas 代码。"},
                {"role": "user", "content": prompt}
            ]
            
            if context:
                history_messages = []
                for line in context.split("\n"):
                    if line.startswith("用户:"):
                        history_messages.append({"role": "user", "content": line[3:]})
                    elif line.startswith("助手:"):
                        history_messages.append({"role": "assistant", "content": line[3:]})
                if history_messages:
                    messages = [{"role": "system", "content": "你是一个专业的数据分析助手，根据对话历史理解用户的问题，并只输出有效的 Python Pandas 代码。"}] + history_messages + [{"role": "user", "content": prompt}]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=500
            )
            
            code = response.choices[0].message.content.strip()
            code = re.sub(r'^```python\s*|\s*```$', '', code)
            logger.info(f"生成的代码: {code}")
            return code
        except Exception as e:
            logger.error(f"调用大语言模型失败: {e}")
            return None


llm_client = LLMClient()
