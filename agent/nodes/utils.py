import os
from typing import Dict, Any

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain import hub

from agent.tools import execute_sql_query
from agent.state import AgentState

FALLBACK_PROMPTS = {
    "order-status-agent": "order_status.txt",
    "product-query-agent": "product_query.txt",
    "returns-agent": "returns.txt",
    "recommendation-agent": "recommendation.txt",
}

def pull_prompt_with_fallback(prompt_name: str) -> ChatPromptTemplate:
    """Pull prompt from LangSmith Hub with fallback to default tenant and then local files."""
    handle = os.getenv("LANGSMITH_HUB_HANDLE")
    
    # 1. Try pulling with handle prefix
    if handle:
        full_name = f"{handle}/{prompt_name}"
        try:
            print(f"Attempting to pull prompt '{full_name}' from LangSmith Hub...")
            return hub.pull(full_name)
        except Exception as e:
            print(f"Failed to pull '{full_name}': {e}.")
            
    # 2. Try pulling without handle prefix (default tenant)
    try:
        print(f"Attempting to pull prompt '{prompt_name}' from LangSmith Hub default tenant...")
        return hub.pull(prompt_name)
    except Exception as e:
        print(f"Failed to pull '{prompt_name}' from default tenant: {e}.")
        
    # 3. Local file fallback
    filename = FALLBACK_PROMPTS.get(prompt_name)
    if not filename:
        raise ValueError(f"Unknown prompt name: {prompt_name}")
        
    print(f"Loading local fallback prompt for '{prompt_name}' from prompts/{filename}...")
    filepath = os.path.join("prompts", filename)
    with open(filepath, "r") as f:
        template_text = f.read()
        
    return ChatPromptTemplate.from_template(template_text)

def check_if_unresolved(agent_name: str, content: str) -> bool:
    """Heuristic check to determine if the agent needs clarification or couldn't find details."""
    content_lower = content.lower()
    if agent_name == "order_status":
        if any(k in content_lower for k in [
            "clarify", "confirm", "which order", "order id", "provide your order id", 
            "please provide", "not found", "which of these", "please specify"
        ]):
            return True
    elif agent_name == "product_query":
        if any(k in content_lower for k in [
            "clarify", "confirm", "which product", "did you mean", "could not find", 
            "not found", "suggest a similar", "which one", "please specify"
        ]):
            return True
    elif agent_name == "returns":
        if any(k in content_lower for k in [
            "clarify", "confirm", "which order", "provide the order id", "not found"
        ]):
            return True
    return False

def run_sub_agent(
    state: AgentState,
    prompt_name: str,
    agent_name: str
) -> Dict[str, Any]:
    """Execute a robust, explicit tool-calling loop with the SQLite database helper."""
    # 1. Initialize LLM
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0
    )
    llm_with_tools = llm.bind_tools([execute_sql_query])

    # 2. Fetch and format the prompt
    prompt = pull_prompt_with_fallback(prompt_name)
    
    customer_id = state.get("customer_id", "Unknown")
    context_dict = state.get("follow_up_context", {})
    last_message = state["messages"][-1].content

    # Format system prompt text safely depending on prompt type
    if hasattr(prompt, "format_messages"):
        formatted_messages = prompt.format_messages(
            customer_id=customer_id,
            context=str(context_dict),
            input=last_message,
            agent_scratchpad=""
        )
        system_prompt_text = "\n".join([m.content for m in formatted_messages])
    else:
        system_prompt_text = prompt.format(
            customer_id=customer_id,
            context=str(context_dict),
            input=last_message,
            agent_scratchpad=""
        )
        
    system_prompt_text = system_prompt_text.replace("{agent_scratchpad}", "").strip()

    # 3. Setup messages
    messages = [
        SystemMessage(content=system_prompt_text),
        HumanMessage(content=last_message)
    ]

    # 4. Tool-calling loop
    print(f"Running custom tool-calling loop for: {agent_name}...")
    max_iterations = 5
    for i in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        
        if not response.tool_calls:
            print(f"Loop finished: no more tool calls at iteration {i}.")
            break
            
        # Handle tool calls
        for tool_call in response.tool_calls:
            if tool_call["name"] == "execute_sql_query":
                query = tool_call["args"].get("query")
                print(f"[{agent_name} Agent] Invoking SQL: {query}")
                tool_output = execute_sql_query.invoke({"query": query})
                messages.append(
                    ToolMessage(
                        content=tool_output,
                        name="execute_sql_query",
                        tool_call_id=tool_call["id"]
                    )
                )

    response_content = messages[-1].content
    is_unresolved = check_if_unresolved(agent_name, response_content)
    print(f"Agent {agent_name} response is_unresolved: {is_unresolved}")

    return {
        "messages": [
            AIMessage(content=response_content)
        ],
        "active_sub_agent": agent_name,
        "is_unresolved": is_unresolved
    }