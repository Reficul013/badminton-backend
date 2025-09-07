import os
from typing import Dict

# load .env first
from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, HTTPException, Request
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from sqlmodel import Session, select

from .database import get_session
from .models import User

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")

def _verify_firebase_token(request: Request) -> Dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not FIREBASE_PROJECT_ID:
        raise HTTPException(status_code=500, detail="FIREBASE_PROJECT_ID not configured")
    token = auth.split(" ", 1)[1]
    try:
        info = id_token.verify_firebase_token(token, GoogleRequest(), audience=FIREBASE_PROJECT_ID)
        return info
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

def get_current_user_id(
    info: Dict = Depends(_verify_firebase_token),
    session: Session = Depends(get_session),
) -> int:
    email = info.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email")

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(
            name=info.get("name") or "New User",
            email=email,
            role="RIDER",
            avatar_url=info.get("picture"),
            nickname=None,
            owns_car=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id
