import asyncio
import websockets
import json
from datetime import datetime
import hashlib
import time
import os

# 🔐 Hash password
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# 🔒 Allowed users
USERS = {
    "Ad@2012": hash_pass("2012"),
    "La@2014": hash_pass("2014")
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

                data["time"] = datetime.now().strftime("%H:%M")
                chat_history.append(data)

                for ws in clients.values():
                    await ws.send(json.dumps(data))

                # 💾 Save chat
                with open("chat.txt", "a") as f:
                    f.write(f"{data['user']}: {data['text']} ({data['time']})\n")

            # 📸 IMAGE
            elif data["type"] == "image":
                data["time"] = datetime.now().strftime("%H:%M")
                chat_history.append(data)

                for ws in clients.values():
                    await ws.send(json.dumps(data))

            # 💬 TYPING
            elif data["type"] in ["typing", "stop_typing"]:
                for ws in clients.values():
                    await ws.send(json.dumps(data))

    finally:
        if user in clients:
            del clients[user]

# 🌍 IMPORTANT: Use Render PORT
async def main():
    PORT = int(os.environ.get("PORT", 3000))

    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"✅ Server running on port {PORT}")
        await asyncio.Future()  # run forever

asyncio.run(main())
