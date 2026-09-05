import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.schemas import AssessmentRequest, TriageResult, PatientCase
from src.extraction import extract_patient_facts
from src.rules import evaluate_case
from src.followups import generate_followup_questions
from src.tts import generate_audio_base64
from src.database import get_db
from src.models import IntakeCase, IntakeMessage
from src.gemini_client import GeminiTimeoutError

logger = logging.getLogger(__name__)

triage_router = APIRouter()


def _persist_case(db: Session, req: AssessmentRequest, case: PatientCase, result: TriageResult):
    """Persist the intake case and the latest message/result to the DB."""
    try:
        case_id = case.case_id if case.case_id else None

        if case_id:
            db_case = db.query(IntakeCase).filter(IntakeCase.id == case_id).first()
        else:
            db_case = None

        if not db_case:
            db_case = IntakeCase(
                initial_complaint=req.patient_statement,
                complaint_category=", ".join(case.complaints) if case.complaints else None,
                urgency=result.urgency,
                department=result.recommended_department,
                human_review_required=result.human_review_required,
                status="IN_PROGRESS" if result.urgency == "PENDING" else "COMPLETE"
            )
            db.add(db_case)
            db.flush()  # Get the generated ID
        else:
            # Update existing case with latest result
            db_case.urgency = result.urgency
            db_case.department = result.recommended_department
            db_case.human_review_required = result.human_review_required
            db_case.complaint_category = ", ".join(case.complaints) if case.complaints else db_case.complaint_category
            db_case.status = "IN_PROGRESS" if result.urgency == "PENDING" else "COMPLETE"

        # Log patient message
        patient_msg = IntakeMessage(
            case_id=db_case.id,
            role="PATIENT",
            message=req.patient_statement
        )
        db.add(patient_msg)

        # Log assistant response (follow-up question or decision)
        if result.follow_up_questions:
            assistant_text = result.follow_up_questions[0]
        else:
            assistant_text = f"[{result.urgency}] {result.decision}"

        assistant_msg = IntakeMessage(
            case_id=db_case.id,
            role="ASSISTANT",
            message=assistant_text
        )
        db.add(assistant_msg)
        db.commit()

        # Inject the real DB case_id back into the PatientCase for continuity
        case.case_id = db_case.id
        logger.info("Case persisted — id: %s, urgency: %s", db_case.id, result.urgency)

    except Exception as e:
        logger.error("DB persistence failed: %s", type(e).__name__)
        db.rollback()
        # Do not re-raise — DB failure must not crash the API response


def _safe_escalation(reason: str, statement: str) -> TriageResult:
    """Return a safe human-escalation result when AI or system fails."""
    return TriageResult(
        urgency="HUMAN ESCALATION",
        recommended_department="Human Review",
        decision=reason,
        rule_id=None,
        reason=reason,
        patient_initially_reported=[statement],
        established_through_followup=[],
        still_unknown=[],
        evidence_text="System Fallback",
        human_review_required=True,
        case_status="🔴 Human escalation"
    )


@triage_router.post("/assess", response_model=TriageResult)
async def assess_patient(req: AssessmentRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    logger.info("Assess request received — conversation_state: %s", req.conversation_state)

    try:
        # 1. Extract structured facts from natural language via Gemini
        try:
            case = extract_patient_facts(req.patient_statement, req.current_case)
        except GeminiTimeoutError:
            logger.error("Gemini timeout during extraction")
            return _safe_escalation(
                "AI intake assistance is temporarily unavailable. Human assessment required.",
                req.patient_statement
            )

        # 2. Deterministic rule evaluation (never fails silently)
        try:
            result = evaluate_case(case)
        except Exception as e:
            logger.error("Rule engine error: %s", e)
            return _safe_escalation(
                "No automated triage recommendation could be safely generated. Human assessment required.",
                req.patient_statement
            )

        # 3. Update pending question state for follow-up context tracking
        if result.follow_up_questions:
            # Store the first missing field as the explicit pending field
            case.pending_fields = result.follow_up_questions[:1]
        else:
            case.pending_fields = []

        # 4. Generate natural language follow-up questions if needed
        if result.follow_up_questions:
            try:
                questions = generate_followup_questions(result.follow_up_questions)
                result.follow_up_questions = questions
                # Track the pending question text for context on next turn
                if questions:
                    case.pending_question = questions[0]
                    result.audio_base64 = await generate_audio_base64(questions[0])
            except GeminiTimeoutError:
                # Fall back to deterministic questions — don't crash
                logger.warning("Gemini timeout during follow-up generation — using fallback")
                fallback_qs = [f"Can you provide more information about: {f}?" for f in result.follow_up_questions]
                result.follow_up_questions = fallback_qs
                if fallback_qs:
                    case.pending_question = fallback_qs[0]
        else:
            case.pending_question = None
            # Generate voice for final decision
            msg = f"Triage decision: {result.urgency}. {result.decision}"
            result.audio_base64 = await generate_audio_base64(msg)

        result.current_case = case

        # 5. Persist to DB (non-blocking — errors logged but don't affect response)
        _persist_case(db, req, case, result)

        elapsed = time.time() - start_time
        logger.info(
            "Assess complete — rule_id: %s, urgency: %s, latency: %.2fs",
            result.rule_id,
            result.urgency,
            elapsed
        )
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("Unhandled error in /assess after %.2fs: %s", elapsed, e, exc_info=True)
        return _safe_escalation(
            "An error occurred during processing. Human assessment required.",
            req.patient_statement
        )


@triage_router.get("/cases")
def get_cases(db: Session = Depends(get_db)):
    """Return all intake cases for the clinician dashboard."""
    try:
        cases = db.query(IntakeCase).order_by(IntakeCase.created_at.desc()).limit(100).all()
        return [
            {
                "id": c.id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "initial_complaint": c.initial_complaint,
                "complaint_category": c.complaint_category,
                "urgency": c.urgency,
                "department": c.department,
                "human_review_required": c.human_review_required,
                "status": c.status
            }
            for c in cases
        ]
    except Exception as e:
        logger.error("Failed to fetch cases: %s", e)
        return []
