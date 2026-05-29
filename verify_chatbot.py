import sqlite3
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agent.graph import build_graph
from agent.state import AgentState

def print_separator(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ".center(80, "="))
    print("="*80 + "\n")

def verify_database():
    print_separator("Database Verification")
    db_path = "ecommerce.db"
    if not os.path.exists(db_path):
        print(f"FAIL: {db_path} does not exist!")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check tables exist
    tables = ['customers', 'products', 'orders', 'returns']
    for t in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
        if not cursor.fetchone():
            print(f"FAIL: Table '{t}' does not exist!")
            sys.exit(1)
    print("[OK] All 4 tables exist in database.")
    
    # 2. Check row counts
    counts = {}
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cursor.fetchone()[0]
        print(f"[OK] Table '{t}' row count: {counts[t]}")
        if counts[t] == 0:
            print(f"FAIL: Table '{t}' is empty!")
            sys.exit(1)
            
    # 3. Customer order distribution
    cursor.execute("SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id HAVING COUNT(*) > 1")
    multi_order_cust = len(cursor.fetchall())
    print(f"[OK] Customers with multiple orders: {multi_order_cust} (Requirement: at least 10)")
    if multi_order_cust < 10:
        print("FAIL: Less than 10 customers have multiple orders!")
        sys.exit(1)
        
    # 4. Products out of stock
    cursor.execute("SELECT COUNT(*) FROM products WHERE stock = 0")
    zero_stock_prod = cursor.fetchone()[0]
    print(f"[OK] Products with zero stock: {zero_stock_prod} (Requirement: at least 5)")
    if zero_stock_prod < 5:
        print("FAIL: Less than 5 products have zero stock!")
        sys.exit(1)
        
    # 5. Referential integrity
    cursor.execute("""
        SELECT COUNT(*) FROM returns r
        JOIN orders o ON r.order_id = o.order_id
        WHERE o.status != 'delivered'
    """)
    invalid_returns = cursor.fetchone()[0]
    print(f"[OK] Returns linked to non-delivered orders: {invalid_returns} (Requirement: 0)")
    if invalid_returns > 0:
        print("FAIL: Referential integrity violated! Returns linked to non-delivered orders.")
        sys.exit(1)
        
    conn.close()
    print("\n[OK] Database Verification Passed successfully!\n")

def test_conversational_flow(graph):
    print_separator("Conversational Flow & Memory Test")
    
    # We will query the DB to find C1001's orders and products so we can simulate the conversation dynamically
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.order_id, p.name, o.status, p.product_id FROM orders o
        JOIN products p ON o.product_id = p.product_id
        WHERE o.customer_id = 'C1001'
    """)
    orders = cursor.fetchall()
    conn.close()
    
    print(f"Customer C1001 orders in database:")
    for o_id, p_name, o_status, p_id in orders:
        print(f"  - Order {o_id}: {p_name} (Status: {o_status})")
        
    if len(orders) < 2:
        print("FAIL: Test requires C1001 to have at least 2 orders.")
        sys.exit(1)
        
    # Pick the second order product for the disambiguation step
    target_order_id, target_product_name, target_status, target_product_id = orders[1]
    
    # Initialize state
    state = {
        "customer_id": "C1001",
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
    
    config = {"tags": ["customer_id:C1001", "environment:testing"]}
    
    # Turn 1: "where is my order?"
    print("\n--- TURN 1: 'where is my order?' ---")
    state["messages"].append(HumanMessage(content="where is my order?"))
    state = graph.invoke(state, config=config)
    print(f"Agent Intent: {state['intent']}")
    print(f"Agent Active Sub-agent: {state['active_sub_agent']}")
    print(f"Agent Response: {state['messages'][-1].content}")
    print(f"Is Unresolved: {state.get('is_unresolved')}")
    
    if state["intent"] != "order_status":
        print("FAIL: Intent should be 'order_status'")
        sys.exit(1)
    if not state.get("is_unresolved"):
        print("FAIL: Should be unresolved due to multiple active orders clarification")
        sys.exit(1)
        
    # Turn 2: Disambiguate by specifying the product
    print(f"\n--- TURN 2: Specify the product '{target_product_name}' ---")
    state["messages"].append(HumanMessage(content=target_product_name))
    state = graph.invoke(state, config=config)
    print(f"Agent Intent: {state['intent']}")
    print(f"Agent Active Sub-agent: {state['active_sub_agent']}")
    print(f"Agent Response: {state['messages'][-1].content}")
    print(f"Follow up Context: {state.get('follow_up_context')}")
    print(f"Is Unresolved: {state.get('is_unresolved')}")
    
    if state["follow_up_context"].get("order_id") != target_order_id:
        print(f"FAIL: Context did not extract target order ID {target_order_id}!")
        sys.exit(1)
    print(f"[OK] Successfully stored order context O1002/O100... matching product '{target_product_name}'")
    
    # Turn 3: "Can I return it?" (using context)
    print("\n--- TURN 3: 'Can I return it?' ---")
    state["messages"].append(HumanMessage(content="Can I return it?"))
    state = graph.invoke(state, config=config)
    print(f"Agent Intent: {state['intent']}")
    print(f"Agent Active Sub-agent: {state['active_sub_agent']}")
    print(f"Agent Response: {state['messages'][-1].content}")
    print(f"Is Unresolved: {state.get('is_unresolved')}")
    
    if state["intent"] != "return_request":
        print("FAIL: Intent should be 'return_request'")
        sys.exit(1)
    if state["active_sub_agent"] != "returns":
        print("FAIL: Active sub-agent should be 'returns'")
        sys.exit(1)
        
    print("\n[OK] Conversational Flow and Memory Test Passed successfully!\n")

def test_unknown_escalation(graph):
    print_separator("Unknown Intent Escalation Test (2+ turns)")
    state = {
        "customer_id": "C1001",
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
    
    config = {"tags": ["customer_id:C1001", "environment:testing"]}
    
    # Turn 1: gibberish
    print("\n--- TURN 1: gibberish ---")
    state["messages"].append(HumanMessage(content="asdfghjkl"))
    state = graph.invoke(state, config=config)
    print(f"Intent: {state['intent']}, Unknown Turns: {state['unknown_turns']}, Escalated: {state['escalation_flag']}")
    
    if state["intent"] != "unknown" or state["unknown_turns"] != 1 or state["escalation_flag"]:
        print("FAIL: Should be unknown turn 1 and not escalated yet")
        sys.exit(1)
        
    # Turn 2: gibberish again
    print("\n--- TURN 2: gibberish again ---")
    state["messages"].append(HumanMessage(content="what is the meaning of life?"))
    state = graph.invoke(state, config=config)
    print(f"Intent: {state['intent']}, Unknown Turns: {state['unknown_turns']}, Escalated: {state['escalation_flag']}")
    print(f"Response: {state['messages'][-1].content}")
    
    if not state["escalation_flag"] or state["active_sub_agent"] != "fallback":
        print("FAIL: Should escalate to fallback on 2nd unknown turn")
        sys.exit(1)
        
    print("\n[OK] Unknown Intent Escalation Test Passed successfully!\n")

def test_unresolved_same_intent_escalation(graph):
    print_separator("Unresolved same-intent escalation test (3 turns)")
    state = {
        "customer_id": "C1001",
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
    
    config = {"tags": ["customer_id:C1001", "environment:testing"]}
    
    # Send "where is my order?" 3 times, without providing a specific order, which keeps it unresolved
    for i in range(1, 4):
        print(f"\n--- TURN {i}: 'where is my order?' ---")
        state["messages"].append(HumanMessage(content="where is my order?"))
        state = graph.invoke(state, config=config)
        print(f"Intent: {state['intent']}")
        print(f"Unresolved Count: {state.get('unresolved_count')}")
        print(f"Is Unresolved: {state.get('is_unresolved')}")
        print(f"Escalation Flag: {state.get('escalation_flag')}")
        print(f"Active Sub-agent: {state.get('active_sub_agent')}")
        print(f"Response: {state['messages'][-1].content[:120]}...")
        
    if not state["escalation_flag"] or state["active_sub_agent"] != "fallback":
        print("FAIL: Should escalate to fallback on 3rd unresolved same-intent turn")
        sys.exit(1)
        
    print("\n[OK] Unresolved Same-Intent Escalation Test Passed successfully!\n")

def main():
    load_dotenv()
    verify_database()
    
    graph = build_graph()
    
    test_conversational_flow(graph)
    test_unknown_escalation(graph)
    test_unresolved_same_intent_escalation(graph)
    
    print("\n" + "="*80)
    print(" ALL TESTS PASSED SUCCESSFULLY! ".center(80, "*"))
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
