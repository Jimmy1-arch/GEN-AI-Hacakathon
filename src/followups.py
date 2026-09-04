import json
from src.gemini_client import gemini_client
from typing import List

FOLLOWUP_PROMPT = """
You are a strict medical intake assistant. 
Based on the missing fields identified by the rules engine: {missing_fields}
Generate a single, clear, natural language follow-up question for the patient to gather this information.

CRITICAL EDGE CASE RULES:
1. Do NOT ask generic questions like "Can you provide more info?".
2. Be specific. For example, if missing "severity", ask "How severe is the pain on a scale of 1-10?".
3. If the missing fields do not make clinical sense for the context, or the patient's statement is completely irrelevant, DO NOT ask a hallucinated or forced medical question. Instead, ask them to clarify their primary complaint.
4. Never diagnose or hint at a diagnosis in the question.

Return ONLY a JSON array of strings containing the questions (maximum 2 questions).
Example: ["Are you having difficulty breathing?", "How severe is the pain?"]
"""

def generate_followup_questions(missing_fields: List[str]) -> List[str]:
    prompt = FOLLOWUP_PROMPT.format(missing_fields=missing_fields)
    try:
        response_text = gemini_client.get_structured_completion(prompt)
        questions = json.loads(response_text)
        if isinstance(questions, list) and questions:
            return questions[:2]
    except Exception as e:
        print(f"Failed to generate followups: {e}")
    
    # Fallback deterministic questions
    qs = []
    for m in missing_fields:
        qs.append(f"Can you provide more information about: {m}?")
    return qs
