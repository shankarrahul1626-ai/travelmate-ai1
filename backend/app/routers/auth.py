from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

router = APIRouter()


class User(BaseModel):
    username: str
    password: str


# naive in-memory users
USERS = {"demo": {"password": "demo"}}


@router.post('/register')
def register(u: User):
    if u.username in USERS:
        raise HTTPException(status_code=400, detail='user exists')
    USERS[u.username] = {"password": u.password}
    return {"status": "ok"}


@router.post('/login')
def login(u: User):
    if u.username not in USERS or USERS[u.username]['password'] != u.password:
        raise HTTPException(status_code=401, detail='invalid credentials')
    # return a fake token (do NOT use in production)
    token = f"fake-token-{u.username}-{int(time.time())}"
    return {"access_token": token, "token_type": "bearer"}
