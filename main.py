import os
from dotenv import load_dotenv
from ynab_api.client import YNABClient
from agents.parser_agent import TransactionParser

def main():
    load_dotenv()
    
    # Initialize YNAB client
    ynab = YNABClient(
        api_key=os.getenv('YNAB_API_KEY')
    )
    
    # Initialize parser
    parser = TransactionParser(
        openai_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Ready to go!
    print("YNAB Assistant ready! 🚀")

if __name__ == "__main__":
    main() 