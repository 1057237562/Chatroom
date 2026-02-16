# Agent Utils Module - OpenAI Integration Guide

## Overview

The Agent Utils module provides AI agent capabilities for the chatroom application using OpenAI's GPT API. The AI agent can participate in conversations, execute commands, and interact with users through private messages.

## Features

- **Natural Language Processing**: AI understands and responds to user messages
- **Command Execution**: AI can execute all available chatroom commands (/help, /t, etc.)
- **Private Messaging**: AI can receive and respond to private messages
- **User List Access**: AI has access to the current list of online users
- **Robust Error Handling**: Handles API failures, timeouts, and rate limiting
- **Async Processing**: Non-blocking AI processing to maintain chat responsiveness

## Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   The requirements now include: `openai>=1.0.0`

2. **Set up OpenAI API Key**
   
   Create a `.env` file or set environment variables:
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

   Or copy and configure `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

## Configuration

The AI agent is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Your OpenAI API key (required) |
| `OPENAI_MODEL` | gpt-3.5-turbo | OpenAI model to use |
| `OPENAI_TEMPERATURE` | 0.7 | Response creativity (0.0-2.0) |
| `OPENAI_MAX_TOKENS` | 500 | Max response length |
| `OPENAI_TIMEOUT` | 30 | API call timeout in seconds |
| `OPENAI_RETRY_ATTEMPTS` | 3 | Number of retries for failed API calls |

### Example .env Configuration

```env
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.8
OPENAI_MAX_TOKENS=300
OPENAI_TIMEOUT=20
OPENAI_RETRY_ATTEMPTS=2
```

## Architecture

### Module Structure

```
utils/
├── __init__.py          # Package exports
├── types.py             # Data types (AgentConfig, AgentMessage, etc.)
├── prompts.py           # System prompts and instruction management
└── agent.py             # Core AIAgent class with OpenAI integration
```

### Key Components

1. **AIAgent Class** (`utils/agent.py`)
   - Main interface for AI functionality
   - Manages OpenAI API communication
   - Handles message processing and command execution
   - Implements retry logic and error handling

2. **AgentConfig** (`utils/types.py`)
   - Configuration dataclass for AI settings
   - Includes API key, model, temperature, timeouts, etc.

3. **Message Types** (`utils/types.py`)
   - `AgentMessage`: Incoming user message
   - `AgentResponse`: AI's response
   - `AgentCommand`: Command for AI to execute

4. **System Prompts** (`utils/prompts.py`)
   - Central management of AI behavior instructions
   - Customizable per use case

## API Reference

### AIAgent Class Methods

#### `__init__(config: AgentConfig)`
Initialize the AI agent with configuration.

```python
from utils import AIAgent, AgentConfig

config = AgentConfig(
    openai_api_key="sk-...",
    model="gpt-3.5-turbo",
    temperature=0.7
)
agent = AIAgent(config)
```

#### `async process_message(message, current_users, available_commands) -> AgentResponse`
Process a user message and generate AI response.

```python
from utils import AgentMessage

user_msg = AgentMessage(
    username="alice",
    content="Hello AI, how are you?",
    message_type="normal"
)

response = await agent.process_message(
    user_msg,
    current_users=["alice", "bob"],
    available_commands=["help", "t"]
)

print(response.message)  # AI's response
print(response.response_type)  # "info", "error", "private", "command"
```

#### `async update_user_list(users: list[str])`
Update the list of currently online users.

```python
await agent.update_user_list(["alice", "bob", "charlie"])
```

#### `async get_users() -> list[str]`
Get the current list of online users known to the agent.

```python
users = await agent.get_users()
print(users)  # ["alice", "bob"]
```

#### `async health_check() -> bool`
Test if OpenAI API is accessible.

```python
is_healthy = await agent.health_check()
if is_healthy:
    print("AI Agent is ready")
else:
    print("AI Agent connection failed")
```

#### `clear_cache() -> None`
Clear the message cache.

```python
agent.clear_cache()
```

### HTTP API

#### `GET /api/users`
Get list of currently online users.

**Response:**
```json
{
  "success": true,
  "users": ["alice", "bob", "charlie"],
  "count": 3
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "users": [],
  "count": 0
}
```

## Integration with Chatroom

### How the AI Participates

1. **User sends a message** to the chatroom
2. **broadcast_message()** broadcasts the message to all users
3. **_process_ai_response()** is triggered asynchronously
4. **AIAgent processes** the message via OpenAI API
5. **Response is handled** based on type:
   - `info`: AI replies in public chat
   - `private`: AI sends private message to user
   - `command`: AI executes a command
   - `error`: Error is logged

### Command Execution Flow

The AI can execute commands just like regular users:

```
User: "hello AI"
AI: [processes message, decides to ask for help]
AI: "/help"
ChatRoom: [executes /help command]
AI: [receives command results, broadcasts them]
```

### Private Message Flow

```
User: "/t @AI Can you help me?"
AI: [processes private message]
AI: [generates response]
AI: [sends private reply to user]
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User Input                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │  WebSocket Handler     │
          │  - Parse message       │
          │  - Route to command    │
          └────────────┬───────────┘
                       │
           ┌───────────┴────────────┐
           │                        │
           ▼                        ▼
      ┌─────────┐          ┌──────────────┐
      │ Command │          │ Broadcast    │
      │ Handler │          │ Message      │
      └─────────┘          └──────┬───────┘
                                  │
                    ┌─────────────┴─────────┐
                    │                       │
                    ▼                       ▼
            ┌──────────────┐    ┌────────────────────┐
            │ Database     │    │ _process_ai_       │
            │ Persist      │    │ response()         │
            │ Message      │    └────┬───────────────┘
            └──────────────┘         │
                                     ▼
                          ┌────────────────────┐
                          │ AIAgent            │
                          │ - Call OpenAI API  │
                          │ - Parse response   │
                          └────┬───────────────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │Broadcast│ │ Private │ │ Command │
              │ Public  │ │ Message │ │ Execute │
              │ Reply   │ │         │ │         │
              └─────────┘ └─────────┘ └─────────┘
```

## Error Handling

The AI agent implements robust error handling:

### OpenAI API Errors

- **Rate Limiting** (`RateLimitError`): Automatic retry with exponential backoff
- **Connection Error** (`APIConnectionError`): Automatic retry, fallback message
- **Timeout** (`Timeout`): Automatic retry, user-friendly error message
- **General API Error** (`APIError`): Logged and reported to user

### Graceful Degradation

If OpenAI API is unavailable:
1. System logs the error
2. User receives a friendly error message
3. Chat continues to function normally
4. Other users' messages are not affected

### Retry Logic

- Exponential backoff: `delay * (2 ^ (attempt - 1))`
- Default: 3 retry attempts with 1-second initial delay
- Configurable via `OPENAI_RETRY_ATTEMPTS` and retry settings

## Performance Considerations

### Caching

The AI agent caches recent responses to avoid duplicate API calls:
- Cache key: `{username}:{message}`
- Limited to 100 entries (automatically cleared when full)
- Use `agent.clear_cache()` to manually clear

### Async Processing

- Message processing happens asynchronously
- AI responses don't block the chat
- Multiple messages can be processed concurrently

### Optimization Tips

1. **Adjust OPENAI_MAX_TOKENS** based on response length needs
2. **Increase OPENAI_TIMEOUT** for slower connections
3. **Lower OPENAI_TEMPERATURE** for more deterministic responses
4. **Use faster models** like `gpt-3.5-turbo` for latency-sensitive use

## Troubleshooting

### AI Agent Not Responding

1. **Check API Key**: Ensure `OPENAI_API_KEY` is set correctly
2. **Check Logs**: Look for errors in application logs
3. **Test Health**: Call `/api/test-ai-health` or check logs for "Health check" messages
4. **Verify Users**: Ensure users are actually online with `/api/users`

### API Rate Limiting

If seeing rate limit errors:
1. Reduce `OPENAI_MAX_TOKENS` to reduce API usage
2. Increase `OPENAI_RETRY_ATTEMPTS` or use longer delays
3. Consider using a higher-tier OpenAI account

### Slow Responses

1. Check network latency with `OPENAI_TIMEOUT`
2. Try a faster model: `OPENAI_MODEL=gpt-3.5-turbo`
3. Lower `OPENAI_MAX_TOKENS` for shorter responses
4. Verify server load and OpenAI API status

### AI Behaves Oddly

1. Adjust `OPENAI_TEMPERATURE` (lower = more consistent, higher = more creative)
2. Check the system prompt in `utils/prompts.py`
3. Clear cache with `agent.clear_cache()`
4. Review recent API responses in logs

## Advanced Usage

### Custom System Prompts

Edit `utils/prompts.py` to customize AI behavior:

```python
SYSTEM_PROMPT = """You are a helpful assistant...
[Your custom instructions here]
"""
```

### Extending AIAgent

Create a custom agent class:

```python
from utils import AIAgent, AgentConfig

class CustomAgent(AIAgent):
    async def process_message(self, message, current_users, available_commands):
        # Your custom logic here
        return await super().process_message(
            message, current_users, available_commands
        )
```

### Disabling AI Agent

Set the environment variable or modify `main.py`:
- Remove `OPENAI_API_KEY` environment variable
- Or set `ai_enabled = False` in `main.py`

## Security Considerations

1. **API Key Protection**:
   - Never commit `.env` file to version control
   - Use environment variables or secure vaults
   - Rotate API keys regularly

2. **Input Validation**:
   - All user inputs are validated before processing
   - AI responses are checked before broadcasting

3. **Rate Limiting**:
   - Monitor OpenAI API usage
   - Implement usage limits if needed
   - Use API key with spending limits

4. **Data Privacy**:
   - Chatroom messages are sent to OpenAI
   - Review OpenAI's privacy policy
   - Ensure compliance with data regulations

## License

This module follows the same license as the main chatroom application.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Consult OpenAI API documentation
4. Check GitHub issues or documentation
