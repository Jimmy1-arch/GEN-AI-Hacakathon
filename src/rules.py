from typing import List, Tuple, Optional
from src.schemas import PatientCase, TriageResult, TriageRule
from src.retrieval import load_rules

SUPPORTED_CATEGORIES = ["fever", "injury", "chest pain", "breathing difficulty", "abdominal pain"]

def normalize_category(complaints: List[str]) -> List[str]:
    matched = []
    for c in complaints:
        cl = c.lower()
        for sc in SUPPORTED_CATEGORIES:
            if sc in cl:
                if sc not in matched:
                    matched.append(sc)
    return matched

def check_condition(case_dict: dict, conditions: dict) -> bool:
    for k, v in conditions.items():
        case_v = case_dict.get(k)
        if case_v != v:
            return False
    return True

def get_missing_fields_for_rule(case_dict: dict, rule: TriageRule) -> List[str]:
    missing = []
    for k, v in rule.conditions.items():
        if case_dict.get(k) is None:
            missing.append(k)
    return missing

def evaluate_case(case: PatientCase) -> TriageResult:
    # 1. Contradictions Check
    if case.contradictions:
        return TriageResult(
            urgency="HUMAN ESCALATION",
            recommended_department="Human Review",
            decision="Contradictory information detected.",
            rule_id=None,
            reason="Patient provided contradictory information which requires human validation.",
            patient_initially_reported=case.additional_facts,
            established_through_followup=[],
            still_unknown=case.unknowns,
            evidence_text="Contradictions: " + ", ".join(case.contradictions),
            human_review_required=True,
            case_status="🔴 Human escalation"
        )
    
    # 2. Match Categories
    cats = normalize_category(case.complaints)
    if not cats:
        # OUTSIDE COVERAGE / NULL CASE
        return TriageResult(
            urgency="HUMAN ESCALATION",
            recommended_department="Human Review",
            decision="No applicable triage rule was found in the current rule set.",
            rule_id=None,
            reason="Complaint falls outside supported coverage (Fever, Injury, Chest pain, Breathing difficulty, Abdominal pain).",
            patient_initially_reported=case.complaints,
            established_through_followup=[],
            still_unknown=case.unknowns,
            evidence_text="Outside coverage",
            human_review_required=True,
            case_status="⚪ Outside coverage"
        )
    
    # 3. Evaluate Rules
    all_rules = load_rules()
    case_dict = case.model_dump()
    
    matched_rules = []
    potential_rules = []
    
    for rule in all_rules:
        if rule.category in cats:
            if check_condition(case_dict, rule.conditions):
                matched_rules.append(rule)
            else:
                missing = get_missing_fields_for_rule(case_dict, rule)
                if missing:
                    potential_rules.append((rule, missing))
                    
    # Priority: High urgency wins
    if matched_rules:
        # Sort by urgency (HIGH > URGENT > ROUTINE)
        urgency_order = {"HIGH": 3, "URGENT": 2, "ROUTINE": 1}
        matched_rules.sort(key=lambda x: urgency_order.get(x.urgency, 0), reverse=True)
        best_rule = matched_rules[0]
        
        return TriageResult(
            urgency=best_rule.urgency,
            recommended_department=best_rule.recommended_department,
            decision=best_rule.explanation,
            rule_id=best_rule.rule_id,
            reason="Matched conditions: " + str(best_rule.conditions),
            patient_initially_reported=case.complaints + case.additional_facts,
            established_through_followup=[],
            still_unknown=case.unknowns,
            evidence_text=f"{best_rule.rule_id} - {best_rule.source}",
            human_review_required=best_rule.escalation_required,
            case_status="🔴 Human escalation" if best_rule.escalation_required else "🟢 Information collected"
        )
    
    # 4. If no exact match but potential rules exist -> Follow up required
    if potential_rules:
        # Gather missing fields
        missing_fields = set()
        for r, m in potential_rules:
            missing_fields.update(m)
            
        return TriageResult(
            urgency="PENDING",
            recommended_department="Pending",
            decision="Insufficient information.",
            rule_id=None,
            reason=f"Missing fields for rule evaluation: {list(missing_fields)}",
            patient_initially_reported=case.complaints,
            established_through_followup=[],
            still_unknown=list(missing_fields) + case.unknowns,
            evidence_text="Needs follow-up",
            human_review_required=False,
            follow_up_questions=list(missing_fields),
            case_status="🟡 Follow-up required"
        )
        
    # 5. No rules matched and no potential rules
    return TriageResult(
        urgency="HUMAN ESCALATION",
        recommended_department="Human Review",
        decision="Rules exist for category but conditions could not be met or resolved.",
        rule_id=None,
        reason="Information provided does not map to known safe pathways.",
        patient_initially_reported=case.complaints,
        established_through_followup=[],
        still_unknown=case.unknowns,
        evidence_text="Fallback",
        human_review_required=True,
        case_status="🔴 Human escalation"
    )
