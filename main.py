import os
import json
import uuid
import time
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagrapi import Client

# Session Storage Directory
SESSIONS_DIR = "/data/sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

app = FastAPI(
    title="Instagram DM API",
    description="Send Instagram DMs via HTTP",
    version="1.0.0"
)

class LoginRequest(BaseModel):
    username: str
    password: str

class SendRequest(BaseModel):
    session_id: str
    recipients: List[str]
    message: str
    interval: float = 0.0  # seconds between messages

@app.post("/login")
async def login(request: LoginRequest):
    client = Client()
    try:
        client.login(request.username, request.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {e}")
    session_id = str(uuid.uuid4())
    session_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(session_path, "w") as f:
        json.dump(client.get_settings(), f)
    return {"session_id": session_id}

@app.post("/send")
async def send(request: SendRequest):
    session_path = os.path.join(SESSIONS_DIR, f"{request.session_id}.json")
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
    settings = json.load(open(session_path))
    client = Client()
    client.set_settings(settings)
    results = {}
    for user in request.recipients:
        try:
            uid = client.user_id_from_username(user)
            client.direct_send(request.message, [uid])
            results[user] = "sent"
        except Exception as exc:
            results[user] = f"error: {exc}"
        if request.interval > 0:
            time.sleep(request.interval)
    with open(session_path, "w") as f:
        json.dump(client.get_settings(), f)
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3013, workers=4)
