import json
from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field, ValidationError, field_validator

from src import model_client


class AgentState(TypedDict):
    title: str
    content: str
    email: str
    strict: bool
    task: str
    planner_proposal: dict
    reviewer_feedback: dict
    turn_count: int
    planner_attempts: int
    turn_ceiling: int
    validation_error: str
    validation_errors: list[str]
    status: str


class PlannerOutput(BaseModel):
    tags: list[str] = Field(min_length=3, max_length=3)
    summary: str

    @field_validator("tags")
    @classmethod
    def validate_tag_lengths(cls, tags):
        for tag in tags:
            if len(tag) < 3 or len(tag) > 30:
                raise ValueError("Each tag must be 3 to 30 characters long")
        return tags

    @field_validator("summary")
    @classmethod
    def validate_summary_length(cls, summary):
        if len(summary.split()) > 25:
            raise ValueError("Summary must be no more than 25 words")
        return summary


def supervisor_node(state: AgentState) -> dict:
    print("---NODE: Supervisor---")
    return {"turn_count": state["turn_count"] + 1}


def planner_node(state: AgentState) -> dict:
    print("---NODE: Planner---")
    attempts = state.get("planner_attempts", 0) + 1
    turn_ceiling = state.get("turn_ceiling", 10)

    prompt = f"""
You are a planner.

Title: {state["title"]}
Content: {state["content"]}

Create exactly 3 tags and a summary with no more than 25 words.

Return only JSON like this:
{{
    "tags": ["tag1", "tag2", "tag3"],
    "summary": "short summary"
}}
"""

    if state.get("validation_error"):
        prompt += f"""

Previous output failed validation:
{state["validation_error"]}

Please correct the output and return valid JSON.
"""

    if state["reviewer_feedback"]:
        prompt += f"""

Reviewer feedback:
{state["reviewer_feedback"].get("reason", "")}

Correct the issues in the new result.
"""

    result = model_client.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
        json_output=True,
    )

    try:
        proposal_data = json.loads(result["message"])
        proposal = PlannerOutput.model_validate(proposal_data)
    except (json.JSONDecodeError, ValidationError, TypeError, KeyError) as error:
        error_text = f"{type(error).__name__}: {error}"
        errors = state.get("validation_errors", []) + [error_text]
        status = "abandoned" if attempts >= turn_ceiling else "running"

        return {
            "planner_proposal": {},
            "reviewer_feedback": {},
            "planner_attempts": attempts,
            "validation_error": error_text,
            "validation_errors": errors,
            "status": status,
        }

    return {
        "planner_proposal": proposal.model_dump(),
        "reviewer_feedback": {},
        "planner_attempts": attempts,
        "validation_error": "",
        "status": "running",
    }


def reviewer_node(state: AgentState) -> dict:
    print("---NODE: Reviewer---")

    prompt = f"""
You are a reviewer.

Title: {state["title"]}
Content: {state["content"]}

Planner result:
{json.dumps(state["planner_proposal"])}

Check that there are exactly 3 relevant tags and that the summary is accurate
and no longer than 25 words.

Return only JSON like this:
{{
    "tags": ["tag1", "tag2", "tag3"],
    "summary": "short summary",
    "changed": true,
    "reason": "short reason"
}}
"""

    result = model_client.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
        json_output=True,
    )
    feedback = json.loads(result["message"])

    if feedback.get("changed", False):
        status = (
            "abandoned"
            if state.get("planner_attempts", 0) >= state.get("turn_ceiling", 10)
            else "running"
        )
    else:
        status = "completed"

    return {
        "reviewer_feedback": feedback,
        "status": status,
    }


def router_logic(state: AgentState):
    if state.get("status") in {"completed", "abandoned"}:
        return END

    if not state["planner_proposal"]:
        if state.get("planner_attempts", 0) >= state.get("turn_ceiling", 10):
            return END
        return "planner"

    if not state["reviewer_feedback"]:
        return "reviewer"

    if state["reviewer_feedback"].get("changed", False):
        if state.get("planner_attempts", 0) >= state.get("turn_ceiling", 10):
            return END
        return "planner"

    return END


workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("planner", planner_node)
workflow.add_node("reviewer", reviewer_node)
workflow.set_entry_point("supervisor")
workflow.add_conditional_edges(
    "supervisor",
    router_logic,
    {
        "planner": "planner",
        "reviewer": "reviewer",
        END: END,
    },
)
workflow.add_edge("planner", "supervisor")
workflow.add_edge("reviewer", "supervisor")
graph = workflow.compile()


def main():
    initial_state: AgentState = {
        "title": "Spacious 3 Bedroom House in San Jose",
        "content": (
            "Three bedroom rental house with a swimming pool, air conditioning, "
            "garage parking, and a large backyard near downtown San Jose."
        ),
        "email": "owner@example.com",
        "strict": True,
        "task": "Create rental tags and a short summary",
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "planner_attempts": 0,
        "turn_ceiling": 10,
        "validation_error": "",
        "validation_errors": [],
        "status": "running",
    }

    for step in graph.stream(initial_state):
        print(json.dumps(step, indent=2))


if __name__ == "__main__":
    main()
