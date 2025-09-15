from pydantic import BaseModel, EmailStr
from typing import List

class UserCreate(BaseModel):
    email: EmailStr
    email_confirm: EmailStr
    password: str
    password_confirm: str         # Nuevo campo
    name: str
    surname: str
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class AdCreate(BaseModel):
    title: str
    user_id: int
    image_urls: List[str]
