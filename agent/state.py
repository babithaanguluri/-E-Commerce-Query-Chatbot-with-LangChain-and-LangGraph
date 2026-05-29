from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
    customer_id: str
    messages: Annotated[List[Any], add_messages]  # Auto-accumulates messages
    intent: str                  # Classified intent for the current turn
    active_sub_agent: str        # Which sub-agent is handling the query
    db_query_results: Dict       # Raw results from a DB lookup
    follow_up_context: Dict      # Last order/product/return discussed
    escalation_flag: bool        # True if the agent cannot resolve the query
    turn_count: int              # Total turns in the session
    unresolved_count: int        # Consecutive unresolved turns for same intent
    is_unresolved: bool          # Whether the active agent's turn was unresolved
    unknown_turns: int           # Consecutive turns with unknown intent
