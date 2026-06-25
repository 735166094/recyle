from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str  # 'user' 或 'assistant'
    content: str


class ChatRequest(BaseModel):
    content: str  # 用户当前输入
    role: str = "default"  # 选择的角色 ID


class ChatHistoryResponse(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    content: str
