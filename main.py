import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from agent.graph import build_graph
from langchain import hub

def main():
    load_dotenv()
    
    print("Welcome to the E-Commerce Support Chatbot!")
    print("Type 'quit' or 'exit' to stop.")
    
    graph = build_graph()
    
    # Initial state
    state = {
        "customer_id": "C1001", # Simulating a logged-in user
        "messages": [],
        "intent": "",
        "active_sub_agent": "",
        "db_query_results": {},
        "follow_up_context": {},
        "escalation_flag": False,
        "turn_count": 0,
        "unresolved_count": 0,
        "is_unresolved": False,
        "unknown_turns": 0
    }
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        # Append user message
        state["messages"].append(HumanMessage(content=user_input))
        
        # Run graph
        print("\nAgent is thinking...")
        
        config = {
            "tags": [f"customer_id:{state.get('customer_id', 'unknown')}", "environment:production"]
        }
        final_state = graph.invoke(state, config=config)
        
        # Extract last agent message
        last_message = final_state["messages"][-1]
        if isinstance(last_message, AIMessage):
            response = last_message.content
        else:
            response = last_message
            
        print(f"Agent ({final_state.get('active_sub_agent', 'unknown')}): {response}")
        
        # Update our running state
        state = final_state
        # Ensure we keep messages as a running list if we need to 
        # (langgraph usually manages this if using MessageGraph, but we are managing state manually here)
        
if __name__ == "__main__":
    main()
