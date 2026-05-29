import os
from langchain import hub
from dotenv import load_dotenv

def push_prompts():
    load_dotenv()
    
    handle = os.getenv("LANGSMITH_HUB_HANDLE")
    if not handle:
        print("Error: LANGSMITH_HUB_HANDLE is not set in .env")
        return
        
    prompts = {
        "order-status-agent": "order_status.txt",
        "product-query-agent": "product_query.txt",
        "returns-agent": "returns.txt",
        "recommendation-agent": "recommendation.txt",
    }
    
    for prompt_name, filename in prompts.items():
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            print(f"Skipping {prompt_name}: {filename} not found.")
            continue
            
        with open(filepath, "r") as f:
            template_text = f.read()
            
        # The prompt needs to be an object to push to hub, usually a ChatPromptTemplate
        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_template(template_text)
        
        full_name = f"{handle}/{prompt_name}"
        try:
            hub.push(full_name, prompt)
            print(f"Successfully pushed {full_name}")
        except Exception as e:
            print(f"Failed to push {full_name}: {e}")
            print(f"Attempting to push {prompt_name} directly without handle prefix...")
            try:
                hub.push(prompt_name, prompt)
                print(f"Successfully pushed {prompt_name} to default tenant")
            except Exception as e2:
                print(f"Failed to push {prompt_name}: {e2}")

if __name__ == "__main__":
    push_prompts()
