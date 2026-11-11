from eval_cases import CASES
from try_model import extract_claim

case = CASES[0]
result = extract_claim({"description": case["description"]})

print("Expected:", case["expected"])
print("Actual:", result["claim"])