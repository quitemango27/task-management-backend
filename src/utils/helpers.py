from fastapi import Request, HTTPException, status, Depends
from src.utils.settings import settings
from src.users.model import UserModel
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError
import jwt
from src.utils.db import get_db


def is_authenticated(request: Request, db: Session = Depends(get_db)):
    token = request.headers.get("authorization")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    token = token.split(" ")[-1]

    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(UserModel).filter(UserModel.id == data.get("_id")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user