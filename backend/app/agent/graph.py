"""
The LangGraph tutor agent described in the doc's section 5.3.

On each incoming chat message, the router node classifies intent, then a
conditional edge dispatches to whichever tool should handle it:
  content_question -> RAG/citation engine
  generate_quiz     -> Quiz Generator tool
  study_plan        -> Study Planner tool
  study_kit         -> Multi-Modal Content Generator tool
  remediation       -> Remediation tool
  other             -> a plain conversational fallback

Because db/llm are request-scoped (a SQLAlchemy session + the configured
LLM provider), the graph is built per-request via `build_tutor_graph(db, llm)`
rather than as a single module-level singleton.
"""
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app import models
from app.agent.state import AgentState
from app.agent.router import classify_intent
from app.agent.study_planner import generate_study_plan
from app.agent.content_generator import generate_study_kit
from app.agent.remediation import generate_remediation
from app.agent.quiz_tools import generate_quiz
from app.llm.base import LLMProvider
from app.rag.query_engine import answer_content_question
from app.services.access import accessible_document_ids, accessible_topics_query


def _resolve_topic_id(db: Session, user_id: str, topic_hint: str | None) -> str | None:
    if not topic_hint:
        return None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    topic = accessible_topics_query(db, user).filter(models.Topic.title.ilike(f"%{topic_hint}%")).first()
    return topic.id if topic else None


def build_tutor_graph(db: Session, llm: LLMProvider):
    def router_node(state: AgentState) -> AgentState:
        classification = classify_intent(llm, state["message"])
        state["intent"] = classification["intent"]
        state["topic_id"] = _resolve_topic_id(db, state["user_id"], classification.get("topic_hint"))
        return state

    def rag_node(state: AgentState) -> AgentState:
        result = answer_content_question(
            llm, accessible_document_ids(db, state["user_id"]), state["message"]
        )
        state["response_content"] = result["content"]
        state["citations"] = result["citations"]
        return state

    def study_plan_node(state: AgentState) -> AgentState:
        plan = generate_study_plan(db, state["user_id"])
        if not plan:
            state["response_content"] = "There's no course content for your subjects yet — once your faculty uploads it, I'll build your study plan."
        else:
            next_item = plan[0]
            state["response_content"] = (
                f"Your next topic is **{next_item.topic.title}** ({next_item.status}). "
                f"{next_item.reason}"
            )
        state["citations"] = []
        return state

    def study_kit_node(state: AgentState) -> AgentState:
        if not state.get("topic_id"):
            state["response_content"] = "Which topic would you like a study kit for?"
            state["citations"] = []
            return state
        kit = generate_study_kit(db, llm, state["user_id"], state["topic_id"])
        state["response_content"] = kit["summary"]
        state["citations"] = []
        return state

    def quiz_node(state: AgentState) -> AgentState:
        if not state.get("topic_id"):
            state["response_content"] = "Which topic should I quiz you on?"
            state["citations"] = []
            return state
        attempt = generate_quiz(db, llm, state["user_id"], state["topic_id"])
        state["response_content"] = (
            f"I've generated a {len(attempt.questions)}-question quiz "
            f"(id: {attempt.id}) — open it in the Quiz tab."
        )
        state["citations"] = []
        return state

    def remediation_node(state: AgentState) -> AgentState:
        if not state.get("topic_id"):
            state["response_content"] = "Which topic are you stuck on?"
            state["citations"] = []
            return state
        result = generate_remediation(db, llm, state["user_id"], state["topic_id"])
        state["response_content"] = result["micro_module"]
        state["citations"] = []
        return state

    def fallback_node(state: AgentState) -> AgentState:
        state["response_content"] = llm.complete(
            [
                {"role": "system", "content": "You are Elara, a friendly AI tutor for school students. Keep replies brief."},
                {"role": "user", "content": state["message"]},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        state["citations"] = []
        return state

    def route_decision(state: AgentState) -> str:
        return state["intent"]

    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("rag", rag_node)
    graph.add_node("study_plan", study_plan_node)
    graph.add_node("study_kit", study_kit_node)
    graph.add_node("generate_quiz", quiz_node)
    graph.add_node("remediation", remediation_node)
    graph.add_node("other", fallback_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "content_question": "rag",
            "study_plan": "study_plan",
            "study_kit": "study_kit",
            "generate_quiz": "generate_quiz",
            "remediation": "remediation",
            "other": "other",
        },
    )
    for node in ["rag", "study_plan", "study_kit", "generate_quiz", "remediation", "other"]:
        graph.add_edge(node, END)

    return graph.compile()


def run_tutor_agent(db: Session, llm: LLMProvider, user_id: str, message: str) -> dict:
    agent = build_tutor_graph(db, llm)
    result = agent.invoke({"user_id": user_id, "message": message})
    return {"content": result["response_content"], "citations": result.get("citations", [])}
