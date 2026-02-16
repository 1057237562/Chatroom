# Agent Utils - Quick Start Guide

## 5-Minute Setup

### 1. Get OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy it somewhere safe

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variable

**On macOS/Linux:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

**On Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-your-api-key-here"
```

**Or create `.env` file:**
```
OPENAI_API_KEY=sk-your-api-key-here
```

### 4. Run the Application

```bash
python main.py
```

Visit `http://localhost:8000` in your browser.

### 5. Chat with AI

1. Open the chatroom in two browser windows
2. One window: log in as "Alice"
3. Other window: log in as "Bob"
4. AI will automatically join and participate

## Testing the Integration

### Run Full Test Suite

```bash
python test_agent_integration.py
```

### Quick Manual Test

```python
import asyncio
from utils import AIAgent, AgentConfig, AgentMessage
import os

async def test():
    config = AgentConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        agent_name="TestBot"
    )
    agent = AIAgent(config)
    
    # Test health check
    is_healthy = await agent.health_check()
    print(f"API Status: {'✓ OK' if is_healthy else '❌ Failed'}")
    
    # Process a message
    message = AgentMessage(
        username="user",
        content="Hello, what's the weather?",
        message_type="normal"
    )
    response = await agent.process_message(
        message,
        current_users=["user", "TestBot"],
        available_commands=["help", "t"]
    )
    print(f"AI Response: {response.message}")

asyncio.run(test())
```

## Common Commands in Chatroom

### Get AI Help
```
/help
```

### Send AI a Private Message
```
/t @AI Hello, I have a question
```

### Get Current Users
```
GET http://localhost:8000/api/users
```

## File Structure

New files created for Agent Utils:

```
utils/
├── __init__.py              # Package exports
├── types.py                 # 6 data classes (AgentConfig, AgentMessage, etc.)
├── prompts.py               # System prompts for AI behavior
└── agent.py                 # Main AIAgent class (~350 lines)

Modified files:
├── main.py                  # Added AI initialization and integration
├── command/base.py          # Updated CommandContext for optional WebSocket
└── requirements.txt         # Added openai>=1.0.0

Documentation:
├── AGENT_UTILS.md           # Comprehensive documentation
├── AGENT_QUICKSTART.md      # This file
├── .env.example             # Configuration template
└── test_agent_integration.py # Integration tests
```

## Configuration Options

Edit `.env` file to customize:

```env
# API Key (required)
OPENAI_API_KEY=sk-...

# Model (default: gpt-3.5-turbo)
# Options: gpt-4, gpt-4-turbo, gpt-3.5-turbo
OPENAI_MODEL=gpt-3.5-turbo

# Temperature: 0-2 (default: 0.7)
# Lower = more focused, Higher = more creative
OPENAI_TEMPERATURE=0.7

# Max response length (default: 500)
OPENAI_MAX_TOKENS=500

# API timeout in seconds (default: 30)
OPENAI_TIMEOUT=30

# Retry attempts for failed requests (default: 3)
OPENAI_RETRY_ATTEMPTS=3
```

## Features Overview

✅ **Natural Conversations**
- AI understands context and responds naturally
- Participates in public chat

✅ **Command Support**
- Execute `/help` to see commands
- Send `/t @username message` for private messages
- AI can execute any available command

✅ **Private Messaging**
- Send AI private messages with `/t @AI message`
- AI responds privately back to you

✅ **User Awareness**
- AI knows who's online
- Personalizes responses based on context

✅ **Robust Error Handling**
- Automatic retry on API failures
- Graceful degradation if API unavailable
- Detailed logging for debugging

✅ **High Performance**
- Async processing (non-blocking)
- Message caching to reduce API calls
- Connection pooling for efficiency

## Troubleshooting

### "OPENAI_API_KEY not set" Error

**Solution:** Set the environment variable
```bash
export OPENAI_API_KEY="your-key-here"
```

### AI Not Responding

1. **Check API Key validity** - Test on [platform.openai.com](https://platform.openai.com)
2. **Check account balance** - May need OpenAI credits
3. **Check logs** - Run with `python -u main.py` to see output
4. **Run health check** - Execute `python test_agent_integration.py`

### Slow Responses

1. **Reduce max tokens** - `OPENAI_MAX_TOKENS=200`
2. **Lower temperature** - `OPENAI_TEMPERATURE=0.3`
3. **Check network** - May be API latency

### Rate Limiting

If getting rate limit errors:
1. Increase `OPENAI_RETRY_ATTEMPTS=5`
2. Reduce message frequency
3. Upgrade OpenAI plan for higher limits

## Next Steps

1. **Customize AI Behavior** - Edit `utils/prompts.py`
2. **Add Custom Commands** - Follow existing command patterns
3. **Extend AI Capabilities** - Subclass `AIAgent`
4. **Monitor Usage** - Check OpenAI dashboard for API usage

## Support Resources

- **OpenAI API Docs**: https://platform.openai.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Python asyncio**: https://docs.python.org/3/library/asyncio.html

## Example: Custom AI Personality

Edit `utils/prompts.py`:

```python
SYSTEM_PROMPT = """You are a helpful Python programming assistant named CodeBot.
You specialize in helping developers with Python code questions.

Current online users: {current_users}

Guidelines:
- Provide clear, concise code examples
- Always explain your solutions
- Suggest best practices
- Be friendly and encouraging
"""
```

Then restart the application:
```bash
python main.py
```

## Performance Tips

### For Production

```env
OPENAI_MODEL=gpt-4-turbo
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.5
OPENAI_TIMEOUT=60
```

### For Development

```env
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=200
OPENAI_TEMPERATURE=0.8
OPENAI_TIMEOUT=15
```

## Security Checklist

- [ ] Never commit `.env` to git
- [ ] Use environment variables for API key
- [ ] Rotate API key regularly
- [ ] Monitor usage in OpenAI dashboard
- [ ] Review chatroom data privacy
- [ ] Set API key spending limits

## That's It!

Your chatroom now has AI capabilities. Start chatting! 🚀

For more details, see:
- `AGENT_UTILS.md` - Complete documentation
- `test_agent_integration.py` - Test examples
- `utils/agent.py` - Source code comments
