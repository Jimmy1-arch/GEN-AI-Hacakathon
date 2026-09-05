import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
import uuid
from src.database import Base

class IntakeCase(Base):
    __tablename__ = "intake_cases"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    initial_complaint = Column(Text, nullable=True)
    complaint_category = Column(String, nullable=True)
    urgency = Column(String, nullable=True)
    department = Column(String, nullable=True)
    human_review_required = Column(Boolean, default=False)
    status = Column(String, default="IN_PROGRESS")
    
    messages = relationship("IntakeMessage", back_populates="case", cascade="all, delete-orphan")
    facts = relationship("ExtractedFact", back_populates="case", cascade="all, delete-orphan")
    evaluations = relationship("RuleEvaluation", back_populates="case", cascade="all, delete-orphan")

class IntakeMessage(Base):
    __tablename__ = "intake_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("intake_cases.id"))
    role = Column(String) # "PATIENT" or "ASSISTANT"
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    case = relationship("IntakeCase", back_populates="messages")

class ExtractedFact(Base):
    __tablename__ = "extracted_facts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("intake_cases.id"))
    field = Column(String)
    value = Column(String) # Stored as string for simplicity, or JSON
    source = Column(String) # "INITIAL_REPORT" or "FOLLOW_UP"
    confidence = Column(String, nullable=True)
    
    case = relationship("IntakeCase", back_populates="facts")

class RuleEvaluation(Base):
    __tablename__ = "rule_evaluations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("intake_cases.id"))
    rule_id = Column(String, nullable=True)
    matched = Column(Boolean)
    conditions = Column(JSON, nullable=True)
    result = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    case = relationship("IntakeCase", back_populates="evaluations")
