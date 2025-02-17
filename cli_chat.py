import os
import dotenv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ai_chat.handler import ChatHandler
from utils.logger import setup_logger
from ynab_api.client import YNABClient

# Load environment variables
dotenv.load_dotenv()

def main():
    # Set up logging
    logger = setup_logger('cli_chat')
    logger.info("Starting YNAB CLI Chat")
    
    # Get credentials from environment
    api_key = os.getenv("YNAB_API_KEY")
    budget_id = os.getenv("YNAB_BUDGET_ID")
    
    if not api_key:
        logger.error("YNAB API key not found in environment")
        print("Error: YNAB API key not found. Please set YNAB_API_KEY environment variable.")
        return
        
    try:
        # Initialize clients - using exact same clients as UI
        ynab_client = YNABClient(api_key=api_key, budget_id=budget_id)
        chat_handler = ChatHandler()
        
        print("\nYNAB AI Assistant CLI 💰")
        print("Chat with your budget! Type 'quit' to exit.\n")
        
        while True:
            # Get user input
            prompt = input("\nYou: ").strip()
            if prompt.lower() == 'quit':
                break
                
            try:
                # Gather context - using same context building as UI
                context = {}
                
                # Get categories
                categories = ynab_client.get_categories()
                if categories:
                    # Summarize by category group
                    group_summary = []
                    category_summary = []
                    
                    for group in categories:
                        if not group['hidden'] and not group['deleted']:
                            group_total_budgeted = 0
                            group_total_activity = 0
                            group_categories = []
                            
                            for cat in group['categories']:
                                if not cat['hidden'] and not cat['deleted']:
                                    cat_budgeted = ynab_client.milliunits_to_dollars(cat['budgeted'])
                                    cat_activity = ynab_client.milliunits_to_dollars(cat['activity'])
                                    group_total_budgeted += cat_budgeted
                                    group_total_activity += cat_activity
                                    
                                    category_summary.append(
                                        f"{cat['name']}: Budgeted ${cat_budgeted:.2f}, "
                                        f"Activity ${cat_activity:.2f}, "
                                        f"Balance ${ynab_client.milliunits_to_dollars(cat['balance']):.2f}"
                                    )
                                    group_categories.append(cat['name'])
                                    
                            group_summary.append(
                                f"{group['name']}: Total Budgeted ${group_total_budgeted:.2f}, "
                                f"Total Activity ${group_total_activity:.2f}, "
                                f"Categories: {', '.join(group_categories)}"
                            )
                            
                    context['category_groups'] = "\n".join(group_summary)
                    context['categories'] = "\n".join(category_summary)
                
                # Get recent transactions
                since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                recent_txns = ynab_client.get_transactions(since_date=since_date)
                
                if recent_txns:
                    # Calculate income vs expenses
                    total_income = sum(
                        ynab_client.milliunits_to_dollars(tx['amount']) 
                        for tx in recent_txns if tx['amount'] > 0
                    )
                    total_expenses = abs(sum(
                        ynab_client.milliunits_to_dollars(tx['amount']) 
                        for tx in recent_txns if tx['amount'] < 0
                    ))
                    net_flow = total_income - total_expenses
                    
                    context['recent_transactions'] = (
                        f"Last 7 days: Income ${total_income:.2f}, "
                        f"Expenses ${total_expenses:.2f}, "
                        f"Net ${net_flow:.2f}"
                    )
                    
                    # Add detailed transaction list
                    transaction_details = []
                    for tx in recent_txns[:10]:
                        amount = ynab_client.milliunits_to_dollars(tx['amount'])
                        transaction_details.append(
                            f"{tx['date']}: {tx.get('payee_name', 'Unknown')} - "
                            f"${abs(amount):.2f} ({'income' if amount > 0 else 'expense'})"
                        )
                    context['transaction_details'] = "\n".join(transaction_details)
                
                # Get month summary
                month_summary = ynab_client.get_month_summary()
                if month_summary:
                    to_be_budgeted = ynab_client.milliunits_to_dollars(month_summary.get('to_be_budgeted', 0))
                    budgeted = ynab_client.milliunits_to_dollars(month_summary.get('budgeted', 0))
                    activity = ynab_client.milliunits_to_dollars(month_summary.get('activity', 0))
                    
                    context['category_status'] = (
                        f"To Be Budgeted: ${to_be_budgeted:.2f}, "
                        f"Total Budgeted: ${budgeted:.2f}, "
                        f"Total Activity: ${activity:.2f}"
                    )
                
                # Get AI response using same chat handler as UI
                response = chat_handler.get_response(prompt, context)
                print(f"\nAssistant: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                print(f"\nOops! Something went wrong: {str(e)} 😅")
                
        print("\nThanks for chatting! See you next time! 👋")
        
    except Exception as e:
        logger.error(f"Failed to initialize clients: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 