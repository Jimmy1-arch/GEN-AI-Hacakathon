import json
import logging
from src.gemini_client import gemini_client, GeminiTimeoutError
from src.schemas import PatientCase

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
You are a medical intake fact extraction assistant.
Your ONLY job is to extract facts stated by the patient into a strict JSON object.

CRITICAL RULES:
- NEVER invent facts. Only extract what the patient explicitly stated.
- NEVER diagnose. NEVER suggest a condition.
- NEVER infer unsupported medical facts.
- Use null for unknown or unstated values (do NOT default to false).
- Extract ONLY facts relevant to: Fever, Injury, Chest pain, Breathing difficulty, Abdominal pain.
- If the patient says "I don't know", "maybe", "not sure", "can't tell" — leave the field null (UNKNOWN).
- If the patient input is irrelevant, ambiguous, or completely off-topic, return an empty case with no facts.
- This is an INTAKE system, not a diagnosis system. Do NOT output diagnosis suggestions.

COMPLAINTS FIELD (MOST IMPORTANT):
- The `complaints` list MUST contain the patient's primary medical condition as a lowercase string.
- Use EXACTLY one of these supported values when they apply:
  "fever", "injury", "chest pain", "breathing difficulty", "abdominal pain"
- Example: Patient says "I have a fever" → complaints: ["fever"]
- Example: Patient says "My chest hurts" → complaints: ["chest pain"]
- Example: Patient says "I'm having trouble breathing" → complaints: ["breathing difficulty"]
- If the complaint is not one of the five above, leave complaints as [].
- Do NOT put these conditions in the `symptoms` field. `symptoms` is only for secondary/additional symptoms.

BOOLEAN FIELDS (breathing_difficulty, chest_pain, abdominal_pain):
- Set to true if the patient clearly states they have it.
- Set to false if the patient clearly denies it.
- Leave null if uncertain or unstated.

SEVERITY/INJURY_SEVERITY:
- Use the string "mild", "moderate", or "severe" based on the patient's own words.
- If they say a number (e.g., "8 out of 10"), map: 1-3 = "mild", 4-6 = "moderate", 7-10 = "severe".

Patient Statement:
"{statement}"
"""

FOLLOW_UP_CONTEXT = """

=== CONVERSATION CONTEXT ===
The assistant just asked the patient this specific question:
"{pending_question}"

This question was asking about the field: {pending_field}

The patient's response above is the ANSWER to that question.
Map the answer directly to the field "{pending_field}" in the JSON output.
Do NOT create a new complaint category from this response.
Do NOT ignore the pending question context.

Examples:
- If pending_field is "breathing_difficulty" and patient says "Yes" → breathing_difficulty: true
- If pending_field is "severity" and patient says "mild" → severity: "mild"
- If pending_field is "injury_severity" and patient says "8 out of 10" → injury_severity: "severe"
=== END CONTEXT ===
"""

MERGE_CONTEXT = """

=== PREVIOUS ESTABLISHED FACTS ===
{previous_facts}

Update the facts based on the NEW statement above.
Retain all previous facts unless the patient explicitly contradicts them.
If a contradiction is detected, add it to the "contradictions" list.
=== END PREVIOUS FACTS ===
"""

SCHEMA_SUFFIX = """

EXPECTED JSON SCHEMA:
{schema}

Return ONLY valid JSON matching this schema. No explanation, no markdown, no code blocks.
"""


def _is_empty_input(text: str) -> bool:
    """Return True if input is effectively empty or trivially short."""
    stripped = text.strip()
    if not stripped:
        return True
    # Purely symbolic or very short (1-2 chars)
    if len(stripped) <= 2 and not stripped.isalpha():
        return True
    # Only whitespace/punctuation
    if all(c in " \t\n.,?!..." for c in stripped):
        return True
    return False


def extract_patient_facts(statement: str, current_case: PatientCase = None) -> PatientCase:
    """
    Extract structured medical facts from a patient statement.
    Merges with current_case if provided.
    Handles pending question context to correctly map follow-up answers.
    """
    if _is_empty_input(statement):
        logger.info("Empty or trivial input — returning empty case")
        if current_case:
            return current_case
        return PatientCase()

    # Build prompt
    prompt = EXTRACTION_PROMPT.format(statement=statement)

    # Add pending question context if we're in a follow-up
    if current_case and current_case.pending_question:
        pending_field = (
            current_case.pending_fields[0]
            if current_case.pending_fields
            else "the requested field"
        )
        prompt += FOLLOW_UP_CONTEXT.format(
            pending_question=current_case.pending_question,
            pending_field=pending_field
        )
        logger.info("Extraction with pending question context — field: %s", pending_field)

    # Add merge context if we have prior facts
    if current_case:
        prompt += MERGE_CONTEXT.format(previous_facts=current_case.model_dump_json())

    # Add schema
    prompt += SCHEMA_SUFFIX.format(
        schema=json.dumps(PatientCase.model_json_schema(), indent=2)
    )

    try:
        response_text = gemini_client.get_structured_completion(prompt, schema_class=PatientCase)

        # Validate JSON before use
        if not response_text or not response_text.strip():
            raise ValueError("Empty response from Gemini")

        data = json.loads(response_text)
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected response type: {type(data)}")

        extracted = PatientCase(**data)
        logger.info(
            "Extraction successful — complaints: %s, pending: %s",
            extracted.complaints,
            extracted.pending_question
        )
        return extracted

    except GeminiTimeoutError as e:
        logger.error("Gemini timed out during extraction: %s", e)
        # Return current case unchanged if we have one, so conversation state is preserved
        if current_case:
            return current_case
        return PatientCase()

    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Malformed Gemini response during extraction: %s", e)
        if current_case:
            return current_case
        return PatientCase()

    except Exception as e:
        logger.error("Unexpected extraction error: %s", type(e).__name__)
        if current_case:
            return current_case
        return PatientCase()
