import asyncio
import websockets
import json
from datetime import datetime
import hashlib
import time
import os
import uuid

# 🔐 Hash password
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# 🔒 Users
USERS = {
    "user1": hash_pass("1234"),
    "user2": hash_pass("5678")
}

clients = {}
chat_history = []
last_msg = {}

async def handler(websocket):
    user = None
    try:
        async for message in websocket:
            data = json.loads(message)

            # 🔒 LOGIN
            if data["type"] == "login":
                username = data["username"]
                password = hash_pass(data["password"])

                if username in USERS and USERS[username] == password:
                    user = username
                    clients[user] = websocket

                    # Send login success + chat history
                    await websocket.send(json.dumps({
                        "type": "login",
                        "status": "success",
                        "history": chat_history
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "login",
                        "status": "fail"
                    }))

            # 💬 MESSAGE
            elif data["type"] == "message":
                now = time.time()
                if user in last_msg and now - last_msg[user] < 1:
                    continue
                last_msg[user] = now

                data["id"] = str(uuid.uuid4())
                data["time"] = datetime.now().strftime("%H:%M")
                data["seen_by"] = []  # ✅ Track seen users
                chat_history.append(data)

                for ws in clients.values():
                    await ws.send(json.dumps(data))

            # 📸 IMAGE
            elif data["type"] == "image":
                data["id"] = str(uuid.uuid4())
                data["time"] = datetime.now().strftime("%H:%M")
                data["seen_by"] = []  # ✅ Track seen users
                chat_history.append(data)

                for ws in clients.values():
                    await ws.send(json.dumps(data))

            # ❌ DELETE MESSAGE
            elif data["type"] == "delete":
                msg_id = data["id"]
                global chat_history
                chat_history = [msg for msg in chat_history if msg.get("id") != msg_id]

                for ws in clients.values():
                    await ws.send(json.dumps({
                        "type": "delete",
                        "id": msg_id
                    }))

            # 👀 SEEN MESSAGE
            elif data["type"] == "seen":
                msg_id = data["id"]
                for msg in chat_history:
                    if msg.get("id") == msg_id and user not in msg["seen_by"]:
                        msg["seen_by"].append(user)

                for ws in clients.values():
                    await ws.send(json.dumps({
                        "type": "seen",
                        "id": msg_id,
                        "seen_by": chat_history[[m["id"] for m in chat_history].index(msg_id)]["seen_by"]
                    }))

            # 💬 TYPING
            elif data["type"] in ["typing", "stop_typing"]:
                for ws in clients.values():
                    await ws.send(json.dumps(data))

    finally:
        if user in clients:
            del clients[user]

async def main():
    PORT = int(os.environ.get("PORT", 3000))
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"✅ Server running on port {PORT}")
        await asyncio.Future()

asyncio.run(main())
