from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes import (
    classifier_node,
    order_status_node,
    product_query_node,
    returns_node,
    recommendation_node,
    fallback_node,
    memory_update_node
)

def route_intent(state: AgentState) -> str:
    """Routes the state to the correct node based on intent and escalation flag."""
    if state.get("escalation_flag"):
        return "fallback"
        
    intent = state.get("intent", "unknown")
    
    if intent == "order_status":
        return "order_status"
    elif intent == "product_query":
        return "product_query"
    elif intent == "return_request":
        return "returns"
    elif intent == "recommendation":
        return "recommendation"
    else:
        return "fallback"

def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    # Add Nodes
    builder.add_node("classifier", classifier_node)
    builder.add_node("order_status", order_status_node)
    builder.add_node("product_query", product_query_node)
    builder.add_node("returns", returns_node)
    builder.add_node("recommendation", recommendation_node)
    builder.add_node("fallback", fallback_node)
    builder.add_node("memory", memory_update_node)

    # Add Edges
    builder.add_edge(START, "classifier")
    
    # Conditional routing based on classifier output
    builder.add_conditional_edges(
        "classifier",
        route_intent,
        {
            "order_status": "order_status",
            "product_query": "product_query",
            "returns": "returns",
            "recommendation": "recommendation",
            "fallback": "fallback"
        }
    )

    # All sub-agents go to memory update
    builder.add_edge("order_status", "memory")
    builder.add_edge("product_query", "memory")
    builder.add_edge("returns", "memory")
    builder.add_edge("recommendation", "memory")
    
    # Fallback goes directly to END or memory? We'll put it to memory to be consistent
    builder.add_edge("fallback", "memory")
    
    # Memory goes to END (waiting for user input)
    builder.add_edge("memory", END)

    return builder.compile()
