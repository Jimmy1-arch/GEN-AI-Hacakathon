import logging
from typing import List, Tuple, Optional
from src.schemas import PatientCase, TriageResult, TriageRule
from src.retrieval import load_rules

logger = logging.getLogger(__name__)

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


def _coerce_bool(val) -> Optional[bool]:
    """Normalize a value to bool if it looks like one (handles 'TRUE'/'FALSE' strings from LLM)."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        if val.upper() == "TRUE":
            return True
        if val.upper() == "FALSE":
            return False
    return None  # Not coercible — keep as-is


def _values_match(case_v, rule_v) -> bool:
    """
    Compare a case field value against a rule condition value.
    Handles the type mismatch where:
      - Rule conditions from JSON booleans:  True / False
      - PatientCase fields from LLM strings: 'TRUE' / 'FALSE' / 'mild' / 'severe'
    """
    # If rule expects a bool, coerce the case value to bool for comparison
    if isinstance(rule_v, bool):
        coerced = _coerce_bool(case_v)
        if coerced is None:
            return False
        return coerced == rule_v
    # Otherwise compare as strings (lowercased to be safe)
    return str(case_v).lower() == str(rule_v).lower()


def check_condition(case_dict: dict, conditions: dict) -> bool:
    """Return True only if every rule condition is satisfied by the case dict."""
    for k, v in conditions.items():
        case_v = case_dict.get(k)
        if case_v is None:
            return False
        if not _values_match(case_v, v):
            return False
    return True


def get_missing_fields_for_rule(case_dict: dict, rule: TriageRule) -> List[str]:
    """Return fields required by the rule that are not yet present in the case."""
    missing = []
    for k, v in rule.conditions.items():
        case_v = case_dict.get(k)
        if case_v is None:
            missing.append(k)
        elif isinstance(v, bool):
            # If the field has a value but it explicitly doesn't match, it's not 'missing',
            # so we don't add it to missing (the rule simply won't fire via check_condition)
            pass
    return missing


def evaluate_case(case: PatientCase) -> TriageResult:
    trace = []

    # 1. Contradictions Check
    if case.contradictions:
        logger.warning("Case has contradictions: %s", case.contradictions)
        trace.append("Contradictions detected in patient statements")
        trace.append("Automatic fallback to Human Review")
        return TriageResult(
            urgency="HUMAN ESCALATION",
            recommended_department="Human Review",
            decision="Contradictory information detected.",
            rule_id=None,
            reason="Patient provided contradictory information which requires human validation.",
            patient_initially_reported=case.complaints + case.additional_facts,
            established_through_followup=[],
            still_unknown=case.unknowns,
            evidence_text="Contradictions: " + ", ".join(case.contradictions),
            human_review_required=True,
            case_status="🔴 Human escalation",
            decision_trace=trace
        )

    # 2. Match Categories — check complaints first, fall back to symptoms as safety net
    cats = normalize_category(case.complaints)
    if not cats and case.symptoms:
        # LLM sometimes puts the main complaint in symptoms instead of complaints
        cats = normalize_category(case.symptoms)
        if cats:
            logger.warning(
                "Category found in symptoms (not complaints): %s — extraction prompt may need improvement",
                cats
            )
            # Promote to complaints for downstream use
            case.complaints = cats

    logger.info("Normalized categories: %s", cats)

    if not cats:
        trace.append("Complaint could not be mapped to a supported category")
        trace.append("Automatic fallback to Human Review")
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
            case_status="⚪ Outside coverage",
            decision_trace=trace
        )

    trace.append(f"Complaint categorized as: {', '.join(cats)}")

    # 3. Evaluate Rules
    all_rules = load_rules()
    case_dict = case.model_dump()

    matched_rules = []
    potential_rules = []

    for rule in all_rules:
        if rule.category in cats:
            if check_condition(case_dict, rule.conditions):
                matched_rules.append(rule)
                logger.info("Rule %s matched", rule.rule_id)
            else:
                missing = get_missing_fields_for_rule(case_dict, rule)
                if missing:
                    potential_rules.append((rule, missing))

    # Priority: High urgency wins
    if matched_rules:
        urgency_order = {"HIGH": 3, "URGENT": 2, "ROUTINE": 1}
        matched_rules.sort(key=lambda x: urgency_order.get(x.urgency, 0), reverse=True)
        best_rule = matched_rules[0]

        trace.append(f"Rule {best_rule.rule_id} matched — urgency: {best_rule.urgency}")
        trace.append(f"Recommended department: {best_rule.recommended_department}")
        if best_rule.escalation_required:
            trace.append("Human review status: REQUIRED")
        else:
            trace.append("Human review status: NOT REQUIRED")

        logger.info("Best matched rule: %s (%s)", best_rule.rule_id, best_rule.urgency)

        return TriageResult(
            urgency=best_rule.urgency,
            recommended_department=best_rule.recommended_department,
            decision=best_rule.explanation,
            rule_id=best_rule.rule_id,
            reason=f"Matched conditions: {best_rule.conditions}",
            patient_initially_reported=case.complaints + case.additional_facts,
            established_through_followup=[],
            still_unknown=case.unknowns,
            evidence_text=f"{best_rule.rule_id} - {best_rule.source}",
            human_review_required=best_rule.escalation_required,
            case_status="🔴 Human escalation" if best_rule.escalation_required else "🟢 Information collected",
            decision_trace=trace,
            rule_conditions=best_rule.conditions
        )

    # 4. If no exact match but potential rules exist → Follow up required
    if potential_rules:
        missing_fields = set()
        for r, m in potential_rules:
            missing_fields.update(m)

        trace.append(f"Missing information detected: {', '.join(missing_fields)}")
        trace.append("Follow-up question(s) requested")

        logger.info("Follow-up required — missing fields: %s", missing_fields)

        return TriageResult(
            urgency="PENDING",
            recommended_department="Pending",
            decision="Insufficient information to evaluate triage rule.",
            rule_id=None,
            reason=f"Missing fields for rule evaluation: {list(missing_fields)}",
            patient_initially_reported=case.complaints,
            established_through_followup=[],
            still_unknown=list(missing_fields) + case.unknowns,
            evidence_text="Needs follow-up",
            human_review_required=False,
            follow_up_questions=list(missing_fields),
            case_status="🟡 Follow-up required",
            decision_trace=trace
        )

    # 5. No rules matched and no potential rules (information present but no pathway)
    trace.append("Information obtained but no deterministic rule pathway matched")
    trace.append("Automatic fallback to Human Review")

    logger.warning("No rule matched and no potential rules for categories: %s", cats)

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
        case_status="🔴 Human escalation",
        decision_trace=trace
    )
