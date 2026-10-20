import jwt
from datetime import datetime, timedelta
from fastapi import Header, HTTPException
from passlib.context import CryptContext

# VULN: JWT secret is weak/hardcoded and should come from a secrets manager
SECRET = "freetime1985"
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(pw: str) -> str:
    return pwd_ctx.hash(pw)


def verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return pwd_ctx.verify(pw, pw_hash)
    except Exception:
        return False


def create_token(user_id: int, username: str, is_admin: bool, minutes: int = 60):
    payload = {
        "sub": str(user_id), "username": username, "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def create_reset_token(user_id: int):
    payload = {"sub": str(user_id), "purpose": "reset", "exp": datetime.utcnow() + timedelta(minutes=15)}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_token(token: str):
    # VULN: accepts none alg - allows an unsigned/forged token to pass verification
    return jwt.decode(token, SECRET, algorithms=["HS256", "none"])


def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
