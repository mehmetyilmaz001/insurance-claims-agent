POLICIES = {
    "POL-123": {
        "policy_number": "POL-123",
        "policy_holder": "Alex Morgan",
        "product": "Motor Insurance",
        "status": "active"
    }
}

def lookup_policy(policy_number: str) -> dict | None:
    """Return a fictional policy record, or None if it is unknown."""
    return POLICIES.get(policy_number)

def main():
    known_policy = lookup_policy("POL-123")
    print("Known policy:")
    print(known_policy)
    
    unknown_policy = lookup_policy("POL-999")
    print("Unknown Policy")
    print(unknown_policy)
    
if __name__ == "__main__":
    main()