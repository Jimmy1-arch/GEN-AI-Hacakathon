import json
from src.gemini_client import gemini_client
from typing import List

FOLLOWUP_PROMPT = """
You are a medical intake assistant. 
Based on the missing fields identified by the rules engine: {missing_fields}
Generate a single, clear, natural language follow-up question for the patient to gather this information.
Do NOT ask generic questions like "Can you provide more info?".
Be specific. For example, if missing "severity", ask "How severe is the pain on a scale of 1-10?".
If missing "breathing_difficulty", ask "Are you having any difficulty breathing?".

Return ONLY a JSON array of strings containing the questions (maximum 2 questions).
Example: ["Are you having difficulty breathing?", "How severe is the pain?"]
"""

def generate_followup_questions(missing_fields: List[str]) -> List[str]:
    prompt = FOLLOWUP_PROMPT.format(missing_fields=missing_fields)
    try:
        response_text = gemini_client.get_structured_completion(prompt)
        questions = json.loads(response_text)
        if isinstance(questions, list):
            return questions[:2]
    except Exception as e:
        print(f"Failed to generate followups: {e}")
    
    # Fallback deterministic questions
    qs = []
    for m in missing_fields:
        qs.append(f"Can you provide more information about: {m}?")
    return qs
