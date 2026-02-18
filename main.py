from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime
import asyncio
import logging
import argparse
from command import CommandFactory, CommandContext
from command.factory import register_builtin_commands
from db import init_db, save_message
from utils import AIAgent, AgentConfig, AgentMessage, AgentCommand

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Register built-in commands
register_builtin_commands()

# In-memory store for connections and usernames
user_map: dict[WebSocket, str] = {}
current_users: set[str] = set()

# AI Agent instance
ai_agent: AIAgent | None = None
AGENT_NAME = "AI"
ai_enabled = True  # Will be set based on OpenAI API key availability

# Initialize database on startup
async def startup_event():
    """Initialize database and AI agent on application startup."""
    global ai_agent, ai_enabled
    try:
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize AI Agent if enabled
        if ai_enabled:
            try:
                ai_provider = os.getenv("AI_PROVIDER", "openai")
                
                if ai_provider == "glm":
                    # Use GLM (Zhipu AI)
                    api_key = os.getenv("GLM_API_KEY")
                    if not api_key:
                        logger.warning("GLM_API_KEY not set. AI Agent disabled.")
                        ai_enabled = False
                    else:
                        config = AgentConfig(
                            glm_api_key=api_key,
                            agent_name=AGENT_NAME,
                            model=os.getenv("GLM_MODEL", "glm-4-flash-250414"),
                            temperature=float(os.getenv("GLM_TEMPERATURE", "0.7")),
                            max_tokens=int(os.getenv("GLM_MAX_TOKENS", "500")),
                            timeout=int(os.getenv("GLM_TIMEOUT", "30")),
                            retry_attempts=int(os.getenv("GLM_RETRY_ATTEMPTS", "3")),
                            ai_provider="glm"
                        )
                        ai_agent = AIAgent(config)
                        logger.info(f"AI Agent object created: {ai_agent}")
                        
                        # Test connection
                        if await ai_agent.health_check():
                            logger.info("GLM AI Agent initialized successfully")
                            logger.info(f"AI Agent variable after initialization: ai_agent={ai_agent is not None}")
                        else:
                            logger.warning("GLM AI Agent health check failed")
                else:
                    # Default to OpenAI
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        logger.warning("OPENAI_API_KEY not set. AI Agent disabled.")
                        ai_enabled = False
                    else:
                        config = AgentConfig(
                            openai_api_key=api_key,
                            agent_name=AGENT_NAME,
                            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
                            timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
                            retry_attempts=int(os.getenv("OPENAI_RETRY_ATTEMPTS", "3")),
                            ai_provider="openai"
                        )
                        ai_agent = AIAgent(config)
                        logger.info(f"AI Agent object created: {ai_agent}")
                        
                        # Test connection
                        if await ai_agent.health_check():
                            logger.info("OpenAI Agent initialized successfully")
                            logger.info(f"AI Agent variable after initialization: ai_agent={ai_agent is not None}")
                        else:
                            logger.warning("OpenAI Agent health check failed")
            except Exception as e:
                logger.error(f"Failed to initialize AI Agent: {e}", exc_info=True)
                ai_enabled = False
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
    
    logger.info(f"Startup event completed: ai_agent={ai_agent is not None}, ai_enabled={ai_enabled}")

def get_timestamp() -> str:
    """Get current time in HH:mm:ss format"""
    return datetime.now().strftime("%H:%M:%S")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            # First message is treated as username if not yet set
            if websocket not in user_map:
                username = data.strip()
                if not username:
                    await websocket.send_text(json.dumps({"type":"error","text":"Username cannot be empty."}))
                    continue
                if username in current_users:
                    await websocket.send_text(json.dumps({"type":"error","text":"Username already taken. Choose another."}))
                    continue
                user_map[websocket] = username
                current_users.add(username)
                await broadcast_user_list()
                await websocket.send_text(json.dumps({"type":"info","text":f"Welcome, {username}!"}))
                logger.info(f"User {username} joined the chat")
            else:
                username = user_map[websocket]
                message = data.strip()
                logger.info(f"User {username} sent message: {message}")
                logger.info(f"Global variables during message: ai_enabled={ai_enabled}, ai_agent={ai_agent is not None}")
                
                # Safety check: if ai_enabled is True but ai_agent is None, try to reinitialize
                if ai_enabled and ai_agent is None:
                    logger.warning("AI is enabled but agent is None, attempting to reinitialize...")
                    await startup_event()
                
                if message:
                    # Check if message is a command (starts with /)
                    if message.startswith("/"):
                        await handle_command(websocket, username, message)
                    else:
                        await broadcast_message(f"{username}: {message}")
                else:
                    logger.warning(f"Empty message from {username}, skipping")
    except WebSocketDisconnect:
        if websocket in user_map:
            username = user_map.pop(websocket)
            current_users.discard(username)
            await broadcast_user_list()
        print("Client disconnected")

@app.get("/api/history")
async def get_chat_history(
    limit: int = 50,
    offset: int = 0,
    username: str | None = None,
    keyword: str | None = None
):
    """
    Retrieve chat history with optional filters.
    
    Query Parameters:
        - limit: Number of messages to retrieve (default: 50, max: 500)
        - offset: Pagination offset (default: 0)
        - username: Filter by username (optional)
        - keyword: Search keyword in message content (optional)
    """
    try:
        from db import get_history
        
        # Validate limit
        limit = min(int(limit), 500)
        offset = max(int(offset), 0)
        
        messages, total_count = await get_history(
            limit=limit,
            offset=offset,
            username=username,
            keyword=keyword
        )
        
        return {
            "success": True,
            "messages": messages,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return {
            "success": False,
            "error": str(e),
            "messages": []
        }

@app.get("/api/history/initial")
async def get_initial_history(limit: int = 20):
    """
    Retrieve initial chat history for startup display.
    Returns the most recent messages in reverse chronological order.
    
    Query Parameters:
        - limit: Number of messages to retrieve (default: 20, max: 50)
    """
    try:
        from db import get_history
        
        # Validate limit for initial load
        limit = min(int(limit), 50)
        
        # Get most recent messages (reverse order for startup display)
        messages, total_count = await get_history(
            limit=limit,
            offset=0,
            username=None,
            keyword=None
        )
        
        return {
            "success": True,
            "messages": list(reversed(messages)),  # Reverse to show oldest first
            "total": total_count,
            "has_more": total_count > limit
        }
    except Exception as e:
        logger.error(f"Error retrieving initial history: {e}")
        return {
            "success": False,
            "error": str(e),
            "messages": [],
            "has_more": False
        }

@app.get("/api/users")
async def get_online_users():
    """
    Get list of currently online users.
    
    Returns:
        {
            "success": true,
            "users": ["user1", "user2", ...],
            "count": number
        }
    """
    try:
        users_list = sorted(list(current_users))
        return {
            "success": True,
            "users": users_list,
            "count": len(users_list)
        }
    except Exception as e:
        logger.error(f"Error retrieving users list: {e}")
        return {
            "success": False,
            "error": str(e),
            "users": [],
            "count": 0
        }

@app.post("/upload")
async def upload_image(file: UploadFile):
    """Upload an image file with security validation."""
    if not file.content_type:
        return {"error": "No file uploaded"}
    if not file.content_type.startswith("image/"):
        return {"error": "Only image files are allowed."}
    
    # Handle None filename and sanitize for security
    if not file.filename:
        return {"error": "File must have a name"}
    
    # Remove directory traversal attempts and sanitize filename
    filename = os.path.basename(file.filename.strip())
    if not filename or filename.startswith('.') or '/' in filename or '\\' in filename:
        return {"error": "Invalid filename"}
    
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            _ = buffer.write(content)
        return {"url": f"/static/uploads/{filename}"}
    except Exception as e:
        return {"error": f"Failed to save file: {str(e)}"}

async def broadcast_user_list():
    payload = json.dumps({"type":"userlist","users":list(current_users)})
    for ws in list(user_map.keys()):
        await ws.send_text(payload)

async def broadcast_message(message: str):
    timestamp = get_timestamp()
    payload = json.dumps({
        "type": "message",
        "text": message,
        "timestamp": timestamp
    })
    logger.debug(f"Broadcasting message to {len(user_map)} users: {message}")
    for ws in list(user_map.keys()):
        await ws.send_text(payload)
    
    # Persist message to database
    # Parse username from message (format: "username: content")
    parts = message.split(":", 1)
    if len(parts) == 2:
        username = parts[0].strip()
        content = parts[1].strip()
        # Save to database asynchronously without blocking
        asyncio.create_task(save_message(username, content, timestamp))
    
    # Process with AI Agent if enabled and message is from a real user
    logger.info(f"Checking AI processing conditions: ai_enabled={ai_enabled}, ai_agent={ai_agent is not None}, parts_len={len(parts)}")
    if ai_enabled and ai_agent and len(parts) == 2:
        username = parts[0].strip()
        content = parts[1].strip()
        
        # Don't reply to AI's own messages
        if username != AGENT_NAME:
            logger.info(f"Triggering AI response for user {username} with content: {content}")
            asyncio.create_task(
                _process_ai_response(username, content, timestamp)
            )
        else:
            logger.info(f"Skipping AI response for AI's own message from {username}")
    else:
        logger.info("AI processing conditions not met, skipping AI response")

async def handle_command(websocket: WebSocket, username: str, message: str):
    """Parse and execute a command."""
    try:
        # Remove leading slash and split into command and arguments
        command_text = message[1:].strip()
        if not command_text:
            error_response = json.dumps({
                "type": "error",
                "text": "Empty command. Use /help for available commands."
            })
            await websocket.send_text(error_response)
            return
        
        parts = command_text.split(maxsplit=1)
        command_name = parts[0].lower()
        args_text = parts[1] if len(parts) > 1 else ""
        
        # Parse arguments (handle quoted strings and @ prefixes)
        args = []
        if args_text:
            # Simple argument parser: split by spaces but preserve @ prefix
            args = args_text.split()
        
        # Try to create and execute command
        try:
            command = CommandFactory.create(command_name)
        except KeyError:
            error_response = json.dumps({
                "type": "error",
                "text": f"Unknown command: /{command_name}. Use /help for available commands."
            })
            await websocket.send_text(error_response)
            return
        
        # Validate command arguments
        is_valid, error_msg = command.validate(args)
        if not is_valid:
            error_response = json.dumps({
                "type": "error",
                "text": f"Invalid arguments: {error_msg}"
            })
            await websocket.send_text(error_response)
            return
        
        # Create command context
        context = CommandContext(
            websocket=websocket,
            username=username,
            user_map=user_map,
            current_users=current_users
        )
        
        # Execute command
        response = await command.execute(context, args)
        
        # Send response to user
        response_payload = {
            "type": response.response_type,
            "text": response.message
        }
        await websocket.send_text(json.dumps(response_payload))
    
    except Exception as e:
        error_response = json.dumps({
            "type": "error",
            "text": f"Command execution error: {str(e)}"
        })
        await websocket.send_text(error_response)

async def _process_ai_response(username: str, content: str, timestamp: str):
    """
    Process AI response to user message asynchronously.
    
    Args:
        username: Username of the sender
        content: Message content
        timestamp: Message timestamp
    """
    global ai_agent
    
    if not ai_agent:
        logger.warning("AI Agent not initialized, skipping AI response")
        return
    
    if not ai_enabled:
        logger.warning("AI not enabled, skipping AI response")
        return
    
    logger.info(f"Processing AI response for message from {username}: {content}")
    
    try:
        # Update AI's user list
        await ai_agent.update_user_list(sorted(list(current_users)))
        
        # Create message for AI to process
        user_message = AgentMessage(
            username=username,
            content=content,
            message_type="normal",
            timestamp=timestamp
        )
        
        # Get available commands
        available_commands = list(CommandFactory.get_all_commands().keys())
        
        # Process message with AI
        ai_response = await ai_agent.process_message(
            user_message,
            sorted(list(current_users)),
            available_commands
        )
        
        if not ai_response.success:
            logger.warning(f"AI processing failed: {ai_response.message}")
            return
        
        logger.info(f"AI generated response: type={ai_response.response_type}, message={ai_response.message}")
        
        # Handle different response types
        if ai_response.response_type == "command":
            # AI wants to execute a command
            if ai_response.command:
                await _execute_ai_command(ai_response.command)
        elif ai_response.response_type == "private":
            # AI wants to send a private message
            await _send_ai_private_message(username, ai_response.message)
        else:
            # AI wants to broadcast a reply
            logger.info(f"Broadcasting AI message: {ai_response.message}")
            await broadcast_message(f"{AGENT_NAME}: {ai_response.message}")
    
    except Exception as e:
        logger.error(f"Error processing AI response: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Error processing AI response: {e}")

async def _execute_ai_command(command: 'AgentCommand') -> None:
    """
    Execute a command on behalf of the AI agent.
    
    Args:
        command: AgentCommand instance
    """
    try:
        # Get the command from factory
        cmd = CommandFactory.create(command.command_name)
        
        # Validate arguments
        is_valid, error_msg = cmd.validate(command.args)
        if not is_valid:
            logger.warning(f"AI command validation failed: {error_msg}")
            return
        
        # Create context for AI
        # Find a WebSocket connection (or use None if no real user connection available)
        # For commands that don't need WebSocket (like /help), we can use a mock
        context = CommandContext(
            websocket=None,
            username=AGENT_NAME,
            user_map=user_map,
            current_users=current_users
        )
        
        # Execute the command
        response = await cmd.execute(context, command.args)
        
        # Handle response
        if response.success:
            if response.response_type == "private" and response.target_user:
                # Send private message response
                for ws, uname in user_map.items():
                    if uname == response.target_user:
                        private_payload = json.dumps({
                            "type": "private",
                            "from": AGENT_NAME,
                            "text": response.message
                        })
                        await ws.send_text(private_payload)
                        break
            else:
                # Broadcast command result
                await broadcast_message(f"{AGENT_NAME}: {response.message}")
        else:
            logger.warning(f"AI command execution failed: {response.message}")
    
    except Exception as e:
        logger.error(f"Error executing AI command: {e}")

async def _send_ai_private_message(target_username: str, message: str):
    """
    Send a private message from AI to a user.
    
    Args:
        target_username: Target user's username
        message: Message content
    """
    try:
        if target_username == AGENT_NAME:
            logger.warning("AI tried to send message to itself")
            return
        
        if target_username not in current_users:
            logger.warning(f"Target user {target_username} not online")
            return
        
        # Find target user's WebSocket
        for ws, username in user_map.items():
            if username == target_username:
                private_payload = json.dumps({
                    "type": "private",
                    "from": AGENT_NAME,
                    "text": message
                })
                await ws.send_text(private_payload)
                logger.info(f"AI sent private message to {target_username}")
                break
    
    except Exception as e:
        logger.error(f"Error sending AI private message: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FastAPI Chatroom Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host IP to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    args = parser.parse_args()
    
    asyncio.run(startup_event())
    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)
