from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class PatientCase(BaseModel):
    complaints: List[str] = Field(default_factory=list, description="List of primary complaints (e.g., 'fever', 'chest pain')")
    symptoms: List[str] = Field(default_factory=list, description="Other symptoms reported")
    onset: Optional[str] = Field(None, description="When the symptoms started")
    duration: Optional[str] = Field(None, description="How long the symptoms have lasted")
    severity: Optional[str] = Field(None, description="Reported severity level")
    temperature: Optional[str] = Field(None, description="Fever temperature if reported")
    breathing_difficulty: Optional[bool] = Field(None, description="Whether breathing difficulty is present")
    chest_pain: Optional[bool] = Field(None, description="Whether chest pain is present")
    injury_type: Optional[str] = Field(None, description="Type of injury if applicable")
    injury_severity: Optional[str] = Field(None, description="Severity of injury")
    abdominal_pain: Optional[bool] = Field(None, description="Whether abdominal pain is present")
    pain_location: Optional[str] = Field(None, description="Location of pain")
    pain_duration: Optional[str] = Field(None, description="Duration of pain")
    additional_facts: List[str] = Field(default_factory=list, description="Any other relevant medical facts")
    unknowns: List[str] = Field(default_factory=list, description="Crucial missing information that needs follow-up")
    contradictions: List[str] = Field(default_factory=list, description="Detected contradictions")

class TriageRule(BaseModel):
    rule_id: str
    category: str
    conditions: Dict[str, Any]
    urgency: str
    recommended_department: str
    explanation: str
    escalation_required: bool
    source: str
    version: str

class TriageResult(BaseModel):
    urgency: str
    recommended_department: str
    decision: str
    rule_id: Optional[str]
    reason: str
    patient_initially_reported: List[str]
    established_through_followup: List[str]
    still_unknown: List[str]
    evidence_text: Optional[str]
    human_review_required: bool
    follow_up_questions: List[str] = []
    case_status: str # "🟢 Information collected", "🟡 Follow-up required", "🔴 Human escalation", "⚪ Outside coverage"
    audio_base64: Optional[str] = None
    current_case: Optional[PatientCase] = None

class AssessmentRequest(BaseModel):
    patient_statement: str
    current_case: Optional[PatientCase] = None
    follow_up_answers: Optional[Dict[str, str]] = None
    initial_statement: Optional[str] = None
