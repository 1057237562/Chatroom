# 命令系统快速开始

## 系统已支持的命令

### 1. 帮助命令 `/help`
显示所有可用命令及其用法。

**用法：**
```
/help
```

**响应示例：**
```
=== Available Commands ===

/help
  Show help information about available commands

/t @username <message>
  Send a private message to a user
```

### 2. 私信命令 `/t`
向在线用户发送私密消息。

**用法：**
```
/t @username 消息内容
/t username 消息内容
```

**示例：**
```
/t @alice Hello Alice, how are you?
/t bob What's up?
/t @charlie This is a multi-word private message
```

**说明：**
- 用户名前可加或不加 `@` 符号
- 消息可包含多个单词
- 只有目标用户能看到私信
- 发送者会收到确认信息

## 错误处理

系统会在以下情况返回错误提示：

| 错误场景 | 返回信息 |
|---------|---------|
| 使用不存在的命令 | `Unknown command: /xxx. Use /help for available commands.` |
| 命令格式错误 | `Invalid format. Usage: /t @username <message>` |
| 私信目标不存在 | `User 'username' is not online` |
| 给自己发私信 | `You cannot send a private message to yourself` |
| 消息为空 | `Message cannot be empty` |

## 工作流程

```
1. 用户在聊天框输入消息
   ↓
2. 系统检测 "/" 前缀
   ├─ 是 → 识别为命令
   └─ 否 → 按普通消息广播
   ↓
3. 命令解析（提取命令名和参数）
   ↓
4. 工厂创建对应命令实例
   ↓
5. 参数校验
   ├─ 失败 → 返回错误信息
   └─ 成功 → 执行命令
   ↓
6. 命令执行
   ├─ 帮助命令 → 返回命令列表
   └─ 私信命令 → 发送私信到目标用户
   ↓
7. 发送响应给用户
```

## 代码架构

```
command/
├── base.py              # 基础类和接口定义
│   ├── CommandBase      # 抽象基类
│   ├── CommandContext   # 命令上下文
│   └── CommandResponse  # 命令响应
├── factory.py           # 命令工厂
│   └── CommandFactory   # 工厂类
├── router.py            # 命令解析器
│   └── CommandParser    # 解析工具
└── commands/
    ├── help.py          # /help 命令
    └── whisper.py       # /t 私信命令
```

## 如何扩展新命令

假设要添加 `/kick @username` 命令：

**第 1 步：创建命令类**

创建 `command/commands/kick.py`：
```python
from command.base import CommandBase, CommandContext, CommandResponse

class KickCommand(CommandBase):
    @property
    def name(self) -> str:
        return "kick"
    
    @property
    def description(self) -> str:
        return "Remove a user from the chat"
    
    @property
    def usage(self) -> str:
        return "/kick @username"
    
    def validate(self, args: list) -> tuple[bool, str]:
        if len(args) < 1:
            return False, "Usage: /kick @username"
        return True, ""
    
    async def execute(self, context: CommandContext, args: list) -> CommandResponse:
        target_user = args[0].lstrip("@")
        
        # 检查用户是否存在
        if target_user not in context.current_users:
            return CommandResponse(
                success=False,
                message=f"User '{target_user}' not found",
                response_type="error"
            )
        
        # 查找并关闭用户连接
        for ws, username in context.user_map.items():
            if username == target_user:
                await ws.close()
                break
        
        return CommandResponse(
            success=True,
            message=f"User '{target_user}' has been kicked",
            response_type="info"
        )
```

**第 2 步：注册命令**

在 `command/factory.py` 中：
```python
from command.commands.kick import KickCommand

# 在文件末尾添加：
CommandFactory.register(KickCommand)
```

**第 3 步：完成！**

现在就可以使用 `/kick @username` 命令了。

## 主程序集成

命令系统已完全集成到 `main.py` 中：

- 第 7 行：导入命令系统
- 第 44-47 行：检测命令前缀并分派处理
- 第 77-144 行：命令执行和响应处理

## 测试命令系统

### 方法 1：使用 WebSocket 客户端

```javascript
// 在浏览器控制台运行
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = function() {
    // 发送用户名
    ws.send('alice');
    
    // 发送帮助命令
    setTimeout(() => ws.send('/help'), 100);
    
    // 发送私信命令
    setTimeout(() => ws.send('/t @bob Hello'), 200);
};

ws.onmessage = function(event) {
    console.log('Received:', JSON.parse(event.data));
};
```

### 方法 2：使用多个浏览器标签

1. 打开多个浏览器标签连接到聊天室
2. 分别输入不同用户名（alice, bob, charlie 等）
3. 在一个标签中输入 `/t @alice Hello`
4. 在 alice 的标签中应该看到私信

## 常见命令示例

```
# 查看帮助
/help

# 向 alice 发送私信
/t @alice Hi, how are you?

# 向 bob 发送问候（不用 @）
/t bob Good morning!

# 发送包含多个单词的私信
/t @charlie This is a longer message with multiple words
```

## 调试技巧

### 查看错误提示

如果命令执行失败，系统会返回详细的错误信息：

- 命令不存在 → 提示使用 `/help`
- 格式错误 → 提示正确的用法
- 用户不在线 → 显示具体哪个用户离线

### 监控 WebSocket 通信

在浏览器开发者工具中：
1. 打开 Network 标签
2. 筛选 WebSocket 连接
3. 在 Messages 子标签中查看所有消息交互

## 性能优化建议

1. **缓存用户列表**（当用户量大时）
2. **异步任务队列**（处理耗时命令）
3. **命令速率限制**（防止滥用）
4. **持久化存储**（保存私信记录）
