from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime
import asyncio
import logging
from command import CommandFactory, CommandContext
from command.factory import register_builtin_commands
from db import init_db, save_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Register built-in commands
register_builtin_commands()

# In-memory store for connections and usernames
user_map: dict[WebSocket, str] = {}
current_users: set[str] = set()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        await init_db()
        logger.info("Database initialized successfully")
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
