import json

path = r"F:\JETinc\JETcity_Launchpad\jetinc_build\benchmark_results.json"

with open(path, "r") as f:
    data = json.load(f)

for item in data:
    tid = item["task_id"]
    b_score = item["baseline_score"]
    b_halluc = item["baseline_hallucinated"]
    d_score = item["deliberated_score"]
    d_halluc = item["deliberated_hallucinated"]
    print(f"{tid}: baseline={b_score}/{b_halluc}   deliberated={d_score}/{d_halluc}")
