---
name: Agent Utils OpenAI Integration
overview: 开发Agent Utils模块，集成OpenAI接口并支持现有命令系统。AI将作为虚拟用户参与聊天，支持所有命令操作、私聊交互，能够查询在线用户列表，并具备完整的错误处理和连接管理。
todos:
  - id: explore-codebase
    content: 探索现有代码库结构、命令系统、消息处理流程
    status: completed
  - id: create-utils-types
    content: 创建utils/types.py定义Agent相关数据类型（AgentConfig、AgentMessage等）
    status: completed
    dependencies:
      - explore-codebase
  - id: create-prompts
    content: 创建utils/prompts.py管理系统提示词和命令指导文本
    status: completed
    dependencies:
      - explore-codebase
  - id: create-agent-core
    content: 实现utils/agent.py核心AIAgent类，包含OpenAI异步客户端和消息处理逻辑
    status: completed
    dependencies:
      - create-utils-types
      - create-prompts
  - id: update-requirements
    content: 更新requirements.txt添加openai依赖
    status: completed
  - id: add-users-api
    content: 在main.py添加GET /api/users接口获取在线用户列表
    status: completed
    dependencies:
      - explore-codebase
  - id: integrate-agent
    content: 在main.py初始化AIAgent，添加消息处理逻辑，实现AI参与聊天
    status: completed
    dependencies:
      - create-agent-core
      - add-users-api
  - id: test-integration
    content: 测试Agent集成、命令执行、私聊功能和错误处理
    status: completed
    dependencies:
      - integrate-agent
---

## 产品概述

为聊天室应用集成OpenAI Agent能力，使系统支持AI智能助手的参与。AI助手需要无缝集成到现有的WebSocket聊天系统中，支持所有聊天命令和交互方式。

## 核心需求

### 功能需求

1. **AI Agent Utils模块**：创建独立的Agent工具库用于OpenAI集成
2. **AI能力支持**：

- 支持所有现有聊天命令操作（/help、/t私聊等）
- 支持私聊交互方式
- 能获取实时用户列表
- 能理解和回复用户消息

3. **API完整性**：

- 提供获取当前在线用户列表的HTTP接口
- 完整的OpenAI API调用封装
- 支持异步消息处理

### 非功能需求

1. **性能与稳定性**：

- 异步处理所有I/O操作，避免阻塞主线程
- OpenAI API调用失败时的重试机制和超时控制
- 全面的日志记录便于调试

2. **安全性**：

- OpenAI API密钥通过环境变量配置
- 输入验证和错误处理

3. **可扩展性**：

- 模块化架构，便于未来扩展Agent能力
- 遵循现有的命令系统和数据流设计

## 技术栈选择

- **编程语言**：Python 3.9+
- **异步框架**：FastAPI + asyncio
- **OpenAI集成**：openai Python库（v1.0+）
- **数据库**：SQLite3 + aiosqlite
- **现有栈**：WebSocket、JSON消息格式

## 实现方案

### 系统架构

采用分层模块化架构：

- **Utils层**（新增）：Agent Utils模块，独立的AI能力封装
- `agent.py`：核心AIAgent类，处理OpenAI通信
- `types.py`：数据类型定义（AgentMessage、AgentCommand等）
- `prompts.py`：系统提示词管理

- **API层**（扩展）：新增HTTP接口供前端和Agent查询
- `/api/users` - 获取在线用户列表

- **应用层**（现有）：main.py集成AI初始化和事件处理

### 数据流设计

```
用户消息 → main.py WebSocket处理 
  ├─ 普通消息：广播 + 数据库持久化
  ├─ 命令消息：CommandFactory执行
  └─ AI回复：通过broadcast_message广播给所有用户
  
AI消息处理流程：
监听WebSocket消息 → OpenAI API调用 → 解析响应 
  ├─ 生成回复消息
  ├─ 执行指定命令（如/t私聊）
  └─ 广播回复或发送私聊
```

### 关键技术决策

1. **异步设计**：全程使用async/await，避免OpenAI API调用阻塞

- 原因：保证聊天室响应性，支持并发处理多个用户消息

2. **独立Agent模块**：Agent Utils与命令系统解耦

- 原因：易于测试、维护和扩展，不侵入现有代码

3. **重试机制**：OpenAI调用失败时使用指数退避

- 原因：提高稳定性，处理网络抖动和API临时故障

4. **提示词管理**：系统提示词集中管理在prompts.py

- 原因：易于调整AI行为，支持版本控制

### 关键接口设计

**AIAgent类核心方法**：

```python
class AIAgent:
    async def initialize(config: AgentConfig) -> None
    async def process_message(message: str, username: str) -> AgentResponse
    async def execute_command(command: str, args: list) -> AgentResponse
    async def get_users() -> list[str]
```

**HTTP API**：

```
GET /api/users
响应: {"users": ["user1", "user2", ...], "success": true}
```

### 性能优化

- **OpenAI调用缓存**：对相同提示词的调用结果短期缓存（避免N+1问题）
- **消息队列**：使用asyncio.Queue处理消息队列，支持并发处理
- **连接复用**：OpenAI客户端实例全局复用，避免重复创建

### 错误处理策略

- OpenAI API异常：捕获并记录，返回友好错误信息给用户
- 超时控制：30秒超时，自动返回降级响应
- 用户不存在：验证用户在线状态，返回错误提示