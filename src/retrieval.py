import json
import os
from typing import List
from src.schemas import TriageRule

def load_rules() -> List[TriageRule]:
    filepath = os.path.join(os.path.dirname(__file__), '..', 'data', 'triage_rules.json')
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        data = json.load(f)
        return [TriageRule(**rule) for rule in data]

def get_applicable_rules(category: str) -> List[TriageRule]:
    rules = load_rules()
    return [r for r in rules if r.category.lower() in category.lower()]
