import os
import yaml
from typing import Dict, List, Optional
import openai
import emoji
from utils.logger import setup_logger

class ChatHandler:
    def __init__(self, openai_client: str, personas_file: str = "config/personas.yaml"):
        self.logger = setup_logger('chat_handler')
        self.logger.info("Initializing ChatHandler")
        
        try:
            # Set OpenAI API key
            openai.api_key = openai_client
            self.logger.debug("OpenAI API key set")
            
            with open(personas_file, 'r') as f:
                config = yaml.safe_load(f)
            self.personas = config['personas']
            self.logger.debug(f"Loaded {len(self.personas)} personas from config")
            
            self.current_persona = "cheerleader"  # default persona
            self.logger.info("ChatHandler initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChatHandler: {str(e)}")
            raise

    def switch_persona(self, persona_name: str) -> None:
        """Switch to a different persona"""
        self.logger.info(f"Switching to persona: {persona_name}")
        if persona_name not in self.personas:
            self.logger.error(f"Unknown persona requested: {persona_name}")
            raise ValueError(f"Unknown persona: {persona_name}")
        self.current_persona = persona_name
        self.logger.debug("Persona switched successfully")

    def get_response(self, user_message: str, 
                    context: Optional[Dict] = None) -> str:
        """Get AI response for user message"""
        self.logger.info("Getting AI response")
        try:
            persona = self.personas[self.current_persona]
            self.logger.debug(f"Using persona: {persona['name']}")
            
            # Build the message list
            messages = [
                {"role": "system", "content": persona['prompt']},
            ]
            
            # Add context if provided
            if context:
                context_msg = self._format_context(context)
                messages.append({"role": "system", "content": context_msg})
                self.logger.debug("Added context to messages")
            
            # Add user message
            messages.append({"role": "user", "content": user_message})
            
            self.logger.debug("Making API call to OpenAI")
            # Get completion from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=persona['temperature'],
                max_tokens=150
            )
            
            self.logger.debug("Successfully got response from OpenAI")
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Failed to get AI response: {str(e)}")
            raise

    def _format_context(self, context: Dict) -> str:
        """Format context data for the AI"""
        self.logger.debug("Formatting context data")
        context_parts = []
        
        # Budget Overview
        if 'budget_name' in context:
            context_parts.append(f"Current Budget: {context['budget_name']}")
        
        if 'category_status' in context:
            context_parts.append("\nBudget Status:")
            context_parts.append(context['category_status'])
        
        # Category Groups and Details
        if 'category_groups' in context:
            context_parts.append("\nCategory Group Summary:")
            context_parts.append(context['category_groups'])
            
        if 'categories' in context:
            context_parts.append("\nDetailed Category Status:")
            context_parts.append(context['categories'])
        
        # Recent Financial Activity
        if 'recent_transactions' in context:
            context_parts.append("\nRecent Financial Activity:")
            context_parts.append(context['recent_transactions'])
        
        if 'transaction_details' in context:
            context_parts.append("\nLatest Transactions:")
            context_parts.append(context['transaction_details'])
        
        formatted = "\n".join(context_parts)
        self.logger.debug(f"Formatted context: {formatted}")
        return formatted

    def ensure_emoji(self, response: str) -> str:
        """Ensure response has at least one emoji"""
        if not any(char in emoji.EMOJI_DATA for char in response):
            self.logger.debug("No emoji found in response, adding one")
            return response + " 😊"
        return response 