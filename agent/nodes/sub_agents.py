from typing import Dict, Any
from agent.state import AgentState
from agent.nodes.utils import run_sub_agent

def order_status_node(state: AgentState) -> Dict[str, Any]:
    return run_sub_agent(state, "order-status-agent", "order_status")

def product_query_node(state: AgentState) -> Dict[str, Any]:
    return run_sub_agent(state, "product-query-agent", "product_query")

def returns_node(state: AgentState) -> Dict[str, Any]:
    return run_sub_agent(state, "returns-agent", "returns")

def recommendation_node(state: AgentState) -> Dict[str, Any]:
    return run_sub_agent(state, "recommendation-agent", "recommendation")
