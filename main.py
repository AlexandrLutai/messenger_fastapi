from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
  <body>
    <h2>FastAPI Chat</h2>
    <ul id="messages"></ul>
    <input id="msg" autocomplete="off" placeholder="Type message..." />
    <button id="send">Send</button>

    <script>
      const ws = new WebSocket(`ws://${location.host}/ws`);
      ws.onopen = () => console.log("✅ Connected");
      ws.onmessage = (event) => {
        const li = document.createElement("li");
        li.textContent = event.data;
        document.querySelector("#messages").appendChild(li);
      };
      document.querySelector("#send").onclick = () => {
        const msg = document.querySelector("#msg").value;
        ws.send(msg);
        document.querySelector("#msg").value = "";
      };
    </script>
  </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

# ---------------------------
# WebSocket endpoint
# ---------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)