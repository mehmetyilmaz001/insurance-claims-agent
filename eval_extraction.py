from eval_cases import CASES
from try_model import extract_claim

failed = 0
total = 0

for case in CASES:
    print(f"\nCase: {case['name']}")
    result = extract_claim({"description": case["description"]})

    if result.get("status") == "extraction_failed":
        raise SystemExit(result["message"].strip())

    for field, expected_value in case["expected"].items():
        total += 1
        actual_value = result["claim"].get(field)
        passed = actual_value == expected_value
        if not passed:
            failed += 1
        outcome = "PASS" if passed else "FAIL"
        print(f"{field}: {outcome} (expected {expected_value!r}, got {actual_value!r})")

print(f"\nSummary: {total - failed}/{total} checks passed")
if failed:
    raise SystemExit(1)
