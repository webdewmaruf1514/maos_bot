import json
from fastapi import FastAPI, Request
from salary_bot import handle_update

app = FastAPI(title="BNPZ Salary Telegram Bot")


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    handle_update(payload)
    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "ok"}
