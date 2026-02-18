from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import uvicorn
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime
import asyncio
import logging
from dotenv import load_dotenv
from command import CommandFactory, CommandContext
from command.factory import register_builtin_commands
from db import init_db, save_message
from utils import AIAgent, AgentConfig, AgentMessage, AgentCommand
from voice_chat import VoiceChatManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

register_builtin_commands()

user_map: dict[WebSocket, str] = {}
current_users: set[str] = set()

voice_manager = VoiceChatManager()

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
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not set. AI Agent disabled.")
                    ai_enabled = False
                else:
                    config = AgentConfig(
                        openai_api_key=api_key,
                        agent_name=AGENT_NAME,
                        model=os.getenv("OPENAI_MODEL", "glm-4.7-flash"),
                        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
                        timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
                        retry_attempts=int(os.getenv("OPENAI_RETRY_ATTEMPTS", "3")),
                        base_url=os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
                    )
                    ai_agent = AIAgent(config)
                    
                    # Test connection
                    if await ai_agent.health_check():
                        logger.info("AI Agent initialized successfully")
                    else:
                        logger.warning("AI Agent health check failed")
            except Exception as e:
                logger.error(f"Failed to initialize AI Agent: {e}")
                ai_enabled = False
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def get_timestamp() -> str:
    """Get current time in HH:mm:ss format"""
    return datetime.now().strftime("%H:%M:%S")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
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
            else:
                username = user_map[websocket]
                message = data.strip()
                if message:
                    # Check if message is a command (starts with /)
                    if message.startswith("/"):
                        await handle_command(websocket, username, message)
                    else:
                        await broadcast_message(f"{username}: {message}")
    except WebSocketDisconnect:
        if websocket in user_map:
            username = user_map.pop(websocket)
            current_users.discard(username)
            await broadcast_user_list()
        print("Client disconnected")

@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    room = None
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "join":
                    username = message.get("username")
                    room_id = message.get("room_id", "default")
                    
                    if username:
                        room = await voice_manager.join_room(room_id, username, websocket)
                        logger.info(f"User {username} joined voice room {room_id}")
                        
                elif msg_type == "audio":
                    if username and room:
                        audio_data = message.get("data", [])
                        if audio_data:
                            await room.broadcast_audio(username, audio_data)
                
                elif msg_type == "screen_start":
                    if username and room:
                        success = await room.start_screen_share(username)
                        if not success:
                            await websocket.send_json({
                                "type": "screen_error",
                                "message": "Screen share already active by another user"
                            })
                
                elif msg_type == "screen_stop":
                    if username and room:
                        await room.stop_screen_share(username)
                
                elif msg_type == "screen_frame":
                    if username and room:
                        frame_data = message.get("data")
                        if frame_data:
                            # logger.info(f"Received screen frame from {username}, size: {len(frame_data)}")
                            await room.broadcast_screen_frame(username, frame_data)
                            
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received on voice endpoint")
                
    except WebSocketDisconnect:
        if username:
            await voice_manager.leave_room(username)
            logger.info(f"Voice client disconnected: {username}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        if username:
            await voice_manager.leave_room(username)

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

@app.get("/api/commands")
async def get_commands(query: str = "", match_type: str = "prefix"):
    """
    Get available commands with optional filtering.
    
    Query Parameters:
        - query: Search query for command matching (optional)
        - match_type: Matching algorithm - "prefix", "fuzzy", or "all" (default: "prefix")
    
    Returns:
        {
            "success": true,
            "commands": [
                {
                    "name": "help",
                    "description": "...",
                    "usage": "/help",
                    "match_score": 1.0
                },
                ...
            ]
        }
    """
    try:
        commands = CommandFactory.get_all_commands()
        results = []
        
        query = query.lower().strip()
        
        if match_type == "all" or not query:
            for name, cmd in commands.items():
                results.append({
                    "name": name,
                    "description": cmd.description,
                    "usage": cmd.usage,
                    "match_score": 1.0
                })
        else:
            for name, cmd in commands.items():
                score = 0.0
                
                if match_type == "prefix":
                    if name.startswith(query):
                        score = 1.0 - (len(query) / (len(name) + 1))
                    elif query in name:
                        score = 0.5 - (len(query) / (len(name) + 1)) * 0.3
                elif match_type == "fuzzy":
                    score = _fuzzy_match(query, name)
                
                if score > 0:
                    results.append({
                        "name": name,
                        "description": cmd.description,
                        "usage": cmd.usage,
                        "match_score": round(score, 3)
                    })
        
        results.sort(key=lambda x: (-x["match_score"], x["name"]))
        
        return {
            "success": True,
            "commands": results,
            "query": query,
            "match_type": match_type
        }
    except Exception as e:
        logger.error(f"Error retrieving commands: {e}")
        return {
            "success": False,
            "error": str(e),
            "commands": []
        }

def _fuzzy_match(pattern: str, text: str) -> float:
    """
    Fuzzy matching algorithm with scoring.
    
    Returns a score between 0 and 1, where higher is better match.
    """
    if not pattern:
        return 1.0
    
    text = text.lower()
    pattern = pattern.lower()
    
    if pattern == text:
        return 1.0
    
    if pattern in text:
        return 0.8 - (len(text) - len(pattern)) / (len(text) + 1) * 0.2
    
    pattern_idx = 0
    consecutive_bonus = 0
    last_match_idx = -2
    
    for i, char in enumerate(text):
        if pattern_idx < len(pattern) and char == pattern[pattern_idx]:
            if i == last_match_idx + 1:
                consecutive_bonus += 0.1
            last_match_idx = i
            pattern_idx += 1
    
    if pattern_idx < len(pattern):
        return 0.0
    
    base_score = len(pattern) / len(text)
    position_bonus = 0.2 if text.startswith(pattern[0]) else 0
    
    return min(1.0, base_score * 0.5 + position_bonus + consecutive_bonus)

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
    if ai_enabled and ai_agent and len(parts) == 2:
        username = parts[0].strip()
        content = parts[1].strip()
        
        # Don't reply to AI's own messages
        if username != AGENT_NAME:
            asyncio.create_task(
                _process_ai_response(username, content, timestamp)
            )

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
        return
    
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
            await broadcast_message(f"{AGENT_NAME}: {ai_response.message}")
    
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
    import threading
    import socket
    import argparse
    
    parser = argparse.ArgumentParser(description="FastAPI Chatroom Server")
    parser.add_argument(
        "--http-port",
        type=int,
        default=80,
        help="HTTP port for redirect server (default: 80)"
    )
    parser.add_argument(
        "--https-port",
        type=int,
        default=443,
        help="HTTPS port for main server (default: 443)"
    )
    args = parser.parse_args()
    
    HTTP_PORT = args.http_port
    HTTPS_PORT = args.https_port
    
    def run_http_redirect():
        redirect_app = FastAPI()
        
        @redirect_app.get("/{path:path}")
        async def redirect_to_https(request: Request, path: str):
            host = request.headers.get("host", "81.68.133.63")
            if ":" in host:
                host = host.split(":")[0]
            https_url = f"https://{host}:{HTTPS_PORT}/{path}"
            return RedirectResponse(url=https_url, status_code=301)
        
        uvicorn.run(
            redirect_app,
            host="0.0.0.0",
            port=HTTP_PORT,
            log_level="warning"
        )
    
    asyncio.run(startup_event())
    
    http_thread = threading.Thread(target=run_http_redirect, daemon=True)
    http_thread.start()
    logger.info(f"HTTP redirect server started on port {HTTP_PORT} -> HTTPS port {HTTPS_PORT}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=HTTPS_PORT,
        reload=True,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
