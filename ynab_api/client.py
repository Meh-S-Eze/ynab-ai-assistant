import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from utils.logger import setup_logger
import json

class YNABClient:
    def __init__(self, api_key: str):
        if not api_key:
            print("Oops! Need an API key!")
            raise ValueError("Need API key")
            
        self.api_key = api_key
        self.base_url = "https://api.ynab.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def get_transactions(self, budget_id: str) -> list:
        try:
            response = self.session.get(f"{self.base_url}/budgets/{budget_id}/transactions")
            response.raise_for_status()
            return response.json().get('data', {}).get('transactions', [])
        except Exception as e:
            print(f"Couldn't get transactions: {e}")
            return []

    def update_transaction(self, budget_id: str, transaction_id: str, 
                         category_id: str = None, memo: str = None):
        try:
            data = {"transaction": {}}
            if category_id:
                data["transaction"]["category_id"] = category_id
            if memo:
                data["transaction"]["memo"] = memo

            response = self.session.put(
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                json=data
            )
            response.raise_for_status()
            return response.json().get('data', {}).get('transaction')
        except Exception as e:
            print(f"Couldn't update transaction: {e}")
            return None

    def _test_connection(self):
        """Test the API connection"""
        try:
            self.logger.debug("Testing YNAB API connection")
            response = self.session.get(f"{self.base_url}/user")
            response.raise_for_status()
            self.logger.debug("YNAB API connection test successful")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"YNAB API connection test failed: {str(e)}")
            if response := getattr(e, 'response', None):
                self.logger.error(f"Response status: {response.status_code}")
                self.logger.error(f"Response body: {response.text}")
            raise

    def _get(self, endpoint: str) -> Dict:
        """Make a GET request to the YNAB API"""
        self.logger.debug(f"Making GET request to endpoint: {endpoint}")
        try:
            response = self.session.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            data = response.json()
            if 'data' not in data:
                self.logger.error(f"Unexpected API response format: {json.dumps(data, indent=2)}")
                raise ValueError("Unexpected API response format")
            return data.get('data', {})
        except requests.exceptions.RequestException as e:
            self.logger.error(f"YNAB API request failed: {str(e)}")
            if response := getattr(e, 'response', None):
                self.logger.error(f"Response status: {response.status_code}")
                self.logger.error(f"Response body: {response.text}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse API response: {str(e)}")
            self.logger.error(f"Raw response: {response.text}")
            raise

    def get_budgets(self) -> List[Dict]:
        """Get all budgets"""
        self.logger.info("Fetching all budgets")
        try:
            response = self._get("/budgets")
            if 'budgets' not in response:
                self.logger.error(f"No budgets found in response: {json.dumps(response, indent=2)}")
                return []
                
            budgets = response['budgets']
            self.logger.debug(f"Found {len(budgets)} budgets")
            for budget in budgets:
                self.logger.debug(f"Budget: {budget.get('name', 'Unknown')} (ID: {budget.get('id', 'Unknown')})")
            return budgets
        except Exception as e:
            self.logger.error(f"Failed to fetch budgets: {str(e)}")
            raise

    def get_categories(self, budget_id: Optional[str] = None) -> List[Dict]:
        """Get all categories for a budget"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
            
        self.logger.info(f"Fetching categories for budget: {budget_id}")
        try:
            response = self._get(f"/budgets/{budget_id}/categories")
            if 'category_groups' not in response:
                self.logger.error(f"No categories found in response: {json.dumps(response, indent=2)}")
                return []
                
            categories = response['category_groups']
            self.logger.debug(f"Found {len(categories)} category groups")
            return categories
        except Exception as e:
            self.logger.error(f"Failed to fetch categories: {str(e)}")
            raise

    def get_transactions(self, budget_id: Optional[str] = None, 
                        since_date: Optional[str] = None) -> List[Dict]:
        """Get transactions for a budget"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
        
        self.logger.info(f"Fetching transactions for budget: {budget_id}")
        endpoint = f"/budgets/{budget_id}/transactions"
        if since_date:
            endpoint += f"?since_date={since_date}"
            self.logger.debug(f"Filtering transactions since: {since_date}")
            
        try:
            response = self._get(endpoint)
            if 'transactions' not in response:
                self.logger.error(f"No transactions found in response: {json.dumps(response, indent=2)}")
                return []
                
            transactions = response['transactions']
            self.logger.debug(f"Found {len(transactions)} transactions")
            return transactions
        except Exception as e:
            self.logger.error(f"Failed to fetch transactions: {str(e)}")
            raise

    class TransactionContext:
        """Context manager for atomic YNAB operations"""
        def __init__(self, client, budget_id: str):
            self.client = client
            self.budget_id = budget_id
            self.original_state = None
            self.transaction_id = None
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None and self.original_state and self.transaction_id:
                # Rollback on error
                try:
                    self.client.session.put(
                        f"{self.client.base_url}/budgets/{self.budget_id}/transactions/{self.transaction_id}",
                        json={"transaction": self.original_state}
                    )
                except Exception as e:
                    self.client.logger.error(f"Failed to rollback transaction: {str(e)}")

    def update_transaction(self, budget_id: Optional[str] = None,
                          transaction_id: str = None,
                          category_id: Optional[str] = None,
                          memo: Optional[str] = None) -> Dict:
        """Update a transaction atomically"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
            
        if not transaction_id:
            self.logger.error("Transaction ID is required")
            raise ValueError("Transaction ID is required")
            
        self.logger.info(f"Updating transaction {transaction_id} in budget: {budget_id}")
        
        with self.TransactionContext(self, budget_id) as tx:
            try:
                # Get current state
                response = self.session.get(
                    f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}"
                )
                response.raise_for_status()
                current_state = response.json().get('data', {}).get('transaction', {})
                
                # Store original state for potential rollback
                tx.original_state = current_state
                tx.transaction_id = transaction_id
                
                # Build update data
                update_data = {"transaction": current_state.copy()}
                if category_id is not None:
                    update_data["transaction"]["category_id"] = category_id
                if memo is not None:
                    update_data["transaction"]["memo"] = memo
                    
                # Perform update
                response = self.session.put(
                    f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                    json=update_data
                )
                response.raise_for_status()
                data = response.json().get('data', {})
                
                if 'transaction' not in data:
                    self.logger.error(f"No transaction in response: {json.dumps(data, indent=2)}")
                    raise ValueError("Unexpected API response format")
                    
                updated_transaction = data['transaction']
                self.logger.debug(f"Successfully updated transaction: {transaction_id}")
                return updated_transaction
                
            except Exception as e:
                self.logger.error(f"Failed to update transaction: {str(e)}")
                raise
            
    def find_category_by_name(self, name: str, budget_id: Optional[str] = None) -> Optional[Dict]:
        """Find a category by name (case-insensitive partial match)"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
            
        self.logger.debug(f"Looking for category matching: {name}")
        categories = self.get_categories(budget_id)
        name = name.lower()
        
        for group in categories:
            if group['hidden'] or group['deleted']:
                continue
            for category in group['categories']:
                if category['hidden'] or category['deleted']:
                    continue
                if name in category['name'].lower():
                    self.logger.debug(f"Found matching category: {category['name']}")
                    return category
                    
        self.logger.debug(f"No category found matching: {name}")
        return None

    def find_transaction_by_description(self, description: str, 
                                      budget_id: Optional[str] = None,
                                      days_back: int = 30) -> Optional[Dict]:
        """Find a transaction by description (case-insensitive partial match)"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
            
        self.logger.debug(f"Looking for transaction matching: {description}")
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        transactions = self.get_transactions(budget_id, since_date)
        description = description.lower()
        
        for transaction in transactions:
            payee_name = transaction.get('payee_name', '').lower()
            memo = transaction.get('memo', '').lower()
            
            if description in payee_name or description in memo:
                self.logger.debug(f"Found matching transaction: {transaction.get('payee_name')}")
                return transaction
                
        self.logger.debug(f"No transaction found matching: {description}")
        return None

    @staticmethod
    def milliunits_to_dollars(milliunits: int) -> float:
        """Convert milliunits to dollars"""
        return milliunits / 1000.0

    def get_budget_months(self, budget_id: Optional[str] = None) -> List[Dict]:
        """Get list of available budget months"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
            
        self.logger.info(f"Fetching available months for budget: {budget_id}")
        try:
            response = self._get(f"/budgets/{budget_id}/months")
            if 'months' not in response:
                self.logger.error(f"No months found in response: {json.dumps(response, indent=2)}")
                return []
                
            months = response['months']
            self.logger.debug(f"Found {len(months)} budget months")
            return months
        except Exception as e:
            self.logger.error(f"Failed to fetch budget months: {str(e)}")
            return []
            
    def get_month_summary(self, budget_id: Optional[str] = None) -> Dict:
        """Get most recent month's budget summary"""
        budget_id = budget_id or self.budget_id
        if not budget_id:
            self.logger.error("Budget ID is required but not provided")
            raise ValueError("Budget ID is required")
            
        # Get available months
        months = self.get_budget_months(budget_id)
        if not months:
            self.logger.error("No budget months available")
            return {}
            
        # Sort by date and get most recent
        months.sort(key=lambda x: x['month'], reverse=True)
        latest_month = months[0]
        month_date = latest_month['month']
        
        self.logger.info(f"Using most recent budget month: {month_date}")
        return latest_month 