import asyncio
import websockets
import json
from datetime import datetime
import hashlib
import time

# 🔐 Users (hashed passwords)
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

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

async def main():
    async with websockets.serve(handler, "0.0.0.0", 3000):
        print("✅ Server running...")
        await asyncio.Future()

asyncio.run(main())