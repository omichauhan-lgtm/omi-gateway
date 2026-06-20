import json
import os

def generate_datasets():
    target_dir = "benchmarks/datasets"
    os.makedirs(target_dir, exist_ok=True)
    
    # 1. Customer Support (100 samples)
    support_data = []
    issues = [
        "payment failure for subscription renewal", "refund policy for international orders",
        "update billing details and email address", "account lockouts due to multiple failed passwords",
        "missing shipment containing medical goods", "invoice mismatch on regional tax/GST percentage",
        "cancellation request for business enterprise plan", "API rate limit adjustments for sandbox keys",
        "mismatched promo code applied during checkout", "device sync failures across Android and iOS apps"
    ]
    for i in range(100):
        issue = issues[i % len(issues)]
        support_data.append({
            "id": f"support_{i+1}",
            "prompt": f"Customer Issue: My {issue}. Please resolve this immediately as it is affecting our workflow. Account Email: support-user-{i+1}@enterprise.com. Details: User is frustrated, query requires step-by-step diagnostic resolution guidelines.",
            "complexity_score": 0.35 + (i % 5) * 0.1
        })
        
    # 2. Coding Tasks (100 samples)
    coding_data = []
    tasks = [
        "implement a thread-safe Singleton pattern in C++", "optimize a SQL query with multiple JOINs and index scans",
        "write a python binary search tree traversal function", "refactor a Javascript React component to use hooks",
        "handle connection pool timeouts in a Go web server", "generate unit tests for a Python FastAPI endpoint",
        "validate JWT signatures using RS256 algorithms in Rust", "design a custom database schema for an e-commerce cart",
        "optimize memory footprint of a large Pandas dataframe", "implement clean exponential backoff retry logic in bash"
    ]
    for i in range(100):
        task = tasks[i % len(tasks)]
        coding_data.append({
            "id": f"coding_{i+1}",
            "prompt": f"Coding Challenge: Please {task}. Follow PEP 8 guidelines or equivalent standard conventions. Provide full docstrings, write clean, robust code with error handling, and explain the time complexity.",
            "complexity_score": 0.6 + (i % 4) * 0.1
        })

    # 3. Summarization (80 samples)
    summarization_data = []
    text_templates = [
        "The recent amendment to Article 21 of the Constitution reinforces fundamental rights. In a landmark judgment, the Supreme Court declared that digital privacy is a core constituent of individual liberty, stating that state surveillance must be governed by proportionality. The legislative implications require public sector departments to revise their data processing protocols, align API accesses with MeitY draft compliance rules, and set strict security boundaries.",
        "Sovereign cloud compute expansion in developing regions has accelerated local LLM research. By hosting local inference centers, agencies reduce dependency on international service providers, decrease foreign transit latency, and preserve data boundary guidelines. This structure mitigates risk of silent policy mutations or model drift and ensures Indic-language tokens are parsed efficiently without overhead.",
        "Financial technology loan underwriting models rely heavily on data integrity and calibration. Traditional credit scores are augmented with real-time transaction telemetry, cash-flow indicators, and tax filing verification. To prevent uncalibrated decisions or biased outcomes, compliance engines enforce expected calibration boundaries, quarantining skewed data loops."
    ]
    for i in range(80):
        text = text_templates[i % len(text_templates)]
        summarization_data.append({
            "id": f"summarize_{i+1}",
            "prompt": f"Text to Summarize: {text} Context: Focus on extracting legal and structural compliance mandates. Generate a 2-sentence executive summary with bullet points of key outcomes.",
            "complexity_score": 0.45 + (i % 3) * 0.15
        })

    # 4. Retrieval Augmented Generation (80 samples)
    rag_data = []
    for i in range(80):
        rag_data.append({
            "id": f"rag_{i+1}",
            "prompt": f"RAG Query: Summarize the policy recommendations for Indic language model training. Document Context 1: MeitY proposes subsidies for Indic dataset curation, focusing on regional dialects. Document Context 2: Tokenizer inefficiency on Devanagari text increases query cost by 3.1x, requiring custom local vocabulary optimizations. Task: Extract recommendations based strictly on these document contexts.",
            "complexity_score": 0.5 + (i % 3) * 0.15
        })

    # 5. Multilingual Indic (80 samples)
    indic_data = []
    phrases = [
        "Translate agricultural crop health advisory regarding rice blast disease to Telugu and Marathi.",
        "Translate the citizen query about water supply connection renewal to Hindi and Kannada.",
        "Translate educational primary school math learning syllabus guidelines to Tamil and Bengali.",
        "Translate the local trade licensing permit application rules to Marathi and Gujarati."
    ]
    for i in range(80):
        phrase = phrases[i % len(phrases)]
        indic_data.append({
            "id": f"indic_{i+1}",
            "prompt": f"Indic translation: Please {phrase}. Ensure that the translated terminology remains culturally context-aware, preserves original technical instructions, and avoids literal translation errors.",
            "complexity_score": 0.4 + (i % 4) * 0.12
        })

    # 6. Enterprise Workflows (60 samples)
    enterprise_data = []
    workflows = [
        "verify compliance of candidate resume against corporate anti-nepotism policies",
        "validate business travel expenses voucher against company mileage allowance caps",
        "audit system logs for unauthorized read accesses on database customer tables",
        "reconcile invoice billing items against negotiated contract price guidelines"
    ]
    for i in range(60):
        w = workflows[i % len(workflows)]
        enterprise_data.append({
            "id": f"enterprise_{i+1}",
            "prompt": f"Workflow Task: Please {w}. Output a boolean compliance decision and list any items that breach corporate governance rules. Follow standard structured JSON format outputs.",
            "complexity_score": 0.55 + (i % 3) * 0.15
        })

    # Write files
    datasets_map = {
        "customer_support.json": support_data,
        "coding_tasks.json": coding_data,
        "summarization.json": summarization_data,
        "retrieval_augmented_generation.json": rag_data,
        "multilingual_indic.json": indic_data,
        "enterprise_workflows.json": enterprise_data
    }
    
    for filename, data in datasets_map.items():
        path = os.path.join(target_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Generated {len(data)} samples in {path}")

if __name__ == "__main__":
    generate_datasets()
