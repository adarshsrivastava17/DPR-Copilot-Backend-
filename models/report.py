"""Generated Report model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=True)
    status = Column(String(50), default="generating")  # generating, completed, failed
    sections = Column(JSON, nullable=True)  # { "executive_summary": "...", ... }
    financial_data = Column(JSON, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    pptx_path = Column(String(500), nullable=True)

    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="reports")
