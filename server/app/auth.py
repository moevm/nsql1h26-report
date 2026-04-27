import os
import uuid
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey12345")
serializer = URLSafeTimedSerializer(SECRET_KEY)

templates = Jinja2Templates(directory="client/templates")

_sessions: dict = {}

USERS = {
    "admin": {"password": "admin123", "role": "admin", "display_name": "Администратор"},
    "teacher": {"password": "teacher123", "role": "teacher", "display_name": "Преподаватель"},
}

router = APIRouter(tags=["auth"])


def create_session(username: str) -> str:
    session_id = str(uuid.uuid4())
    user = USERS[username]
    _sessions[session_id] = {
        "username": username,
        "role": user["role"],
        "display_name": user["display_name"],
    }
    return session_id


def get_current_user(request: Request) -> Optional[dict]:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    return _sessions.get(session_id)


def require_auth(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


@router.get("/login")
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user = USERS.get(username)
    if not user or user["password"] != password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401,
        )
    session_id = create_session(username)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("session_id", session_id, httponly=True, samesite="lax")
    return response


@router.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_id")
    return response
