from typing import Dict, Any

from langsmith import get_current_run_tree
from langchain_core.messages import AIMessage

from agent.state import AgentState


def fallback_node(state: AgentState) -> Dict[str, Any]:
    """Handles escalation to a human support agent or polite rephrase on first unknown turn."""
    is_escalated = state.get("escalation_flag", False) or state.get("unknown_turns", 0) >= 2

    if is_escalated:
        handoff_message = (
            "I'm sorry, I wasn't able to fully resolve your request. "
            "I am escalating this conversation to a human support agent who will be with you shortly. "
            "Thank you for your patience."
        )

        # Add escalation tag to LangSmith trace
        run_tree = get_current_run_tree()

        if run_tree:
            run_tree.add_tags(["escalated:true"])
            # Attempt to tag the parent run as well
            if run_tree.parent_run:
                run_tree.parent_run.add_tags(["escalated:true"])

        # Print escalation details for debugging/logging
        print("\n--- ESCALATION LOG ---")

        print(f"Customer ID: {state.get('customer_id')}")
        print(f"Intent: {state.get('intent')}")
        print(f"Turns: {state.get('turn_count')}")

        print("\nConversation History:")

        for m in state.get("messages", []):

            if hasattr(m, "type") and hasattr(m, "content"):
                print(f"{m.type}: {m.content}")
            else:
                print(str(m))

        print("----------------------\n")

        return {
            "messages": [
                AIMessage(content=handoff_message)
            ],
            "active_sub_agent": "fallback",
            "escalation_flag": True
        }
    else:
        # First unknown turn: ask user to rephrase politely
        rephrase_message = (
            "I'm sorry, I didn't quite understand that. "
            "Could you please rephrase your request or ask about order status, "
            "products, returns, or recommendations?"
        )
        return {
            "messages": [
                AIMessage(content=rephrase_message)
            ],
            "active_sub_agent": "fallback",
            "escalation_flag": False
        }