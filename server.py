import asyncio
import json
import hashlib
import time
import uuid
from datetime import datetime
from aiohttp import web

# -------------------
# Password & users
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

USERS = {
    "user1": hash_pass("1234"),
    "user2": hash_pass("5678")
}

clients = {}       # username -> websocket
chat_history = []  # all messages
last_msg = {}      # anti-spam

# -------------------
# Serve index.html
async def index(request):
    return web.FileResponse('index.html')

# -------------------
# WebSocket handler
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    user = None
    clients_list = clients

    async for msg in ws:
        if msg.type != web.WSMsgType.TEXT:
            continue

        data = json.loads(msg.data)

        # LOGIN
        if data["type"] == "login":
            username = data["username"]
            password = hash_pass(data["password"])
            if username in USERS and USERS[username] == password:
                user = username
                clients[user] = ws
                await ws.send_json({
                    "type": "login",
                    "status": "success",
                    "history": chat_history
                })
            else:
                await ws.send_json({"type": "login", "status": "fail"})

        # MESSAGE
        elif data["type"] == "message":
            now = time.time()
            if user in last_msg and now - last_msg[user] < 1:
                continue
            last_msg[user] = now
            data["id"] = str(uuid.uuid4())
            data["time"] = datetime.now().strftime("%H:%M")
            data["seen_by"] = []
            chat_history.append(data)
            for cws in clients.values():
                await cws.send_json(data)

        # DELETE
        elif data["type"] == "delete":
            msg_id = data["id"]
            global chat_history
            chat_history = [msg for msg in chat_history if msg.get("id") != msg_id]
            for cws in clients.values():
                await cws.send_json({"type": "delete", "id": msg_id})

        # SEEN
        elif data["type"] == "seen":
            msg_id = data["id"]
            for msg in chat_history:
                if msg.get("id") == msg_id and user not in msg["seen_by"]:
                    msg["seen_by"].append(user)
            # broadcast
            for cws in clients.values():
                seen_msg = next((m for m in chat_history if m["id"] == msg_id), None)
                if seen_msg:
                    await cws.send_json({
                        "type": "seen",
                        "id": msg_id,
                        "seen_by": seen_msg["seen_by"]
                    })

        # TYPING
        elif data["type"] in ["typing", "stop_typing"]:
            for cws in clients.values():
                await cws.send_json(data)

    if user and user in clients:
        del clients[user]

    return ws

# -------------------
app = web.Application()
app.router.add_get('/', index)
app.router.add_get('/ws', websocket_handler)

if __name__ == '__main__':
    web.run_app(app, port=int(os.environ.get("PORT", 3000)))
