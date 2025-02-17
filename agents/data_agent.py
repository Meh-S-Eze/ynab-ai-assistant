from typing import Dict, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging

class DataOperationsAgent:
    """
    Handles all data operations and interactions with the YNAB data.
    Acts as the single source of truth for data modifications.
    """
    def __init__(self, data_dir: str = "test_data"):
        self.logger = logging.getLogger('data_agent')
        self.budget_file = f"{data_dir}/MVP AI AGENTS as of 2025-02-16 19-55 - Budget.csv"
        self.register_file = f"{data_dir}/MVP AI AGENTS as of 2025-02-16 19-55 - Register.csv"
        
        self._load_data()
        
    def _load_data(self):
        """Load and prepare the YNAB data."""
        self.logger.info("Loading YNAB data")
        
        # Load CSV files
        self.budget_data = pd.read_csv(self.budget_file)
        self.transactions = pd.read_csv(self.register_file)
        
        # Convert numeric columns
        self._convert_budget_columns()
        self._convert_transaction_columns()
        
        # Clean up categories
        self.budget_data['Category Group'] = self.budget_data['Category Group'].fillna('Uncategorized')
        self.budget_data['Category'] = self.budget_data['Category'].fillna('Uncategorized')
        
    def _convert_budget_columns(self):
        """Convert budget numeric columns to float."""
        budget_columns = ['Budgeted', 'Activity', 'Available']
        for col in budget_columns:
            if col in self.budget_data.columns:
                self.budget_data[col] = pd.to_numeric(
                    self.budget_data[col].str.replace('$', '').str.replace(',', ''), 
                    errors='coerce'
                ).fillna(0)
                
    def _convert_transaction_columns(self):
        """Convert transaction amounts to float and calculate net amount."""
        if 'Inflow' in self.transactions.columns and 'Outflow' in self.transactions.columns:
            for col in ['Inflow', 'Outflow']:
                self.transactions[col] = pd.to_numeric(
                    self.transactions[col].str.replace('$', '').str.replace(',', ''), 
                    errors='coerce'
                ).fillna(0)
            
            self.transactions['Amount'] = self.transactions['Inflow'] - self.transactions['Outflow']
            
    def find_transaction(self, description: str) -> Optional[Dict]:
        """Find a transaction by description."""
        self.logger.debug(f"Searching for transaction: {description}")
        
        description = description.lower()
        recent_txns = self.transactions[
            pd.to_datetime(self.transactions['Date']) >= pd.to_datetime(
                (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
        ]
        
        for _, row in recent_txns.iterrows():
            if description in str(row['Payee']).lower():
                return {
                    'id': str(row.name),
                    'date': row['Date'],
                    'payee_name': row['Payee'],
                    'category_name': row['Category'],
                    'amount': row['Amount']
                }
        return None
        
    def find_category(self, name: str) -> Optional[Dict]:
        """Find a category by name."""
        if not name:
            return None
            
        # Clean up the category name
        name = name.lower().strip()
        name = name.rstrip('?!.,')  # Remove trailing punctuation
            
        self.logger.debug(f"Searching for category: {name}")
        
        # Category name mappings
        category_map = {
            'medical': 'Health & Wellness',
            'health': 'Health & Wellness',
            'healthcare': 'Health & Wellness',
            'wellness': 'Health & Wellness',
            'doctor': 'Health & Wellness',
            'dental': 'Health & Wellness',
            'therapy': 'Health & Wellness'
        }
        
        if name in category_map:
            name = category_map[name].lower()
            
        for _, row in self.budget_data.iterrows():
            category = str(row['Category']).lower()
            if name in category or category in name:
                return {
                    'id': str(row.name),
                    'name': row['Category'],
                    'group': row['Category Group']
                }
        
        # If we didn't find an exact match, try partial matches
        for _, row in self.budget_data.iterrows():
            category = str(row['Category']).lower()
            words = set(name.split()) & set(category.split())
            if words:
                return {
                    'id': str(row.name),
                    'name': row['Category'],
                    'group': row['Category Group']
                }
                
        return None
        
    def update_category(self, transaction_name: str, category_name: str) -> Dict:
        """Update a transaction's category."""
        if not transaction_name or not category_name:
            raise ValueError("Transaction name and category are required")
            
        self.logger.info(f"Updating category for {transaction_name} to {category_name}")
        
        # Find transaction and category
        transaction = self.find_transaction(transaction_name)
        if not transaction:
            raise ValueError(f"I couldn't find a recent transaction matching '{transaction_name}'")
            
        category = self.find_category(category_name)
        if not category:
            raise ValueError(f"I couldn't find a category matching '{category_name}'")
            
        # Update the transaction
        tx_id = int(transaction['id'])
        self.transactions.loc[tx_id, 'Category'] = category['name']
        
        # Return updated transaction
        return {
            'transaction': transaction['payee_name'],
            'old_category': transaction['category_name'],
            'new_category': category['name'],
            'date': transaction['date'],
            'amount': transaction['amount']
        }
        
    def get_category_spending(self, category_name: str, days: int = 30) -> float:
        """Get total spending in a category."""
        if not category_name:
            return 0.0
            
        self.logger.debug(f"Getting spending for category: {category_name}")
        
        category = self.find_category(category_name)
        if not category:
            return 0.0
            
        recent_txns = self.transactions[
            pd.to_datetime(self.transactions['Date']) >= pd.to_datetime(
                (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            )
        ]
        
        category_txns = recent_txns[recent_txns['Category'] == category['name']]
        return abs(category_txns['Amount'].sum()) 