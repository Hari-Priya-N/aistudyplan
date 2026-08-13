import json

from app.llm.base import LLMProvider

TOPIC_EXTRACTION_SYSTEM_PROMPT = """You are an expert curriculum designer. Given raw syllabus or \
lecture text, extract a hierarchical knowledge graph of topics and sub-topics a student needs to \
master, in a sensible learning order.

Respond ONLY with a JSON object of this exact shape, nothing else:
{
  "topics": [
    {
      "title": "string",
      "difficulty": "easy" | "medium" | "hard",
      "subtopics": [
        {"title": "string", "difficulty": "easy" | "medium" | "hard"}
      ]
    }
  ]
}
"""


def extract_knowledge_graph(llm: LLMProvider, syllabus_text: str) -> list[dict]:
    # Truncate very long syllabi to keep the extraction call fast and cheap.
    excerpt = syllabus_text[:12000]
    messages = [
        {"role": "system", "content": TOPIC_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": excerpt},
    ]
    raw = llm.complete(messages, temperature=0.2, max_tokens=2000, json_mode=True)
    try:
        parsed = json.loads(raw)
        return parsed.get("topics", [])
    except (json.JSONDecodeError, AttributeError):
        # Fallback: never let a malformed LLM response break ingestion.
        return [{"title": "General Concepts", "difficulty": "medium", "subtopics": []}]
