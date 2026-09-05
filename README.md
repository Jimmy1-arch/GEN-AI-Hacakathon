TRACK_ID=PS01
# TriageAI — GenAI-Assisted Patient Intake & Triage Support

## 1. Overview
TriageAI is a natural-language intake and triage-support system designed to assist human clinical staff. Patients frequently describe symptoms using informal, unstructured language. TriageAI uses Generative AI to understand the patient's plain-language input, extract structured medical facts, and identify missing required information. It asks targeted follow-up questions until enough information is gathered to evaluate the case against a deterministic rule engine.

**Important Boundary:** This is an intake and triage-support system. It is **NOT** a diagnostic system and does not replace doctors or nurses. It provides grounded triage recommendations to help route patients to the correct department safely.

## 2. Problem Statement — PS01
This repository implements the PS01 problem statement. It fulfills the core requirements by:
- Accepting plain-language patient descriptions of their complaints.
- Using GenAI to extract structured data and dynamically generating follow-up questions to resolve missing information.
- Evaluating the collected data against a strict set of deterministic **triage rules**.
- Generating a structured **triage note** that contains the recommended urgency, department, applied Rule ID, patient-reported information, information established through follow-up, and remaining unknowns.
- Enforcing strict **human escalation** for uncertain, out-of-scope, or contradictory information.
- Maintaining safety by explicitly **avoiding diagnosis** and grounding all final decisions in verifiable rules rather than LLM hallucinations.

## 3. Key Capabilities
- Natural-language patient intake
- GenAI-assisted information extraction
- Context-aware follow-up questions
- Structured case state management
- Missing-information detection
- Deterministic rule evaluation
- Rule ID traceability and citations
- Triage note generation (Clinical Intake Summary)
- Human escalation and Out-of-scope handling
- Contradictory information detection
- Case persistence (SQLite database)
- Demo/simulation scenarios

## 4. Supported Complaint Categories
The system is explicitly bounded to evaluate rules for five supported categories:
1. Fever
2. Injury
3. Chest pain
4. Breathing difficulty
5. Abdominal pain

The application is intentionally limited to its supported triage rules. If a patient presents with an unsupported complaint (e.g., "toothache" or "blurry vision"), the system does not force the complaint into an unrelated category. Instead, it correctly handles it as an **Out-of-Scope** scenario and immediately triggers a **Human Escalation**.

## 5. System Architecture
The application architecture strictly separates GenAI language understanding from clinical decision making.

```text
Patient
   │
   ▼
Natural-language intake (Frontend)
   │
   ▼
GenAI understanding / extraction (Gemini 3.5 Flash-Lite)
   │
   ▼
Structured case state (PatientCase Schema)
   │
   ├── Missing information?
   │        │
   │        ▼
   │   Follow-up question generated
   │        │
   │        ▼
   │   Patient response
   │        │
   │        └──────────────► Structured case state updated
   │
   ▼
Deterministic triage rule engine (Python)
   │
   ▼
Rule ID + matched conditions (JSON Triage Rules)
   │
   ▼
Urgency + Department Recommendation
   │
   ▼
Triage Note & Database Persistence (SQLite)
   │
   ▼
Human Review (when required by rule or safety boundary)
```

**Architectural Separation:** GenAI is used *only* for language understanding, structuring data, and natural language generation. The deterministic rule engine is 100% responsible for the final triage recommendation. The LLM is never the final clinical decision-maker.

## 6. How GenAI Is Used
GenAI (via Google Gemini) is utilized for specific, bounded language tasks:
- **Natural-language understanding:** Parsing the initial patient statement.
- **Structured fact extraction:** Mapping informal text (e.g., "it hurts a lot") to structured schema fields (e.g., `severity: "severe"`).
- **Contextual interpretation:** Mapping follow-up answers (e.g., "Yes") to the correct pending field (e.g., `chest_pain: true`).
- **Follow-up question generation:** Translating missing schema fields into natural, empathetic questions.

**What GenAI does NOT do:**
- It does **not** diagnose the patient.
- It does **not** override deterministic triage rules.
- It does **not** independently determine the final urgency or department.
- It does **not** invent clinical rules.

## 7. Conversation State
The application maintains conversational context between patient messages to accurately map follow-up answers to previously identified missing fields. 

**Conceptual Flow:**
1. Patient: *"I have chest pain."*
2. Extraction: Category = Chest pain. `breathing_difficulty` is unknown.
3. Rule Engine: Identifies `breathing_difficulty` as a missing field required for chest pain rules.
4. Assistant: *"Are you also experiencing any shortness of breath?"*
5. Patient: *"Yes."*
6. Extraction: Uses context of the pending field to map "Yes" → `breathing_difficulty: true`.
7. Rule Engine: Evaluates the updated case state.

## 8. Rule Engine
The triage rules are the authoritative source for recommendations.
- **Storage:** Rules are stored as deterministic JSON definitions in `data/triage_rules.json`.
- **Selection:** The engine filters rules based on the patient's identified category.
- **Evaluation:** It iterates through rule conditions. If all conditions match the structured case, the rule fires. If information is missing, it triggers follow-ups.
- **Urgency/Department:** The highest urgency matched rule provides the final `urgency`, `recommended_department`, and `escalation_required` flag.
- **Human Escalation:** If no pathway matches, or if there are contradictions, the engine deterministically outputs a Human Escalation result.

## 9. Grounded GenAI / Traceability
The evaluator explicitly values traceability. This project grounds its recommendations using **JSON rule definitions**.

All triage recommendations are directly traceable to a specific rule defined in `triage_rules.json`. 
**Traceability Flow:**
Patient facts → Rule Engine → Matches `R-CHEST-001` → Output includes Rule ID, Matched Conditions, and Source ("Local Triage Guidelines v1").

The system does not hallucinate rules; every decision provides an evidence citation linking back to the static JSON configuration.

## 10. Triage Note
The system generates a Clinical Intake Summary (Triage Note) containing:
- Original patient complaint
- Complaint category
- Recommended urgency & department
- Applied Rule ID (if matched)
- Rule evaluation status
- Patient-reported information
- Missing / remaining unknown information
- Human escalation status

The note clearly summarizes the intake evaluation for human staff without suggesting a medical diagnosis.

## 11. Human-in-the-Loop Safety
Automated triage assistance is intentionally bounded. The system escalates instead of guessing. Human Escalation is automatically triggered for:
- High-risk cases (e.g., Chest pain with breathing difficulty).
- Unresolved uncertainty (no deterministic rule matches the provided facts).
- Unsupported/Out-of-scope complaints (e.g., "my ear hurts").
- Conflicting information (e.g., patient says no breathing difficulty, then says yes).
- AI/System failures (e.g., Gemini API timeouts).

When the system cannot safely establish the information required for rule evaluation, the case is routed for human review rather than receiving a guessed recommendation.

## 12. Safety Boundaries
- **No diagnosis:** The system outputs urgency and department, never a clinical diagnosis.
- **No fabricated clinical facts:** If the patient doesn't state it, the field remains `null` (Unknown).
- **No guessing:** The system never infers values to force a rule match.
- **No LLM override:** The LLM cannot change the urgency of a deterministic rule.
- **Timeout safety:** If the LLM API fails or times out, the system safely catches the error and generates a Human Escalation response rather than crashing or hanging.

## 13. User Workflow
1. Start a new intake via the UI.
2. Patient describes their complaint in natural language.
3. AI extracts relevant information into a structured case.
4. Rule engine evaluates the case and identifies missing information.
5. AI asks a targeted follow-up question via Text/Voice (Edge-TTS).
6. Patient responds.
7. Structured case state is updated.
8. Rule engine re-evaluates the case.
9. Upon a complete match, Rule ID and matched conditions are surfaced.
10. The final Triage Note is generated.
11. High-risk or uncertain cases are automatically flagged in the Review Queue.

## 14. Example Interaction
**Patient:** *"My chest hurts."*
**Extraction:** Category: `chest pain`.
**System:** Evaluates rules. Missing required field: `breathing_difficulty`. 
**System:** *"Are you also having any difficulty breathing?"*
**Patient:** *"Yes, I am."*
**Extraction:** Updates case state: `breathing_difficulty: true`.
**System:** Evaluates rules. Matches `R-CHEST-001`.

**Output Triage Note:**
- **Category:** Chest pain
- **Urgency:** HIGH
- **Department:** Emergency Department
- **Rule ID:** R-CHEST-001
- **Matched Conditions:** `{"chest_pain": true, "breathing_difficulty": true}`
- **Escalation:** Human review required.

## 15. Out-of-Scope and Edge Cases
The system includes a comprehensive suite of 58 automated tests covering edge cases:
- **Empty input:** Returns an empty case, triggering Human Escalation.
- **Out-of-Scope input:** e.g., "toothache" categorizes as Outside Coverage → Escalation.
- **"I don't know":** Maps to `null` (Unknown), keeping the system from falsely assuming `false`.
- **Contradictory info:** Triggers immediate Human Escalation.
- **AI Failure/Timeout:** Caught by custom exceptions, safely returning a fallback Human Escalation result.

## 16. API / Backend
The backend is built with **FastAPI**.

**Key Endpoints:**
- `GET /health`: Immediate health check (no LLM calls) returning `{"status": "ok", "port": 8000}`.
- `GET /api/cases`: Retrieves all persisted intake cases from the SQLite database.
- `POST /api/assess`: Main assessment endpoint.

**Example `POST /api/assess` Request:**
```json
{
  "patient_statement": "I have a mild fever",
  "conversation_state": "NEW_CASE",
  "current_case": null
}
```

**Example Response:**
```json
{
  "urgency": "ROUTINE",
  "recommended_department": "General Practice",
  "decision": "Routine fever without severe symptoms can be evaluated in General Practice.",
  "rule_id": "R-FEVER-002",
  "reason": "Matched conditions: {'severity': 'mild'}",
  "human_review_required": false
}
```

## 17. Project Structure
```text
.
├── app.py                  # FastAPI entry point
├── requirements.txt        # Project dependencies
├── README.md               # This documentation
├── triage.db               # SQLite database for persistence
├── data/
│   └── triage_rules.json   # Deterministic rules source of truth
├── src/
│   ├── database.py         # SQLAlchemy configuration
│   ├── extraction.py       # LLM extraction & prompt context logic
│   ├── followups.py        # LLM follow-up generation
│   ├── gemini_client.py    # Google GenAI SDK wrapper & timeout handling
│   ├── models.py           # Database schema
│   ├── retrieval.py        # Rule loading logic
│   ├── rules.py            # Deterministic rule engine evaluation
│   ├── schemas.py          # Pydantic models for structured state
│   ├── triage.py           # API routes and orchestration
│   └── tts.py              # Edge-TTS voice generation
├── static/
│   ├── app.js              # Frontend logic
│   ├── index.html          # Frontend UI
│   └── style.css           # UI Styling
└── tests/
    ├── test_ps01.py        # Comprehensive test suite (58 tests)
    └── test_rules.py       # Legacy rule tests
```

---
*Developed for the PS01 Evaluation Track.*
