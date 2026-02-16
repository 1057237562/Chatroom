# 聊天室命令系统文档

## 系统概述

本聊天室应用实现了一个高度可扩展的命令系统，采用**策略模式**设计，支持识别以 `/` 前缀开头的指令。

## 目录结构

```
command/
├── __init__.py           # 包入口，导出公共接口
├── base.py              # 基础类定义（CommandBase, CommandContext, CommandResponse）
├── factory.py           # 命令工厂（负责命令注册和创建）
├── router.py            # 命令路由器（消息解析）
└── commands/
    ├── __init__.py
    ├── help.py          # /help 命令实现
    └── whisper.py       # /t 私信命令实现
```

## 核心模块说明

### 1. base.py - 基础类和数据结构

**CommandContext**
- 包含命令执行所需的上下文信息
- 字段：websocket（连接）、username（用户名）、user_map（用户映射）、current_users（在线用户集合）

**CommandResponse**
- 命令执行结果的标准响应格式
- 字段：success（是否成功）、message（返回消息）、response_type（响应类型）、target_user（目标用户，用于私信）

**CommandBase** (抽象基类)
- 所有命令的基类
- 抽象方法：
  - `name`: 命令名称（不含斜杠）
  - `description`: 命令描述
  - `usage`: 命令用法
  - `validate(args)`: 参数校验
  - `execute(context, args)`: 命令执行

### 2. factory.py - 命令工厂

**CommandFactory** (单例模式)
- 管理所有已注册命令
- 方法：
  - `register(command_class)`: 注册命令类
  - `create(command_name)`: 创建命令实例
  - `get_all_commands()`: 获取所有命令

已注册命令：
- `help` → HelpCommand
- `t` → WhisperCommand

### 3. router.py - 命令解析器

**CommandParser** (静态工具类)
- `is_command(message)`: 检查消息是否为命令
- `parse(message)`: 解析命令和参数

### 4. commands/help.py - 帮助命令

**HelpCommand** - `/help` 命令
- 功能：列出所有可用命令及用法
- 参数：无
- 输出：格式化的命令帮助文本

### 5. commands/whisper.py - 私信命令

**WhisperCommand** - `/t` 命令
- 功能：向在线用户发送私密消息
- 用法：`/t @username message` 或 `/t username message`
- 参数校验：
  - 用户名非空
  - 消息非空
  - 目标用户必须在线
  - 不允许给自己发私信
- 输出：私信发送确认或错误信息

## 使用示例

### 用户端命令

1. **获取帮助**
   ```
   /help
   ```
   返回所有可用命令列表

2. **发送私信**
   ```
   /t @alice Hello, this is a private message
   /t bob How are you?
   ```
   - 支持带 `@` 或不带 `@` 的用户名
   - 消息可包含多个单词

### 错误处理场景

| 场景 | 返回消息 |
|------|---------|
| `/unknown` | 未知命令 |
| `/t` | 格式错误，请使用 /t @username message |
| `/t @offline_user msg` | 用户不在线 |
| `/t @self msg` | 不能给自己发私信 |
| `/help extra_arg` | help 命令不接受参数 |

## 消息格式

### 命令请求
```json
{
  "type": "command",
  "text": "/t @alice Hello"
}
```

### 成功响应
```json
{
  "type": "info",
  "text": "Private message sent to alice"
}
```

### 错误响应
```json
{
  "type": "error",
  "text": "Unknown command: /unknown. Use /help for available commands."
}
```

### 私信接收
```json
{
  "type": "private",
  "from": "alice",
  "text": "Hello, this is a private message"
}
```

## 扩展新命令

### 步骤

1. **创建新命令类**
   ```python
   # command/commands/mycommand.py
   from command.base import CommandBase, CommandContext, CommandResponse
   
   class MyCommand(CommandBase):
       @property
       def name(self) -> str:
           return "mycommand"
       
       @property
       def description(self) -> str:
           return "My command description"
       
       @property
       def usage(self) -> str:
           return "/mycommand <args>"
       
       def validate(self, args: list) -> tuple[bool, str]:
           if len(args) < 1:
               return False, "Argument required"
           return True, ""
       
       async def execute(self, context: CommandContext, args: list) -> CommandResponse:
           # 实现命令逻辑
           return CommandResponse(
               success=True,
               message="Success",
               response_type="info"
           )
   ```

2. **在 factory.py 中注册**
   ```python
   from command.commands.mycommand import MyCommand
   
   CommandFactory.register(MyCommand)
   ```

### 示例：禁言命令
```python
class MuteCommand(CommandBase):
    @property
    def name(self) -> str:
        return "mute"
    
    async def execute(self, context: CommandContext, args: list) -> CommandResponse:
        target_user = args[0].lstrip("@")
        # 实现禁言逻辑
        return CommandResponse(
            success=True,
            message=f"User {target_user} has been muted",
            response_type="info"
        )
```

## 集成点

### main.py 中的集成

1. **导入命令系统**
   ```python
   from command import CommandFactory, CommandContext
   ```

2. **命令分派**
   在 `websocket_endpoint` 中，消息处理逻辑：
   ```python
   if message.startswith("/"):
       await handle_command(websocket, username, message)
   else:
       await broadcast_message(f"{username}: {message}")
   ```

3. **handle_command 函数**
   - 解析命令和参数
   - 创建命令实例
   - 执行参数校验
   - 调用命令执行
   - 发送响应

## 参数校验流程

```
消息接收
    ↓
检查"/"前缀 → 是 → 解析命令名和参数
    ↓                     ↓
  否 → 正常广播消息     否 → 未知命令错误
                        ↓
                    参数校验
                        ↓
                    验证失败 → 返回错误
                        ↓
                    验证成功
                        ↓
                    创建上下文
                        ↓
                    执行命令
                        ↓
                    发送响应
```

## 错误处理机制

1. **命令不存在**：快速返回"未知命令"提示
2. **参数验证失败**：返回具体的格式错误信息
3. **业务逻辑错误**：返回执行失败原因（如用户离线）
4. **系统异常**：捕获所有异常，返回通用错误提示

## 性能考虑

- **用户查询**：O(n) 复杂度，通过遍历 user_map 查找（在线用户通常数量小）
- **命令创建**：O(1) 复杂度，工厂模式存储
- **参数解析**：O(m) 复杂度，其中 m 为参数个数

## 安全考虑

1. **自我私信防护**：禁止用户给自己发私信
2. **离线用户检查**：确保私信目标在线
3. **参数校验**：所有用户输入都经过验证
4. **异常捕获**：所有命令执行异常都被捕获并报告

## 客户端集成建议

### JavaScript/WebSocket 客户端示例

```javascript
// 发送命令
function sendCommand(command) {
  websocket.send(command);
}

// 处理响应
websocket.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === "private") {
    console.log(`Private from ${data.from}: ${data.text}`);
  } else if (data.type === "error") {
    console.error(`Error: ${data.text}`);
  } else if (data.type === "info") {
    console.log(`Info: ${data.text}`);
  }
};

// 使用示例
sendCommand("/help");
sendCommand("/t @alice Hello");
```

## 测试建议

1. **命令解析测试**
   - 验证 `/help` 解析正确
   - 验证 `/t @username message` 解析正确
   - 验证参数个数校验

2. **参数验证测试**
   - 无参数时报错
   - 缺少消息时报错
   - 自我私信时报错
   - 离线用户时报错

3. **功能测试**
   - 帮助命令返回正确格式
   - 私信成功发送
   - 私信只发送给目标用户
   - 发送者收到确认消息

4. **错误处理测试**
   - 未知命令处理
   - 异常情况恢复
   - 多个用户并发命令

## 常见问题

**Q: 如何添加命令权限控制？**
A: 在 CommandContext 中添加 user_role 字段，在 validate() 中检查权限。

**Q: 如何实现命令别名？**
A: 在 CommandFactory._commands 中为同一个命令类注册多个名称。

**Q: 如何持久化私信？**
A: 在命令执行时，同时将私信保存到数据库（如 SQLite、PostgreSQL）。

**Q: 支持私信群组吗？**
A: 可以创建 GroupMessageCommand，通过修改目标发送逻辑，向多个用户发送。
