import os
import yaml
from typing import Dict, List, Optional
import emoji
from utils.logger import setup_logger
from .model_router import ModelRouter, ServiceDegradationError, ModelRuntimeError

class ChatHandler:
    def __init__(self, personas_file: str = "config/personas.yaml"):
        self.logger = setup_logger('chat_handler')
        self.logger.info("Initializing ChatHandler")
        
        try:
            # Load personas config
            with open(personas_file, 'r') as f:
                config = yaml.safe_load(f)
            self.personas = config['personas']
            self.logger.debug(f"Loaded {len(self.personas)} personas from config")
            
            # Initialize model router
            self.model_router = ModelRouter("model_configs/production.yaml")
            self.logger.info("Initialized model router")
            
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
            
            # Build the prompt
            prompt = self._build_prompt(persona, user_message, context)
            
            try:
                # Get response from model router
                response = self.model_router.query(prompt)
                self.logger.debug("Successfully got response from model")
                return self.ensure_emoji(response.content)
            except ServiceDegradationError:
                self.logger.warning("Service degraded, using fallback response")
                return self._get_fallback_response()
            except ModelRuntimeError as e:
                self.logger.error(f"Model error: {str(e)}")
                return "I'm having trouble thinking right now. Could you try again in a moment? 😅"
                
        except Exception as e:
            self.logger.error(f"Failed to get AI response: {str(e)}")
            raise

    def _build_prompt(self, persona: Dict, message: str, context: Optional[Dict] = None) -> str:
        """Build a prompt for the model"""
        parts = [
            f"You are a {persona['name']}. {persona['prompt']}",
        ]
        
        if context:
            context_msg = self._format_context(context)
            parts.append(f"\nContext:\n{context_msg}")
        
        parts.append(f"\nUser: {message}\nAssistant:")
        return "\n".join(parts)

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

    def _get_fallback_response(self) -> str:
        """Get a fallback response when the model service is degraded"""
        fallbacks = [
            "I'm a bit overwhelmed right now, but I'm still here to help! Could you try that again? 😊",
            "Things are a bit busy, but I want to help. Mind repeating that? 🌟",
            "I need a quick moment to catch up. Could you ask that again? 💭"
        ]
        return fallbacks[0]  # Always use the first one for consistency

    def ensure_emoji(self, response: str) -> str:
        """Ensure response has at least one emoji"""
        if not any(char in emoji.EMOJI_DATA for char in response):
            self.logger.debug("No emoji found in response, adding one")
            return response + " 😊"
        return response 