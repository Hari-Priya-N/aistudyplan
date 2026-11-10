import json

from sqlalchemy.orm import Session

from app import models
from app.agent.quiz_tools import _get_topic_context
from app.llm.base import LLMProvider

STUDY_KIT_SYSTEM_PROMPT = """You are a multi-modal study material generator for an adaptive \
tutor. Given source material on a topic, produce ALL of the following in one response, kept \
structurally consistent every time:

1. summary: a clear 3-4 sentence overview of the topic.
2. flashcards: 5 term/definition pairs covering the key ideas.
3. quiz: 5 multiple-choice questions (with correct_index).
4. step_by_step_guide: an ordered list of 4-8 short steps walking through solving a
   representative problem in this topic (not just the final answer) — reason through the
   logical progression the way a worked example would.

Respond ONLY with JSON of this exact shape:
{
  "summary": "string",
  "flashcards": [{"term": "string", "definition": "string"}],
  "quiz": [{"question": "string", "options": ["a","b","c","d"], "correct_index": 0}],
  "step_by_step_guide": ["step 1 text", "step 2 text"]
}
"""


def generate_study_kit(db: Session, llm: LLMProvider, user_id: str, topic_id: str) -> dict:
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise ValueError("Topic not found")

    context = _get_topic_context(llm, topic, top_k=8)
    messages = [
        {"role": "system", "content": STUDY_KIT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Topic: {topic.title}\n\nSource material:\n{context[:6000]}"},
    ]
    raw = llm.complete(messages, temperature=0.4, max_tokens=2500, json_mode=True)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "summary": "Could not generate a study kit right now — please try again.",
            "flashcards": [],
            "quiz": [],
            "step_by_step_guide": [],
        }

    parsed["topic_id"] = topic_id
    return parsed
