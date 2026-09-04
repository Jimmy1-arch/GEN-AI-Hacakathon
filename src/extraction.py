import json
from src.gemini_client import gemini_client
from src.schemas import PatientCase

EXTRACTION_PROMPT = """
You are a medical intake fact extraction assistant.
Given the patient's statement, extract relevant facts into a strict JSON object matching the provided schema.

Rules:
- NEVER invent facts.
- NEVER diagnose.
- NEVER infer unsupported medical facts.
- Use null for unknown values.
- Distinguish explicitly stated facts from assumptions.
- Extract ONLY what is relevant to the supported triage rules (Fever, Injury, Chest pain, Breathing difficulty, Abdominal pain).

Patient Statement:
"{statement}"
"""

def extract_patient_facts(statement: str, current_case: PatientCase = None) -> PatientCase:
    # If we have a current case, we should merge the new statement
    prompt = EXTRACTION_PROMPT.format(statement=statement)
    if current_case:
        prompt += f"\n\nPrevious established facts:\n{current_case.model_dump_json()}"
        prompt += "\n\nUpdate the facts based on the NEW statement. Retain previous facts unless contradicted."
        
    try:
        response_text = gemini_client.get_structured_completion(prompt, schema_class=PatientCase)
        data = json.loads(response_text)
        return PatientCase(**data)
    except Exception as e:
        print(f"Extraction failed: {e}")
        # Return empty case on failure to allow graceful degradation
        return PatientCase()
