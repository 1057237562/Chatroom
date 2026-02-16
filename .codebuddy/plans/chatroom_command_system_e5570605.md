---
name: chatroom_command_system
overview: 为聊天室应用实现基于策略模式的命令系统，支持私信（/t）和帮助（/help）命令，代码组织在 command 目录下，提供完整的参数校验和错误处理机制。
todos:
  - id: setup-command-structure
    content: 创建 command 包结构和基础文件（__init__.py, base.py, factory.py）
    status: completed
  - id: implement-base-command
    content: 实现 CommandBase 基类，定义命令接口、上下文、响应结构
    status: completed
    dependencies:
      - setup-command-structure
  - id: implement-commands
    content: 实现 WhisperCommand 和 HelpCommand，包含参数校验和执行逻辑
    status: completed
    dependencies:
      - implement-base-command
  - id: implement-command-factory
    content: 实现 CommandFactory，完成命令注册、创建和路由机制
    status: completed
    dependencies:
      - implement-commands
  - id: integrate-main-program
    content: 修改 main.py websocket_endpoint，集成命令系统，支持命令前缀识别和分派
    status: completed
    dependencies:
      - implement-command-factory
  - id: error-handling-testing
    content: 完整的错误处理测试，验证所有参数校验、边界条件、异常恢复
    status: completed
    dependencies:
      - integrate-main-program
---

## 产品概述

为现有的FastAPI聊天室添加一个高可扩展的命令系统，支持以 `/` 前缀开头的指令解析和处理。

## 核心功能

- **私信命令** (`/t @username message`)：用户可以向在线用户发送私密消息，仅目标用户接收
- **帮助命令** (`/help`)：显示所有可用命令及其使用方法
- **命令系统框架**：采用策略模式设计，支持轻松扩展新命令
- **参数验证与错误处理**：
- 命令格式验证（检查是否为有效的命令格式）
- 用户存在性检查（确保私信目标用户在线）
- 消息内容验证（非空校验、自身私信防护）
- 完整的错误提示反馈机制

## 技术选型

### 当前技术栈

- **后端框架**：FastAPI + Uvicorn
- **实时通信**：WebSocket
- **数据管理**：内存存储（user_map、current_users）
- **Python版本**：3.8+

### 实现方案

#### 系统架构

采用**策略模式**实现命令系统，核心设计：

- **基础命令类（Command Base Class）**：定义命令接口，所有命令继承此类
- **命令工厂（CommandFactory）**：根据命令名称实例化对应的命令处理器
- **命令路由（CommandRouter）**：解析消息中的命令前缀和参数，分派给相应处理器

#### 关键设计决策

1. **为什么采用策略模式**

- 解耦命令处理逻辑与主程序流
- 每个命令独立文件，便于维护和扩展
- 新增命令无需修改既有代码（开闭原则）

2. **命令执行上下文**

- 传递 WebSocket 连接和当前用户名，使命令能访问完整的用户/连接信息
- 支持命令执行状态（成功/失败）和响应消息

3. **私信实现方式**

- 遍历 user_map 找到目标用户的 WebSocket 连接
- 使用单点发送而非广播，确保只有目标用户接收

4. **参数校验策略**

- `/t` 命令支持两种格式：`/t @username message` 或 `/t username message`
- 自动去除 `@` 符号进行用户匹配
- 完整检查：用户存在性、用户在线状态、消息非空、禁止自我私信

#### 性能考虑

- **O(n)查询复杂度**：user_map查询为线性复杂度（用户在线数量级）
- 当前在线用户预期数量小，无需优化
- 如需支持万级用户，可改进为字典映射（username → WebSocket）
- **避免重复遍历**：缓存在线用户列表，私信查询时高效定位
- **错误快速路径**：参数校验在前，减少无效命令处理

#### 扩展性设计

- 所有命令统一继承 CommandBase，新命令只需实现 `execute()` 和 `validate()` 方法
- CommandFactory 通过导入新命令类自动注册
- 便于后续添加：`/mute`、`/kick`、`/broadcast` 等管理命令

## 模块划分

### command 包结构

```
command/
├── __init__.py           # 导出公共接口
├── base.py              # CommandBase 基类（抽象接口）
├── factory.py           # CommandFactory 工厂类（命令注册与实例化）
└── commands/
    ├── __init__.py
    ├── help.py          # HelpCommand（/help）
    └── whisper.py       # WhisperCommand（/t 私信）
```

### 数据流

```
WebSocket消息 → 命令解析(/前缀检测) → 参数提取与校验 → 工厂创建命令实例 
→ 执行命令(execute) → 单点/广播发送响应 → 客户端接收
```

## 实现要点

### 1. 命令基类（base.py）

- 定义 `validate()` 和 `execute()` 抽象方法
- 定义命令上下文数据结构（包含 websocket、username、user_map、current_users）
- 定义命令响应结构（成功/失败、响应消息）

### 2. 私信命令（whisper.py）

- 解析 `/t @username msg` 格式
- 校验目标用户是否存在且在线
- 禁止用户给自己发私信
- 构造私信消息并单点发送到目标 WebSocket

### 3. 帮助命令（help.py）

- 列出所有支持的命令及用法
- 格式化命令列表，返回友好的帮助信息

### 4. 主程序集成（main.py）

- 第39-42行改造：消息接收后先检测 `/` 前缀
- 调用 CommandRouter 解析命令，若非命令则按原逻辑广播
- 完整的异常捕获（命令不存在、参数错误等）

## 错误处理机制

- **无效命令**：`/unknown` → 返回"未知命令"
- **参数缺失**：`/t` 无参数 → 返回"格式错误，请使用 /t @username message"
- **用户不存在**：`/t @offline_user msg` → 返回"用户不在线"
- **自我私信**：`/t @self msg` → 返回"不能给自己发私信"
- **未知错误**：捕获所有异常，返回通用错误提示

## 代码质量

- 所有命令类遵循一致的签名和异常处理模式
- 参数校验集中在 `validate()` 方法，execute() 仅执行业务逻辑
- 完整的日志记录（可选），便于调试私信、命令执行失败等事件