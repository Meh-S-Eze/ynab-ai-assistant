from agents.coordinator import CoordinatorAgent

def main():
    # Create our friendly budget buddy
    buddy = CoordinatorAgent()
    
    # Test some example interactions
    test_requests = [
        # Categorization
        "Can you categorize 'Point Of Sale Withdrawal NOCD / INC: WWW.TREATMYOCILUS' as Medical?",
        
        # Spending queries
        "How much have I spent on medical expenses this month?",
        "What's my health and wellness spending like?",
        
        # Error cases
        "Can you categorize something that doesn't exist?",
        "How much did I spend on fake category?"
    ]
    
    # Try each request
    for request in test_requests:
        print("\nUser:", request)
        response = buddy.handle_request(request)
        print("Buddy:", response)
        
if __name__ == "__main__":
    main() 