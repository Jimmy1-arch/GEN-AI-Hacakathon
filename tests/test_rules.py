from src.schemas import PatientCase
from src.rules import evaluate_case

def test_high_risk_chest_pain():
    case = PatientCase(
        complaints=["chest pain"],
        chest_pain="TRUE",
        breathing_difficulty="TRUE",
        severity="severe"
    )
    result = evaluate_case(case)
    assert result.urgency == "HIGH"
    assert result.rule_id == "R-CHEST-001"
    assert result.human_review_required is True

def test_routine_fever():
    case = PatientCase(
        complaints=["fever"],
        severity="mild"
    )
    result = evaluate_case(case)
    assert result.urgency == "ROUTINE"
    assert result.rule_id == "R-FEVER-002"

def test_null_case():
    case = PatientCase(
        complaints=["shoulder hurts when I sit"],
    )
    result = evaluate_case(case)
    assert result.case_status == "⚪ Outside coverage"
    assert result.human_review_required is True

def test_contradiction():
    case = PatientCase(
        complaints=["breathing difficulty"],
        contradictions=["Patient initially said no breathing difficulty but later said yes."]
    )
    result = evaluate_case(case)
    assert "Contradictory" in result.decision
    assert result.human_review_required is True

def test_missing_information():
    case = PatientCase(
        complaints=["fever"],
        # Missing severity which is required by fever rules
    )
    result = evaluate_case(case)
    assert result.case_status == "🟡 Follow-up required"
    assert "severity" in result.follow_up_questions
