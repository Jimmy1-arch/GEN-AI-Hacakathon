from fastapi import APIRouter, HTTPException
from src.schemas import AssessmentRequest, TriageResult, PatientCase
from src.extraction import extract_patient_facts
from src.rules import evaluate_case
from src.followups import generate_followup_questions

triage_router = APIRouter()

@triage_router.post("/assess", response_model=TriageResult)
def assess_patient(req: AssessmentRequest):
    try:
        # 1. Extract structured facts from the natural language input via Gemini
        # It handles merging if current_case is provided.
        case = extract_patient_facts(req.patient_statement, req.current_case)
        
        # 2. Deterministic rule evaluation
        result = evaluate_case(case)
        
        # 3. Generate natural language follow-up questions if needed
        if result.follow_up_questions:
            questions = generate_followup_questions(result.follow_up_questions)
            result.follow_up_questions = questions
            
        return result
    except Exception as e:
        print(f"Error in triage router: {e}")
        # Graceful degradation response
        return TriageResult(
            urgency="HUMAN ESCALATION",
            recommended_department="Human Review",
            decision="System processing error.",
            rule_id=None,
            reason="An error occurred during fact extraction or rule evaluation.",
            patient_initially_reported=[req.patient_statement],
            established_through_followup=[],
            still_unknown=[],
            evidence_text="System Fallback",
            human_review_required=True,
            case_status="🔴 Human escalation"
        )
