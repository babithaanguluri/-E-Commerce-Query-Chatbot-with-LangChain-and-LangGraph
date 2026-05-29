from typing import Dict, Any, Optional

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agent.state import AgentState


class ContextExtraction(BaseModel):

    order_id: Optional[str] = Field(
        default=None,
        description="The specific order ID discussed"
    )

    product_id: Optional[str] = Field(
        default=None,
        description="The specific product ID discussed"
    )

    return_id: Optional[str] = Field(
        default=None,
        description="The specific return ID discussed"
    )


def memory_update_node(state: AgentState) -> Dict[str, Any]:
    """Extracts follow-up context from the last agent message.
    
    IMPORTANT: When is_unresolved=True the agent asked a clarifying question
    and its response may contain ambiguous IDs (e.g. "We have O1001 and O1002,
    which one?"). We must NOT store those as context because the user has NOT
    confirmed which ID they meant. We only extract IDs when the agent actually
    resolved the query (is_unresolved=False).
    """

    messages = state["messages"]

    if not messages:
        return {
            "follow_up_context": state.get("follow_up_context", {})
        }
    
    # When is_unresolved=True the agent asked a clarifying question.
    # We must NOT extract specific IDs (they would be ambiguous, e.g. "We have
    # O1001 and O1002 — which one?"), but we DO store the agent's clarifying
    # question text so the next turn's sub-agent can reference it to figure out
    # which order/product the user is pointing to.
    if state.get("is_unresolved", False):
        last_agent_message = state["messages"][-1]
        clarification_text = (
            last_agent_message
            if isinstance(last_agent_message, str)
            else getattr(last_agent_message, "content", str(last_agent_message))
        )
        current_context = state.get("follow_up_context", {})
        new_context = current_context.copy()
        new_context["clarification_question"] = clarification_text
        return {"follow_up_context": new_context}


    last_agent_message = messages[-1]

    # Extract content safely
    if isinstance(last_agent_message, str):
        content = last_agent_message
    else:
        content = getattr(
            last_agent_message,
            "content",
            str(last_agent_message)
        )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Extract any specific concrete IDs mentioned in the text "
            "that represent an order, product, or return. "
            "If no IDs are mentioned, return null values. "
            "Do NOT extract or return literal placeholders like 'O10...', 'P10...', or 'R10...'. "
            "Only return actual concrete IDs found in the text (e.g. O1002, P1008, R1001)."
        ),
        ("human", "{text}")
    ])

    llm = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0
    )

    extractor = prompt | llm.with_structured_output(
        ContextExtraction
    )

    try:

        result = extractor.invoke({
            "text": content
        })

        current_context = state.get(
            "follow_up_context",
            {}
        )

        new_context = current_context.copy()

        if result.order_id:
            new_context["order_id"] = result.order_id

        if result.product_id:
            new_context["product_id"] = result.product_id

        if result.return_id:
            new_context["return_id"] = result.return_id

        return {
            "follow_up_context": new_context
        }

    except Exception as e:

        print(f"Failed to extract context: {e}")

        return {
            "follow_up_context": state.get(
                "follow_up_context",
                {}
            )
        }