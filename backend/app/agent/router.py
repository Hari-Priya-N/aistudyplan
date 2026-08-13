import json

from app.llm.base import LLMProvider

ROUTER_SYSTEM_PROMPT = """You are the tool router for an AI tutor agent. Classify the student's \
message into exactly one intent:

- "content_question": they're asking about course content / concepts (route to RAG).
- "generate_quiz": they want a quiz on a topic.
- "study_plan": they want to know what to study next / see their plan.
- "study_kit": they want a summary/flashcards/full study kit for a topic.
- "remediation": they're confused after a quiz / want help with a specific weak spot.
- "other": greetings, small talk, anything else.

If a topic name is mentioned or clearly implied, extract it.

Respond ONLY with JSON: {"intent": "...", "topic_hint": "string or null"}
"""


def classify_intent(llm: LLMProvider, message: str) -> dict:
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    raw = llm.complete(messages, temperature=0.0, max_tokens=150, json_mode=True)
    try:
        parsed = json.loads(raw)
        if parsed.get("intent") not in {
            "content_question", "generate_quiz", "study_plan", "study_kit", "remediation", "other"
        }:
            parsed["intent"] = "content_question"
        return parsed
    except json.JSONDecodeError:
        return {"intent": "content_question", "topic_hint": None}
