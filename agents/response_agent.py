from typing import Dict, Optional
import random
import logging

class ResponseAgent:
    """
    Handles generating natural, friendly responses to user requests.
    Makes budget talk fun! 😊
    """
    def __init__(self):
        self.logger = logging.getLogger('response_agent')
        
        # Fun emoji for different response types
        self.category_emoji = ['✅', '📝', '🏷️', '🎯']
        self.spending_emoji = ['💰', '📊', '💵', '🧮']
        self.error_emoji = ['😅', '🤔', '😬']
        
        # Response templates
        self.categorization_templates = [
            "Got it! I've marked {transaction} as {category}",
            "All set! {transaction} is now in {category}",
            "Updated! {transaction} has been categorized as {category}",
            "Done! I've put {transaction} under {category}"
        ]
        
        self.spending_templates = [
            "You've spent ${amount:.2f} on {category} in the last {days} days",
            "Your {category} spending is ${amount:.2f} over the past {days} days",
            "Looking at {category}, you've spent ${amount:.2f} in {days} days",
            "For {category}, you're at ${amount:.2f} in spending over {days} days"
        ]
        
        self.error_templates = [
            "Hmm, I'm not quite sure what you mean",
            "I didn't catch that, could you rephrase it?",
            "Sorry, I'm having trouble understanding that request",
            "I'm a bit confused - could you try saying that another way?"
        ]
        
    def get_response(self, result: Dict) -> str:
        """Generate a friendly response based on the result type."""
        self.logger.debug(f"Generating response for: {result}")
        
        if result['type'] == 'categorize':
            return self._get_categorization_response(result)
        elif result['type'] == 'spending':
            return self._get_spending_response(result)
        elif result['type'] == 'error':
            return self._get_error_response(result)
        else:
            return result.get('message', 'Not sure how to respond to that!')
            
    def _get_categorization_response(self, result: Dict) -> str:
        """Generate response for category updates."""
        template = random.choice(self.categorization_templates)
        emoji = random.choice(self.category_emoji)
        
        response = template.format(
            transaction=result['transaction'],
            category=result['new_category']
        )
        
        # Add helpful context about the amount
        if 'amount' in result:
            response += f" (${abs(result['amount']):.2f})"
            
        return f"{emoji} {response}"
        
    def _get_spending_response(self, result: Dict) -> str:
        """Generate response for spending queries."""
        template = random.choice(self.spending_templates)
        emoji = random.choice(self.spending_emoji)
        
        # Format time period nicely
        days = result.get('days', 30)  # Default to this month
        if days == 30:
            period = "this month"
        elif days == 7:
            period = "this week"
        elif days == 1:
            period = "today"
        else:
            period = f"the last {days} days"
            
        response = template.format(
            category=result.get('category', 'Unknown'),
            amount=result.get('amount', 0.0),
            days=period
        )
        
        # Add helpful context about budget if available
        if 'budget' in result:
            budget = result['budget']
            remaining = budget - result.get('amount', 0.0)
            if remaining > 0:
                response += f"\nYou still have ${remaining:.2f} left in your budget!"
            elif remaining < 0:
                response += f"\nLooks like you're ${abs(remaining):.2f} over budget"
            else:
                response += "\nThat's exactly your budget amount!"
                
        return f"{emoji} {response}"
        
    def _get_error_response(self, result: Dict) -> str:
        """Generate friendly error response."""
        template = random.choice(self.error_templates)
        emoji = random.choice(self.error_emoji)
        
        response = result.get('message', template)
        return f"{emoji} {response}" 