from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# In-memory store for connections and usernames
user_map: dict[WebSocket, str] = {}
current_users: set[str] = set()

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
                    await broadcast_message(f"{username}: {message}")
    except WebSocketDisconnect:
        if websocket in user_map:
            username = user_map.pop(websocket)
            current_users.discard(username)
            await broadcast_user_list()
        print("Client disconnected")

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        return {"error": "Only image files are allowed."}
    filename = file.filename
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"url": f"/static/uploads/{filename}"}

async def broadcast_user_list():
    payload = json.dumps({"type":"userlist","users":list(current_users)})
    for ws in list(user_map.keys()):
        await ws.send_text(payload)

async def broadcast_message(message: str):
    payload = json.dumps({"type":"message","text":message})
    for ws in list(user_map.keys()):
        await ws.send_text(payload)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
