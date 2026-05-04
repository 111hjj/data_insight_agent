"""
Agent 模块
==========
AI Agent 核心组件，负责数据分析的智能部分

包含：
- analyzer: 数据分析引擎（意图识别、代码执行、图表生成、报告生成）
- llm_client: 大语言模型客户端（OpenAI/Ollama）
- code_generator: 基于规则的代码生成器（降级方案）
- memory: 对话记忆管理
"""

from agent.analyzer import DataAnalyzer
from agent.llm_client import LLMClient
from agent.code_generator import CodeGenerator
from agent.memory import MemoryService

analyzer = DataAnalyzer()
llm_client = LLMClient()
code_generator = CodeGenerator()
memory_service = MemoryService()
