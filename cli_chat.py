import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ai_chat.handler import ChatHandler
from utils.logger import setup_logger
import pandas as pd

class YNABTestClient:
    def __init__(self, data_dir: str = "test_data"):
        self.logger = setup_logger('ynab_test_client')
        self.budget_file = os.path.join(data_dir, "MVP AI AGENTS as of 2025-02-16 19-55 - Budget.csv")
        self.register_file = os.path.join(data_dir, "MVP AI AGENTS as of 2025-02-16 19-55 - Register.csv")
        
        # Load data
        self.budget_data = pd.read_csv(self.budget_file)
        self.transactions = pd.read_csv(self.register_file)
        
        # Convert numeric columns to float
        budget_columns = ['Budgeted', 'Activity', 'Available']
        for col in budget_columns:
            if col in self.budget_data.columns:
                self.budget_data[col] = pd.to_numeric(
                    self.budget_data[col].str.replace('$', '').str.replace(',', ''), 
                    errors='coerce'
                ).fillna(0)
        
        # Convert Inflow/Outflow to float and calculate Amount
        if 'Inflow' in self.transactions.columns and 'Outflow' in self.transactions.columns:
            self.transactions['Inflow'] = pd.to_numeric(
                self.transactions['Inflow'].str.replace('$', '').str.replace(',', ''), 
                errors='coerce'
            ).fillna(0)
            
            self.transactions['Outflow'] = pd.to_numeric(
                self.transactions['Outflow'].str.replace('$', '').str.replace(',', ''), 
                errors='coerce'
            ).fillna(0)
            
            # Calculate Amount (Inflow - Outflow)
            self.transactions['Amount'] = self.transactions['Inflow'] - self.transactions['Outflow']
        
        # Clean up category names
        self.budget_data['Category Group'] = self.budget_data['Category Group'].fillna('Uncategorized')
        self.budget_data['Category'] = self.budget_data['Category'].fillna('Uncategorized')
        
        self.logger.info(f"Loaded {len(self.budget_data)} budget items and {len(self.transactions)} transactions")

    def get_categories(self) -> List[Dict]:
        """Get all categories grouped"""
        categories = []
        for group_name, group_data in self.budget_data.groupby('Category Group'):
            if group_name == 'Uncategorized':
                continue
                
            group = {
                'name': group_name,
                'hidden': False,
                'deleted': False,
                'categories': []
            }
            
            for _, row in group_data.iterrows():
                category = {
                    'name': row['Category'],
                    'hidden': False,
                    'deleted': False,
                    'budgeted': row['Budgeted'] * 1000,  # Convert to milliunits
                    'activity': row['Activity'] * 1000,
                    'balance': row['Available'] * 1000
                }
                group['categories'].append(category)
                
            categories.append(group)
            
        return categories

    def get_transactions(self, since_date: Optional[str] = None) -> List[Dict]:
        """Get transactions, optionally filtered by date"""
        if since_date:
            mask = pd.to_datetime(self.transactions['Date']) >= pd.to_datetime(since_date)
            txns = self.transactions[mask]
        else:
            txns = self.transactions
            
        transactions = []
        for _, row in txns.iterrows():
            transaction = {
                'id': str(row.name),  # Use index as ID
                'date': row['Date'],
                'payee_name': row['Payee'],
                'category_name': row['Category'],
                'memo': row['Memo'] if pd.notna(row['Memo']) else '',
                'amount': int(row['Amount'] * 1000)  # Convert to milliunits
            }
            transactions.append(transaction)
            
        return transactions

    def find_category_by_name(self, name: str) -> Optional[Dict]:
        """Find a category by name (case-insensitive partial match)"""
        name = name.lower()
        
        # Map common category names to actual categories
        category_map = {
            'medical': 'Health & Wellness',
            'health': 'Health & Wellness',
            'healthcare': 'Health & Wellness'
        }
        
        # Check if we have a direct mapping
        if name in category_map:
            name = category_map[name].lower()
        
        for _, row in self.budget_data.iterrows():
            category_name = str(row['Category']).lower()
            if name in category_name:
                return {
                    'id': str(row.name),  # Use index as ID
                    'name': row['Category'],
                    'group': row['Category Group']
                }
        return None

    def find_transaction_by_description(self, description: str, days_back: int = 30) -> Optional[Dict]:
        """Find a transaction by description (case-insensitive partial match)"""
        description = description.lower()
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        recent_txns = self.transactions[
            pd.to_datetime(self.transactions['Date']) >= pd.to_datetime(since_date)
        ]
        
        for _, row in recent_txns.iterrows():
            payee = str(row['Payee']).lower()
            memo = str(row['Memo']).lower() if pd.notna(row['Memo']) else ''
            
            # Simple contains check
            if description in payee:
                return {
                    'id': str(row.name),
                    'date': row['Date'],
                    'payee_name': row['Payee'],
                    'category_name': row['Category'],
                    'memo': memo,
                    'amount': row['Amount']
                }
        return None

    def update_transaction(self, transaction_id: str, category_id: str) -> Dict:
        """Update a transaction's category"""
        # Find category name from ID
        category_name = self.budget_data.loc[int(category_id), 'Category']
        
        # Update transaction in dataframe
        self.transactions.loc[int(transaction_id), 'Category'] = category_name
        
        # Return updated transaction
        row = self.transactions.loc[int(transaction_id)]
        return {
            'id': transaction_id,
            'date': row['Date'],
            'payee_name': row['Payee'],
            'category_name': category_name,
            'memo': row['Memo'] if pd.notna(row['Memo']) else '',
            'amount': int(row['Amount'] * 1000)
        }

    @staticmethod
    def milliunits_to_dollars(milliunits: int) -> float:
        """Convert milliunits to dollars"""
        return milliunits / 1000.0

def main():
    # Set up logging
    logger = setup_logger('cli_chat')
    logger.info("Starting YNAB CLI Chat")
    
    # Initialize clients
    ynab_client = YNABTestClient()
    chat_handler = ChatHandler(
        openai_client=os.getenv('OPENAI_API_KEY')
    )
    
    print("\nYNAB AI Assistant CLI 💰")
    print("Chat with your budget! Type 'quit' to exit.\n")
    
    while True:
        # Get user input
        prompt = input("\nYou: ").strip()
        if prompt.lower() == 'quit':
            break
            
        try:
            # Gather context
            context = {}
            
            # Get categories
            categories = ynab_client.get_categories()
            if categories:
                # Summarize by category group
                group_summary = []
                category_summary = []
                
                for group in categories:
                    group_total_budgeted = 0
                    group_total_activity = 0
                    group_categories = []
                    
                    for cat in group['categories']:
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
            recent_txns = ynab_client.get_transactions(since_date)
            
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
            
            # Check if this is a categorization request first
            if any(keyword in prompt.lower() for keyword in ['categorize', 'category', 'move to']):
                try:
                    # First, let OpenAI handle just the categorization task
                    categorization_prompt = f"""
                    You are a transaction categorization assistant. Extract ONLY the transaction and category from this request.

                    User request: "{prompt}"

                    Rules:
                    1. Return ONLY the transaction name and desired category in this format: payee|||category
                    2. Do not add any other text or explanation
                    3. Use the exact transaction name from the request
                    4. Use the exact category name from the request
                    
                    Example input: "Please categorize my Amazon purchase as Shopping"
                    Example output: Amazon|||Shopping
                    """
                    
                    categorization_response = chat_handler.get_response(categorization_prompt, {})
                    if '|||' in categorization_response:
                        payee, category = categorization_response.split('|||')
                        payee = payee.strip()
                        category = category.strip()
                        
                        # Find the transaction
                        transaction = ynab_client.find_transaction_by_description(payee)
                        if transaction:
                            # Find the category
                            category_match = ynab_client.find_category_by_name(category)
                            if category_match:
                                # Update transaction
                                updated = ynab_client.update_transaction(
                                    transaction_id=transaction['id'],
                                    category_id=category_match['id']
                                )
                                print(f"\nUpdated! Transaction '{updated['payee_name']}' is now in category '{category_match['name']}' 🎯")
                                
                                # Now get a friendly response about the update
                                update_prompt = f"""
                                The user asked to categorize a transaction, and I've done that successfully.
                                Transaction: {updated['payee_name']}
                                New Category: {category_match['name']}
                                
                                Give a short, friendly response focusing ONLY on the categorization (don't mention budget overview or other categories).
                                """
                                response = chat_handler.get_response(update_prompt, {})
                                print(f"\nAssistant: {response}")
                            else:
                                print(f"\nI found the transaction for {transaction['payee_name']}, but couldn't find the category '{category}'. Available categories are:")
                                print(context.get('categories', 'No categories available'))
                        else:
                            print(f"\nI couldn't find a transaction matching '{payee}'. Could you be more specific?")
                    else:
                        print("\nI didn't understand which transaction you want to categorize. Could you try rephrasing it?")
                        
                except Exception as e:
                    logger.error(f"Error processing categorization request: {str(e)}")
                    print("\nSorry, I had trouble with that categorization. Could you try rephrasing it?")
            else:
                # Handle regular chat about budget
                chat_prompt = f"""
                You are a friendly budget assistant. The user has asked: "{prompt}"

                Here's their recent budget information:
                {context.get('recent_transactions', '')}
                
                Category Details:
                {context.get('categories', '')}

                Give a focused response addressing their specific question. Don't try to cover everything - just answer what they asked about.
                """
                response = chat_handler.get_response(chat_prompt, {})
                print(f"\nAssistant: {response}")
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            print(f"\nOops! Something went wrong: {str(e)} 😅")
            
    print("\nThanks for chatting! See you next time! 👋")

if __name__ == "__main__":
    main() 