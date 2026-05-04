# 项目架构说明

## 🏗️ 整体架构

本项目采用**分层架构**设计，遵循关注点分离原则：

```
┌─────────────────────────────────────────┐
│              前端 (Frontend)             │
│         web/index.html (SPA)            │
├─────────────────────────────────────────┤
│           路由层 (Routers)               │
│   处理HTTP请求，参数校验，调用服务层      │
├─────────────────────────────────────────┤
│          服务层 (Services)               │
│   核心业务逻辑：分析、生成、记忆管理      │
├─────────────────────────────────────────┤
│          工具层 (Utils)                  │
│   日志、配置、生命周期等基础设施          │
└─────────────────────────────────────────┘
```

## 📂 各层职责

### 1. 路由层 (`routers/`)
**职责**: API接口定义、请求/响应格式化

**文件说明**:
- `data_analysis.py`: 核心数据分析接口（快速+深度）
- `chat.py`: 聊天对话接口
- `documents.py`: 文件上传管理接口
- `health.py`: 健康检查接口

### 2. 服务层 (`services/`)
**职责**: 业务逻辑实现、数据处理、AI交互

**核心模块**:
- **data_analysis_service.py** (最核心)
  - 意图识别: 判断用户想做什么
  - 代码生成: 调用LLM或规则匹配
  - 代码执行: 安全运行生成的代码
  - 图表生成: Matplotlib可视化
  
- **dataframe_agent.py**
  - 基于规则的模式匹配（降级方案）
  - 多文件聚合逻辑
  - 预定义的分析模板

- **memory_service.py**
  - 对话历史存储（内存）
  - 上下文管理
  - 会话ID生成

- **chat_service.py**
  - 快速分析的封装
  - 流式响应处理

- **document_service.py**
  - 文件上传处理
  - CSV/Excel解析
  - 元数据提取

### 3. 工具层 (`utils/`)
**职责**: 基础设施、通用工具

- **logger.py**: 日志配置和统一接口
- **lifespan.py**: 应用启动/关闭的生命周期事件

### 4. 中间件 (`middleware/`)
- **logging_middleware.py**: HTTP请求日志记录

## 🔀 数据流示意

### 快速分析流程
```
用户输入 → [路由层] 参数校验
         → [服务层] 意图识别 → 代码生成 → 代码执行
         → 返回结果 (同步)
```

### 深度分析流程
```
用户输入 → [路由层] 创建SSE连接
         → [服务层] 加载上下文 → 流式生成多个分析步骤
         → 逐步推送结果 (异步流式)
```

## 💡 设计决策

### 为什么选择 FastAPI?
- 自动生成API文档 (Swagger UI)
- 原生支持异步
- 类型提示集成好
- 性能优秀 (基于 Starlette)

### 为什么用 Pandas 而不是 SQL?
- 用户上传的是CSV/Excel文件，不是数据库
- Pandas 更适合探索性数据分析
- 便于生成统计图表

### 为什么有"快速"和"深度"两种模式?
- **快速模式**: 简单场景，响应快，适合简单查询
- **深度模式**: 复杂分析，支持上下文，体验更好但稍慢
- 让用户根据需求选择，平衡速度和功能

### 代码执行安全性如何保证?
1. **白名单机制**: 只允许 pd, np, plt 等安全库
2. **危险操作检测**: 过滤掉 os, subprocess, eval 等
3. **超时限制**: 30秒超时防止死循环
4. **独立线程**: 不阻塞主进程

## 🎯 关键技术点（面试常问）

### 1. 自然语言到代码的转换
```python
# 方案A: LLM生成 (需要API Key)
code = llm_agent.generate_code(query, df)

# 方案B: 规则匹配 (离线可用，作为降级)
code = dataframe_agent.generate_code_by_rules(query)
```

### 2. SSE流式输出实现
```python
# 使用 Python generator + StreamingResponse
async def stream_generator():
    for chunk in analysis_process():
        yield f"data: {json.dumps(chunk)}\n\n"

return StreamingResponse(
    stream_generator(),
    media_type="text/event-stream"
)
```

### 3. 对话上下文管理
```python
# 简单的内存存储 (生产环境建议用Redis)
conversations = {}

def add_message(conv_id, role, content):
    if conv_id not in conversations:
        conversations[conv_id] = {"messages": []}
    conversations[conv_id]["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })
```

## 📈 扩展性考虑

当前设计的可扩展点：
1. **新增分析类型**: 在 `_detect_intent()` 添加新模式
2. **支持新文件格式**: 在 `_load_dataframe()` 添加解析器
3. **更换AI模型**: 只需修改 `LLMAgent` 类
4. **添加认证**: 通过FastAPI中间件实现
5. **持久化存储**: 替换 `memory_service` 的后端

---

**最后更新**: 2024-05  
**维护者**: [你的名字]
