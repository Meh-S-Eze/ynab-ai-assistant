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
        
    def parse_request(self, text: str) -> dict:
        # Simple categorization check
        if "categorize" in text.lower() or "category" in text.lower():
            return self._parse_categorization(text)
        
        # Simple spending check    
        if "spent" in text.lower() or "spending" in text.lower():
            return self._parse_spending(text)
            
        return {"type": "chat", "message": text}

    def _parse_categorization(self, text: str) -> dict:
        # Look for text between quotes first
        transaction = None
        category = None
        
        # Simple quote check
        quotes = text.split('"')
        if len(quotes) > 1:
            transaction = quotes[1]
            
        # Look for category after "as" or "to"
        words = text.lower().split()
        for i, word in enumerate(words):
            if word in ["as", "to"] and i < len(words) - 1:
                category = words[i + 1]
                break

        if not transaction or not category:
            return {
                "type": "error",
                "message": "Could you rephrase that? Not sure what to categorize!"
            }

        return {
            "type": "categorize",
            "transaction": transaction,
            "category": category
        }

    def _parse_spending(self, text: str) -> dict:
        # Default to "this month"
        days = 30
        category = None

        # Super simple time period check
        if "week" in text:
            days = 7
        elif "year" in text:
            days = 365

        # Look for category after "on" or "in"
        words = text.lower().split()
        for i, word in enumerate(words):
            if word in ["on", "in"] and i < len(words) - 1:
                category = words[i + 1]
                break

        return {
            "type": "spending",
            "category": category,
            "days": days
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