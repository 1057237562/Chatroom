# FastAPI Chatroom

## Image Upload

You can upload images to the server using the `/upload` endpoint. Send a `multipart/form-data` request with a file field named `file`.

Example using `curl`:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/image.png"
```

The server will store the image in `static/uploads` and return a JSON response containing the URL where the image can be accessed, e.g. `/static/uploads/image.png`.

You can then reference the image in your HTML or use it directly in the chat.

---

## Requirements

- Python 3.8+
- fastapi
- uvicorn[standard]

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
uvicorn main:app --reload
```

The server will start on http://localhost:8000.

## Using the Chatroom

Open `static/index.html` in a browser or navigate to `http://localhost:8000/static/index.html` if you add a static route. The page contains a simple WebSocket client that connects to `ws://localhost:8000/ws`. Type a message and press Send to see it echoed back.

## Notes

- The WebSocket endpoint echoes back any text message received.
- The server logs client disconnections to the console.

---

Enjoy building your chatroom!