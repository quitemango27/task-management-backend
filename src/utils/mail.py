from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from typing import List





conf = ConnectionConfig(
    MAIL_USERNAME = "quite.mango27@gmail.com",
    MAIL_PASSWORD = "vhra svrk scav ysjk",
    MAIL_FROM ="quite.mango27@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="Vidya",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)



async def send_email(emails: List[str]):
    html = """<p>Hi Thanks for registration</p> """

    message = MessageSchema(
        subject="Registration Successful",
        recipients=emails,
        body=html,
        subtype=MessageType.html)

    fm = FastMail(conf)
    await fm.send_message(message)
    return {"message": "email has been sent"}