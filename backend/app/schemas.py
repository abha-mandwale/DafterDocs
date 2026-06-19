from datetime import datetime
from typing import Literal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


UserRole = Literal['admin', 'member', 'viewer']
ProcessingStage = Literal[
    'uploading',
    'ocr',
    'translating',
    'summarizing',
    'concluding',
    'completed',
    'failed',
]


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class ProcessDocumentResponse(BaseModel):
    jobId: str
    status: ProcessingStage


class DocumentResult(BaseModel):
    id: str
    sourceLanguage: str
    targetLanguage: str
    originalText: str
    translatedText: str
    summary: list[str]
    conclusion: str
    status: ProcessingStage
    createdAt: datetime


class ProcessingStatusResponse(BaseModel):
    id: str
    status: ProcessingStage
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    result: Optional[DocumentResult] = None


class ExportResponse(BaseModel):
    base64: str
    fileName: str
