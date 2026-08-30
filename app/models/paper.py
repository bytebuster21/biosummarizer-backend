from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.core.database import Base

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    original_text = Column(Text)
    summary = Column(Text, nullable=True)
    structured_summary = Column(Text, nullable=True) # JSON serialized multi-perspective brief
    graph_data = Column(Text, nullable=True)         # JSON serialized knowledge graph
    uploaded_at = Column(DateTime, default=datetime.utcnow)