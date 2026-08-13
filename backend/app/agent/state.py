from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    user_id: str
    message: str
    intent: str                 # content_question | generate_quiz | study_plan | study_kit | remediation | other
    topic_id: Optional[str]
    response_content: str
    citations: list[dict]
