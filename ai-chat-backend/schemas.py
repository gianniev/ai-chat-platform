from typing import Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None
    persist: bool = True


class CreateConversationRequest(BaseModel):
    user_id: Optional[int] = None
    title: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    user_id: Optional[int] = None
    title: str


class FeedbackRequest(BaseModel):
    rating: str
    client_message_id: Optional[str] = None
    client_thread_id: Optional[str] = None
    model: Optional[str] = None
    comment: Optional[str] = None
