import os
import dotenv
import logging
import sys
import click
from ynab_api.client import YNABClient
from ai_chat.handler import ChatHandler
from agents.parser_agent import TransactionParser

# Load environment variables
dotenv.load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cli_test')

@click.command()
def test_connection():
    """Test YNAB and OpenAI connections"""
    client = YNABClient("test_key")
    parser = TransactionParser("test_key")
    
    print("Testing connections...")
    # Add simple connection tests here

def main():
    print("\n🎬 Starting YNAB Assistant")
    print("=" * 50)
    
    # Get credentials from environment
    api_key = os.getenv("YNAB_API_KEY")
    budget_id = os.getenv("YNAB_BUDGET_ID")
    
    if not api_key:
        logger.error("YNAB API key not found in environment")
        print("Error: YNAB API key not found. Please set YNAB_API_KEY environment variable.")
        return
        
    try:
        # Initialize clients with real API
        ynab_client = YNABClient(api_key=api_key, budget_id=budget_id)
        chat_handler = ChatHandler()
        
        # Test basic budget info
        print("\nFetching budget info...")
        budgets = ynab_client.get_budgets()
        print(f"Found {len(budgets)} budgets")
        
        # Test categories
        print("\nFetching categories...")
        categories = ynab_client.get_categories()
        category_count = sum(len(g['categories']) for g in categories)
        print(f"Found {category_count} categories in {len(categories)} groups")
        
        # Test transactions
        print("\nFetching recent transactions...")
        transactions = ynab_client.get_transactions()
        print(f"Found {len(transactions)} transactions")
        
        # Test chat
        print("\nTesting chat interaction...")
        context = {
            'budget_name': budgets[0]['name'] if budgets else 'Unknown',
            'recent_transactions': f"Found {len(transactions)} recent transactions",
            'categories': f"Found {category_count} categories"
        }
        
        test_prompts = [
            "How many transactions do I have?",
            "What categories are available?",
            "Show me my budget summary"
        ]
        
        for prompt in test_prompts:
            print(f"\nTest prompt: {prompt}")
            response = chat_handler.get_response(prompt, context)
            print(f"Response: {response}")
            
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main() 