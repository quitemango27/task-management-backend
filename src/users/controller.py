from src.users.dtos import UserSchema,LoginSchema
from sqlalchemy.orm import Session
from src.users.model import UserModel
from fastapi import BackgroundTasks, HTTPException,status,Request
from pwdlib import PasswordHash
import jwt
from src.utils.settings import settings
from datetime import datetime, timedelta
from jwt.exceptions import InvalidTokenError
from src.utils.mail import send_email
password_hash=PasswordHash.recommended()

def get_password_hash(password:str):
    return password_hash.hash(password)

def Verify_paassword(plain_password,hashed_password):
     return password_hash.verify(plain_password,hashed_password)

async def register(body: UserSchema, db: Session,bg_tasks: BackgroundTasks):
    is_user=db.query(UserModel).filter(UserModel.username==body.username).first()
    if is_user:
        raise HTTPException(status_code=400,detail="Username already exists")
    is_email=db.query(UserModel).filter(UserModel.email==body.email).first()
    if is_email:
        raise HTTPException(status_code=400,detail="Email already exists")

    hash_pasword=get_password_hash(body.password)
    new_user=UserModel(
        name=body.name,
        username=body.username,
        hash_password=hash_pasword,
        email=body.email
    )

    db.add(new_user)
    db.commit() 
    db.refresh(new_user)
    # send email
    bg_tasks.add_task(send_email, [new_user.email])

    
    return new_user




def user_login(body:LoginSchema , db: Session):
    user=db.query(UserModel).filter(UserModel.username==body.username).first()
    if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="You entered wrong password")
    if not Verify_paassword(body.password,user.hash_password):
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="You entered wrong password")

    exp_time=datetime.now()+timedelta(minutes=settings.EXP_TIME)
    token=jwt.encode({"_id": user.id,"exp":exp_time},settings.SECRET_KEY,algorithm=settings.ALGORITHM)
    print(exp_time)
    
    return {"token":token}


def is_authenticated(request:Request,db:Session):
    try:
            
        token=(request.headers.get("authorization"))
        token=token.split(" ")[-1]


        data=jwt.decode(token,settings.SECRET_KEY,settings.ALGORITHM)
        user_id=data.get("_id")
        

        user=db.query(UserModel).filter(UserModel.id==user_id).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found")
            
        return user

    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid token")