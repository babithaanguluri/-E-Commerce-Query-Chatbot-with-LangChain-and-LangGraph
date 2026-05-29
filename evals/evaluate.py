import json
import os
import time
import random
from langsmith import Client
from langsmith.evaluation import evaluate
from dotenv import load_dotenv

from agent.state import AgentState
from agent.nodes.classifier import classifier_node
from langchain_core.messages import HumanMessage

def intent_classifier_wrapper(inputs: dict) -> dict:
    """Wrapper function to adapt dataset inputs to the node's expected state."""
    state = AgentState(
        customer_id="test",
        messages=[HumanMessage(content=inputs["query"])],
        intent="",
        active_sub_agent="",
        db_query_results={},
        follow_up_context={},
        escalation_flag=False,
        turn_count=0,
        unresolved_count=0,
        is_unresolved=False,
        unknown_turns=0
    )
    
    max_retries = 6
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            # The classifier_node expects a state dictionary
            result = classifier_node(state)
            return {"classified_intent": result.get("intent")}
        except Exception as e:
            err_msg = str(e).lower()
            if "rate_limit" in err_msg or "429" in err_msg or "limit reached" in err_msg or "tpm" in err_msg:
                if attempt == max_retries - 1:
                    print(f"Max retries reached for query '{inputs.get('query')}'. Error: {e}")
                    raise e
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1.5)
                print(f"Rate limit hit for query '{inputs.get('query')}'. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"Non-rate-limit error classifying intent for query '{inputs.get('query')}': {e}")
                raise e

def exact_match_evaluator(run, example) -> dict:
    """Custom scoring function to check if intent matches exactly."""
    if run.error or not run.outputs or "classified_intent" not in run.outputs:
        return {"key": "intent_accuracy", "score": 0.0}
    expected_intent = example.outputs["intent"]
    predicted_intent = run.outputs["classified_intent"]
    score = 1.0 if expected_intent == predicted_intent else 0.0
    return {"key": "intent_accuracy", "score": score}

def run_evaluation():
    load_dotenv()
    
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("Error: LANGCHAIN_API_KEY is not set.")
        return

    client = Client()
    dataset_name = "E-Commerce Intent Classification"
    
    # 1. Load data
    with open(os.path.join(os.path.dirname(__file__), "dataset.json"), "r") as f:
        data = json.load(f)

    # 2. Check if dataset exists, if not create it
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Dataset for testing intent classification accuracy."
        )
        for example in data:
            client.create_example(
                inputs={"query": example["query"]},
                outputs={"intent": example["intent"]},
                dataset_id=dataset.id
            )
        print(f"Created dataset: {dataset_name}")
    else:
        print(f"Using existing dataset: {dataset_name}")

    # 3. Run evaluation
    print("Running evaluation...")
    experiment_results = evaluate(
        intent_classifier_wrapper,
        data=dataset_name,
        evaluators=[exact_match_evaluator],
        experiment_prefix="intent-classifier-eval",
        metadata={"environment": "testing"},
        max_concurrency=2
    )
    
    print("\nEvaluation complete! View results in LangSmith.")

if __name__ == "__main__":
    run_evaluation()
