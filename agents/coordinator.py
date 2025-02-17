from typing import Dict, Optional
import logging
from .parser_agent import ParserAgent
from .data_agent import DataOperationsAgent
from .response_agent import ResponseAgent

class CoordinatorAgent:
    """
    The main coordinator that orchestrates the workflow between agents.
    Think of it as the friendly budget buddy in charge! 😊
    """
    def __init__(self, data_dir: str = "test_data"):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('coordinator')
        
        # Initialize our specialist agents
        self.parser = ParserAgent()
        self.data_ops = DataOperationsAgent(data_dir)
        self.responder = ResponseAgent()
        
    def handle_request(self, user_input: str) -> str:
        """
        Main entry point for handling user requests.
        Coordinates between agents to understand, process, and respond.
        """
        self.logger.info(f"Handling request: {user_input}")
        
        try:
            # Step 1: Parse the request
            parsed = self.parser.parse_request(user_input)
            self.logger.debug(f"Parsed request: {parsed}")
            
            # Step 2: Process based on request type
            if parsed['type'] == 'categorize':
                result = self._handle_categorization(parsed)
            elif parsed['type'] == 'spending':
                result = self._handle_spending_query(parsed)
            else:
                result = parsed  # Pass through chat/error messages
                
            # Step 3: Generate friendly response
            response = self.responder.get_response(result)
            self.logger.debug(f"Generated response: {response}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            return self.responder.get_response({
                'type': 'error',
                'message': str(e)
            })
            
    def _handle_categorization(self, parsed: Dict) -> Dict:
        """Handle transaction categorization request."""
        try:
            # Update the transaction category
            result = self.data_ops.update_category(
                parsed['transaction'],
                parsed['category']
            )
            
            # Add request type for response generation
            result['type'] = 'categorize'
            return result
            
        except ValueError as e:
            return {
                'type': 'error',
                'message': str(e)
            }
            
    def _handle_spending_query(self, parsed: Dict) -> Dict:
        """Handle spending/budget query."""
        try:
            # Get spending for the category
            amount = self.data_ops.get_category_spending(
                parsed['category'],
                parsed['days']
            )
            
            return {
                'type': 'spending',
                'category': parsed['category'],
                'amount': amount,
                'days': parsed['days']
            }
            
        except ValueError as e:
            return {
                'type': 'error',
                'message': str(e)
            } 