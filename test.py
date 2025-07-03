import requests
import time
import logging
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

endpoint = "http://localhost:8000/chat"

def run_test_with_context(test_case: Dict, previous_responses: List[Dict] = None):
    """Run a test case with context from previous responses"""
    history = []
    if previous_responses:
        for prev in previous_responses:
            history.append({"role": "user", "content": prev["query"]})
            history.append({"role": "assistant", "content": prev["response"]})

    logging.info(f"\n=== Running Test: {test_case['name']} ===")
    logging.info(f"Description: {test_case.get('description', 'N/A')}")
    logging.info(f"Query: {test_case['message']}")
    
    try:
        res = requests.post(endpoint, json={
            "message": test_case["message"],
            "history": history
        })
        
        if res.ok:
            response = res.json().get("response", "")
            logging.info("\nResponse received:")
            logging.info("-" * 80)
            logging.info(response)
            logging.info("-" * 80)
            return {
                "status": "passed",
                "query": test_case["message"],
                "response": response
            }
        else:
            logging.error(f"Request failed: {res.text}")
            return {"status": "failed", "error": res.text}
            
    except Exception as e:
        logging.error(f"Test execution error: {str(e)}")
        return {"status": "failed", "error": str(e)}

# Multi-step test cases that require tool chaining
test_suites = [
    {
        "name": "Privacy Rights Evolution Analysis",
        "description": "Tests the system's ability to analyze legal evolution through multiple cases",
        "steps": [
            {
                "name": "Initial Case Search",
                "message": "Find the landmark Supreme Court case that established privacy as a fundamental right in India."
            },
            {
                "name": "Detailed Analysis",
                "message": "Summarize the main principles established in this privacy judgment and how it affects digital rights."
            },
            {
                "name": "Comparative Analysis",
                "message": "Compare this with previous Supreme Court judgments on privacy rights before this landmark case."
            }
        ]
    },
    {
        "name": "Environmental Rights Research",
        "description": "Tests the system's ability to research and synthesize information from multiple sources",
        "steps": [
            {
                "name": "Recent Cases",
                "message": "Find recent Supreme Court judgments related to environmental protection under Article 21."
            },
            {
                "name": "Principle Extraction",
                "message": "Summarize the key environmental principles established in these judgments."
            },
            {
                "name": "Implementation Analysis",
                "message": "How have these environmental principles been implemented in subsequent High Court judgments?"
            }
        ]
    },
    {
        "name": "Legal Document Analysis",
        "description": "Tests the system's ability to analyze legal documents and their implications",
        "steps": [
            {
                "name": "Document Analysis",
                "message": "Find and summarize the latest Supreme Court judgment on cryptocurrency regulation in India."
            },
            {
                "name": "Impact Analysis",
                "message": "Based on this judgment, explain the current legal status of cryptocurrency trading in India."
            },
            {
                "name": "Regulatory Framework",
                "message": "What are the key RBI guidelines that apply to cryptocurrency transactions based on this judgment?"
            }
        ]
    }
]

def run_test_suite():
    """Run all test suites and collect results"""
    suite_results = []
    
    for suite in test_suites:
        logging.info(f"\n=== Starting Test Suite: {suite['name']} ===")
        step_results = []
        
        for step in suite['steps']:
            result = run_test_with_context(step, step_results)
            if result["status"] == "passed":
                step_results.append(result)
            else:
                logging.error(f"Test suite '{suite['name']}' failed at step '{step['name']}'")
                break
            time.sleep(2)  # Prevent rate limiting
        
        suite_results.append({
            "name": suite["name"],
            "steps_completed": len(step_results),
            "total_steps": len(suite["steps"]),
            "status": "passed" if len(step_results) == len(suite["steps"]) else "failed"
        })
        
    return suite_results

def analyze_results(results: List[Dict]):
    """Analyze and display test results"""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = total - passed
    
    logging.info("\n=== Test Suite Results ===")
    logging.info(f"Total Test Suites: {total}")
    logging.info(f"Passed: {passed}")
    logging.info(f"Failed: {failed}")
    
    logging.info("\nDetailed Results:")
    for result in results:
        logging.info(f"\n{result['name']}:")
        logging.info(f"Status: {result['status']}")
        logging.info(f"Steps Completed: {result['steps_completed']}/{result['total_steps']}")

if __name__ == "__main__":
    logging.info("Starting Jurisol Multi-Tool Test Suite...")
    results = run_test_suite()
    analyze_results(results)