TRACK_ID=PS01

# TriageAI - Patient Intake Triage Assistant

## Problem Statement
Patients arriving at intake describe their situation in incomplete, everyday language. This project builds a triage assistant that extracts structured facts from natural language, identifies missing information, asks relevant follow-up questions, and deterministically applies local clinical triage rules to produce a safe, grounded triage note.

## Architecture
The application strictly separates AI inference from clinical decision making:
1. **Frontend**: Pure HTML/JS communicating with a FastAPI backend.
2. **Gemini Layer**: Uses `gemini-3.5-flash-lite` for intent understanding, JSON fact extraction, and generating targeted follow-up questions.
3. **Deterministic Rule Engine**: Pure Python logic that validates extracted facts, applies strict rules, handles missing/conflicting information, and generates final triage recommendations without LLM hallucinations.

## Setup and Running
1. `pip install -r requirements.txt`
2. Set your environment variable: `set GEMINI_API_KEY=your_key` or use `.env`.
3. `python app.py`
4. Open `http://localhost:8000`

## Demo Cases
- **Normal**: "I have had a mild fever since yesterday." -> Routine evaluation.
- **High Risk**: "I have chest pain and difficulty breathing." -> High-priority human escalation.
- **Null Case**: "My shoulder feels strange when I sit." -> Outside coverage / Human review.

## Safety Limitations
This system does NOT provide diagnoses. It is an intake triage support tool designed to route patients according to explicit local guidelines.

## Demo Video
[Link to Demo Video](#)
