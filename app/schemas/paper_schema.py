from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PaperCreate(BaseModel):
    title: str
    original_text: str

class PaperResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True