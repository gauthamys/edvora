'''APP'''
import os as _os

import dotenv as _dotenv
import jwt as _jwt
from uuid import uuid4
from typing import List, Optional
import fastapi as _fastapi
import fastapi.security as _security
from fastapi.templating import Jinja2Templates

import sqlalchemy.orm as _orm

import services as _services
import schemas as _schemas
import socket_util as _socket
import models as _models
from session import *

_dotenv.load_dotenv()

_JWT_SECRET = _os.environ['JWT_SECRET']

app = _fastapi.FastAPI()
manager = _socket.ConnectionManager()
templates = Jinja2Templates(directory="templates")

@app.get('/')
async def get(request: _fastapi.Request):
    return templates.TemplateResponse('general_pages/homepage.html', {'request': request})

@app.post("/api/users")
async def create_user(user: _schemas.UserCreate, db: _orm.Session = _fastapi.Depends(_services.get_db)):
    db_user = await _services.get_user_by_email(email=user.email, db=db)
    if db_user:
        raise _fastapi.HTTPException(
            status_code=400,
            detail="User with that email already exists")

    user = await _services.create_user(user=user, db=db)

    return await _services.create_token(user=user)

@app.post("/api/create_session/")
async def create_session(response: _fastapi.Response, token: Optional[str]=_fastapi.Query(None)):

    session = uuid4()
    name = _jwt.decode(token, _JWT_SECRET, algorithms=['HS256'])['email'].split('@')[0]
    data = SessionData(username=name)

    await backend.create(session, data)
    cookie.attach_to_response(response, session)

    return f"created session for {name}"

@app.get("/api/whoami", dependencies=[_fastapi.Depends(cookie)])
async def whoami(session_data: SessionData = _fastapi.Depends(verifier)):
    return session_data

@app.post("/api/delete_session")
async def del_session(response: _fastapi.Response, session_id: UUID = _fastapi.Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"

@app.post("/api/token")
async def generate_token(form_data: _security.OAuth2PasswordRequestForm = _fastapi.Depends(), db: _orm.Session = _fastapi.Depends(_services.get_db)):
    user = await _services.authenticate_user(email=form_data.username, password=form_data.password, db=db)

    if not user:
        raise _fastapi.HTTPException(
            status_code=401, detail="Invalid Credentials")

    return await _services.create_token(user=user)


@app.get("/api/users/me", response_model=_schemas.User)
async def get_user(user: _schemas.User = _fastapi.Depends(_services.get_current_user)):
    return user


@app.post("/api/user-posts", response_model=_schemas.Post)
async def create_post(
    post: _schemas.PostCreate,
    user: _schemas.User = _fastapi.Depends(_services.get_current_user),
    db: _orm.Session = _fastapi.Depends(_services.get_db)
):
    return await _services.create_post(user=user, db=db, post=post)


@app.get("/api/my-posts", response_model=List[_schemas.Post])
async def get_user_posts(user: _schemas.User = _fastapi.Depends(_services.get_current_user),
                         db: _orm.Session = _fastapi.Depends(_services.get_db)):
    return await _services.get_user_posts(user=user, db=db)

@app.websocket("/api/ws")
async def websocket_endpoint(
        websocket: _fastapi.WebSocket,
        cookie_or_token=_fastapi.Depends(_services.get_cookie_or_token)
    ):
    print(cookie_or_token)
    user = _jwt.decode(cookie_or_token, _JWT_SECRET, algorithms=["HS256"])
    db = _services.get_db()
    await manager.connect(websocket)
    username = user["email"].split('@')[0]
    await manager.broadcast(f'{username} has entered.')
    try:
        while True:
            post = await websocket.receive_text()
            await manager.broadcast(f'{username}:\t{post}')
            #await _services.create_post(user=user, db=db, post={"post_text": post})
    except _fastapi.WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.broadcast(f'{username} left.')
