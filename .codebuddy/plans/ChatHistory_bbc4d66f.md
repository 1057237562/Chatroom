---
name: ChatHistory
overview: 为 FastAPI 聊天应用实现完整的聊天历史记录功能，包括数据库持久化存储、多条件查询、界面展示及性能优化。
todos:
  - id: db-setup
    content: 创建 SQLite 数据库模块，定义消息表结构、初始化脚本、字段索引
    status: completed
  - id: db-async-ops
    content: 实现异步消息存储和查询操作（使用 aiosqlite），在 broadcast_message 后调用存储函数
    status: completed
    dependencies:
      - db-setup
  - id: api-history
    content: 创建 /api/history REST 端点，支持分页、用户名过滤、时间范围查询参数
    status: completed
    dependencies:
      - db-async-ops
  - id: history-command
    content: 实现 HistoryCommand 类（/history 命令），注册到命令工厂，返回历史消息摘要
    status: completed
    dependencies:
      - api-history
  - id: frontend-ui
    content: 添加前端历史面板 UI，实现搜索、筛选、分页加载交互，集成虚拟滚动优化
    status: completed
    dependencies:
      - history-command
  - id: requirements-update
    content: 更新 requirements.txt，添加 aiosqlite 依赖
    status: completed
---

## 用户需求总结

### 产品概览

为现有 FastAPI 聊天室应用添加消息持久化存储功能，实现完整的聊天历史管理和查询系统，包括数据存储、查询接口和用户界面。

### 核心功能

1. **消息持久化存储**

- 将所有聊天消息、元数据（发送者、时间戳、消息类型）持久化至数据库
- 支持消息内容、发送者、时间戳等字段的完整记录
- 确保数据存储安全可靠

2. **历史记录查询**

- 支持按时间顺序获取历史消息
- 支持按用户名、关键词、时间范围等条件查询
- 提供分页查询以优化性能
- 创建数据库索引加速查询

3. **前端展示与交互**

- 新增历史消息面板，展示历史聊天记录
- 支持加载历史消息功能
- 支持搜索和时间筛选
- 前端虚拟滚动优化大量消息显示

4. **命令系统扩展**

- 实现 `/history` 命令供用户查询历史记录
- 支持指定查询参数（用户、时间范围等）

### 技术约束

- 使用 SQLite 轻量级数据库（无额外依赖，适合本地应用）
- 与现有 FastAPI + WebSocket 架构集成
- 遵循现有命令系统设计模式
- 保持前端 Metro 风格 CSS 一致性

## 技术栈选择

### 核心技术

- **数据库**: SQLite（内置，轻量级，支持 Python 3.9+ 原生集成）
- **数据库驱动**: `sqlite3`（Python 标准库）
- **ORM 层**: 无（直接使用 sqlite3 以保持简洁）
- **异步集成**: `aiosqlite`（异步 SQLite 驱动，与 FastAPI WebSocket 兼容）
- **时间管理**: `datetime`（已有依赖）

### 现有依赖复用

- `fastapi`, `uvicorn`, `python-multipart`（保持不变）

## 实现方案

### 高级策略

1. **数据库层设计**

- 创建 `ChatMessage` 表，包含字段：
    - `id` (INTEGER PRIMARY KEY)
    - `username` (TEXT NOT NULL)
    - `content` (TEXT NOT NULL)
    - `timestamp` (TEXT NOT NULL)
    - `message_type` (TEXT, 默认 'normal')
- 在 `username` 和 `timestamp` 上建立索引加速查询
- 使用 SQLite 的 SQLite3 模块进行同步操作（初始化），`aiosqlite` 进行异步查询

2. **集成点**

- **消息存储**: 在 `broadcast_message()` 函数调用后立即存储至数据库
- **查询接口**: 创建 HTTP 端点 `/api/history` 支持参数化查询（用户名、时间范围、分页）
- **命令扩展**: 创建 `HistoryCommand` 类（`/history` 命令），通过命令系统返回历史记录摘要

3. **前端集成**

- 新增"历史"标签页，展示历史消息面板
- 实现搜索和筛选 UI，支持按用户、时间范围、关键词查询
- 虚拟滚动列表处理大量消息（性能优化）
- 分页加载历史记录（每次加载 50 条）

### 关键技术决策

**为何选择 SQLite？**

- 项目是本地聊天应用，无需中央服务器，SQLite 足以满足需求
- 无外部依赖，简化部署
- 支持事务和索引，性能可控
- Python 内置 sqlite3 模块

**为何选择 aiosqlite？**

- FastAPI 基于异步架构，aiosqlite 提供非阻塞数据库访问
- 避免线程池开销，保持异步特性
- 性能对标传统同步驱动

**分页策略**

- 前端默认请求最近 50 条消息
- 支持 `offset` 参数加载更久的历史
- 避免一次加载全部数据导致内存溢出

**索引策略**

- `username` 索引：加速按用户过滤查询 (O(log n))
- `timestamp` 索引：加速按时间范围查询 (O(log n))
- 复合索引 `(username, timestamp)` 可选，如需频繁组合查询

### 性能优化

| 操作 | 预期复杂度 | 优化策略 |
| --- | --- | --- |
| 存储消息 | O(1) | 批量提交（若消息量大，可使用队列） |
| 按用户查询 | O(log n) | 用户名索引 |
| 按时间范围查询 | O(log n) | 时间戳索引 |
| 分页查询 | O(log n + k) | LIMIT/OFFSET，k=每页条数 |
| 全文搜索 | O(n) | 若需优化，可集成 FTS5 模块 |


### 数据流

```
用户发送消息
  ↓
broadcast_message() 广播消息
  ↓
save_message_to_db() 异步存储 (aiosqlite)
  ↓
前端请求 /api/history
  ↓
查询数据库（带索引）
  ↓
返回分页结果 + 元数据
  ↓
前端虚拟滚动渲染历史面板
```

## 实现细节

### 向后兼容性

- 内存中的 `user_map` 和 `current_users` 保持不变（用于实时连接管理）
- 现有消息广播逻辑不变（仅新增存储操作）
- 现有命令系统完全兼容（新增 HistoryCommand）

### 错误处理

- 数据库写入失败：记录错误日志，不阻断消息广播
- 数据库读取失败：返回 HTTP 500，前端友好提示
- 网络异常：前端重试机制

### 日志记录

- 使用 Python `logging` 模块
- 日志级别：INFO（初始化、查询统计）、ERROR（异常）
- 避免记录敏感信息（消息内容本身不敏感，但用户隐私考虑）

## 架构设计

### 模块划分

1. **数据库模块** (`db/message_db.py`)

- SQLite 连接管理
- 消息表初始化
- CRUD 操作（异步）

2. **API 模块** (在 `main.py` 中)

- `/api/history` GET 端点
- 参数校验和查询分派

3. **命令模块** (`command/commands/history.py`)

- `HistoryCommand` 实现
- 轻量化摘要返回

4. **前端模块** (`static/index.html`, `static/metro.css`)

- 历史面板 UI
- 搜索和筛选组件
- 虚拟滚动实现

### 启动流程

1. 应用启动时，初始化 SQLite 数据库（创建表、索引）
2. 注册 HistoryCommand
3. 前端加载时获取最新 50 条消息并渲染