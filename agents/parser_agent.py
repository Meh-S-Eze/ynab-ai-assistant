from typing import Dict, Optional
import re
import logging

class ParserAgent:
    """
    Handles parsing and understanding user requests.
    Extracts key information like transaction details and categories.
    """
    def __init__(self):
        self.logger = logging.getLogger('parser_agent')
        
    def parse_request(self, user_input: str) -> Dict:
        """Parse user input and identify request type and details."""
        self.logger.debug(f"Parsing request: {user_input}")
        
        # Check for categorization request
        if self._is_categorization_request(user_input):
            return self._parse_categorization(user_input)
            
        # Check for spending query
        if self._is_spending_query(user_input):
            return self._parse_spending_query(user_input)
            
        # Default to general chat
        return {
            'type': 'chat',
            'message': user_input
        }
        
    def _is_categorization_request(self, text: str) -> bool:
        """Check if this is a categorization request."""
        categorization_patterns = [
            r'categori[sz]e',
            r'set.*category',
            r'mark.*as',
            r'should be',
            r'put.*in'
        ]
        
        text = text.lower()
        return any(re.search(pattern, text) for pattern in categorization_patterns)
        
    def _parse_categorization(self, text: str) -> Dict:
        """Extract transaction and category from categorization request."""
        # Look for quoted transaction name first
        transaction = None
        quoted = re.findall(r'[\'"]([^\'"]*)[\'"]', text)
        if quoted:
            transaction = quoted[0]
        else:
            # Try to find transaction between common phrases
            patterns = [
                r'categori[sz]e\s+([^\.]+?)\s+(?:as|to|in|under)',
                r'transaction (?:for |of |)([^\.]+?)\s+(?:as|to|in|under)',
                r'purchase (?:for |of |)([^\.]+?)\s+(?:as|to|in|under)',
                r'payment (?:for |to |)([^\.]+?)\s+(?:as|to|in|under)',
                r'charge (?:for |from |)([^\.]+?)\s+(?:as|to|in|under)'
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    transaction = match.group(1).strip()
                    break

        # Look for category after common phrases
        category = None
        category_patterns = [
            r'(?:as|to|in|under|in the|to the|under the)\s+([^\.]+?)(?:\s+category|\s+budget|\s+group|$)',
            r'should be\s+([^\.]+)',
            r'mark (?:as|it as)\s+([^\.]+)'
        ]
        
        for pattern in category_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                category = match.group(1).strip()
                break
                
        if not transaction or not category:
            self.logger.warning(f"Could not parse categorization request - transaction: {transaction}, category: {category}")
            return {
                'type': 'error',
                'message': "I couldn't quite catch which transaction and category you meant. Could you try rephrasing that?"
            }
            
        return {
            'type': 'categorize',
            'transaction': transaction,
            'category': category
        }
        
    def _is_spending_query(self, text: str) -> bool:
        """Check if this is a spending query."""
        spending_patterns = [
            r'how much',
            r'spent',
            r'spending',
            r'expenses',
            r'balance',
            r'budget'
        ]
        
        text = text.lower()
        return any(re.search(pattern, text) for pattern in spending_patterns)
        
    def _parse_spending_query(self, text: str) -> Dict:
        """Extract category and time period from spending query."""
        # Look for category
        category_patterns = [
            r'(?:on|in|for) ([^\.]*?) (?:spending|expenses|budget)',
            r'spent (?:on|in|for) ([^\.]*)'
        ]
        
        category = None
        for pattern in category_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                category = match.group(1).strip()
                break
                
        # Look for time period
        time_patterns = {
            'this month': 30,
            'this week': 7,
            'today': 1,
            'year': 365,
            'month': 30,
            'week': 7,
            'day': 1
        }
        
        days = 30  # Default to this month
        text = text.lower()
        for period, period_days in time_patterns.items():
            if period in text:
                days = period_days
                break
                
        return {
            'type': 'spending',
            'category': category,
            'days': days
        } 