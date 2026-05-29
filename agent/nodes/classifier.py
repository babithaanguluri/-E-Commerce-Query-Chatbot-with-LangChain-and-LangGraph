from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from agent.state import AgentState

class IntentClassification(BaseModel):
    intent: str = Field(description="The intent of the user's query. Must be one of: 'order_status', 'product_query', 'return_request', 'recommendation', 'unknown'.")

def classifier_node(state: AgentState) -> Dict[str, Any]:
    """Classify the user intent and handle escalation logic."""
    messages = state["messages"]
    last_user_message = next((m for m in reversed(messages) if m.type == "human"), None)
    
    if not last_user_message:
        return {"intent": "unknown", "unresolved_count": 0, "unknown_turns": 0, "escalation_flag": False}

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert intent classifier for an e-commerce platform. "
                   "Classify the user's latest message into exactly one of these categories:\n"
                   "1. order_status (e.g., 'where is my order', 'track my order')\n"
                   "2. product_query (e.g., 'do you have this in stock', 'how much is the jacket')\n"
                   "3. return_request (e.g., 'I want to return this', 'how do I get a refund')\n"
                   "4. recommendation (e.g., 'what should I buy', 'suggest some gifts')\n"
                   "5. unknown (if it doesn't fit the above or is gibberish)\n\n"
                   "Consider the follow up context: {context}\n"
                   "The last active sub-agent was: {active_agent}\n"
                   "Did the last sub-agent ask for clarification (unresolved): {is_unresolved}\n"
                   "CRITICAL: If the last active sub-agent was order_status and was unresolved (asked for clarification), and the user is responding with a product name (e.g., 'Wind Gadget', 'the jacket', 'Oil Thingamajig') or order number to specify their order, their intent is STILL order_status!"),
        ("human", "{message}")
    ])

    llm = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0
    )
    classifier = prompt | llm.with_structured_output(IntentClassification)
    
    result = classifier.invoke({
        "message": last_user_message.content,
        "context": state.get("follow_up_context", {}),
        "active_agent": state.get("active_sub_agent", "none"),
        "is_unresolved": str(state.get("is_unresolved", False))
    })
    
    new_intent = result.intent
    current_intent = state.get("intent", "")
    escalation_flag = state.get("escalation_flag", False)
    
    # 1. Unknown intent tracking: escalate if unknown for 2+ consecutive turns
    unknown_turns = state.get("unknown_turns", 0)
    if new_intent == "unknown":
        unknown_turns += 1
    else:
        unknown_turns = 0
        
    # 2. Unresolved same-intent tracking: escalate if same intent unresolved for 3 turns
    # The counter always increments while the same intent persists so that
    # 3 consecutive same-intent turns (even if individually "resolved" by stored
    # context) will eventually trigger escalation. It resets only on intent change.
    unresolved_count = state.get("unresolved_count", 0)
    if new_intent == current_intent and new_intent != "unknown":
        # Same intent as before — always increment regardless of is_unresolved.
        # This ensures 3 repeated same-intent queries trigger escalation.
        unresolved_count += 1
    else:
        # Intent changed (or first turn for this intent) — reset to 1
        unresolved_count = 1 if new_intent != "unknown" else 0
        
    # 3. Escalation check
    if unknown_turns >= 2 or unresolved_count >= 3:
        escalation_flag = True
        
    # Tag intent and customer_id to LangSmith trace
    from langsmith import get_current_run_tree
    run_tree = get_current_run_tree()
    customer_id = state.get("customer_id", "unknown")
    if run_tree:
        tags = [f"intent:{new_intent}", f"customer_id:{customer_id}", "environment:production"]
        run_tree.add_tags(tags)
        if run_tree.parent_run:
            run_tree.parent_run.add_tags(tags)
            
    return {
        "intent": new_intent,
        "unresolved_count": unresolved_count,
        "unknown_turns": unknown_turns,
        "escalation_flag": escalation_flag,
        "turn_count": state.get("turn_count", 0) + 1
    }

