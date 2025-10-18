from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, Session, create_engine, select

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ---------- БАЗА ДАННЫХ ---------- #
class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    text: str

engine = create_engine("sqlite:///chat.db")
SQLModel.metadata.create_all(engine)

# ---------- WEBSOCKET ---------- #
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[username] = websocket
        await self.broadcast(f"🟢 {username} joined the chat")

    def disconnect(self, username: str):
        self.active_connections.pop(username, None)

    async def broadcast(self, message: str):
        for ws in self.active_connections.values():
            await ws.send_text(message)

manager = ConnectionManager()

# ---------- РОУТЫ ---------- #
@app.get("/", response_class=HTMLResponse)
async def home():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(username: str = Form(...)):
    response = RedirectResponse(url=f"/chat?username={username}", status_code=302)
    return response

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, username: str):
    # загрузим последние 20 сообщений
    with Session(engine) as session:
        messages = session.exec(select(Message).order_by(Message.id.desc()).limit(20)).all()
        messages.reverse()
    return templates.TemplateResponse("chat.html", {"request": request, "username": username, "messages": messages})

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Сохраняем в базу
            with Session(engine) as session:
                msg = Message(username=username, text=data)
                session.add(msg)
                session.commit()
            await manager.broadcast(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.broadcast(f"🔴 {username} left the chat")