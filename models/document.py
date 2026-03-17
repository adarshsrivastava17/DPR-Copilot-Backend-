"""Document model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, xlsx
    file_size = Column(Integer, default=0)
    is_reference = Column(Boolean, default=False)  # reference DPR or project doc
    parsed_text = Column(Text, nullable=True)
    sections_json = Column(Text, nullable=True)

    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
