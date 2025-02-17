from typing import Dict, Optional, List
import yaml
import logging
import os
from pydantic import BaseModel, Field
from contextlib import contextmanager
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ModelRuntimeError(Exception):
    """Raised when model execution fails"""
    pass

class TokenLimitError(Exception):
    """Raised when token limit is exceeded"""
    pass

class TimeoutError(Exception):
    """Raised when model request times out"""
    pass

class ServiceDegradationError(Exception):
    """Raised when service is degraded and needs attention"""
    pass

class AIResponseSchema(BaseModel):
    """Schema for validating AI responses"""
    content: str
    confidence: float = Field(..., gt=0, lt=1)
    error: Optional[str] = None

class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
        self.logger = logging.getLogger('circuit_breaker')

    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.is_open = True
            self.logger.warning(f"Circuit breaker opened after {self.failures} failures")

    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if not self.is_open:
            return True

        if self.last_failure_time and \
           datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
            self.reset()
            return True

        return False

    def reset(self):
        """Reset the circuit breaker state"""
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
        self.logger.info("Circuit breaker reset")

class ModelRouter:
    """Routes requests to appropriate AI models with fallback handling"""
    
    def __init__(self, config_path: str):
        self.logger = logging.getLogger('model_router')
        
        # Get GitHub token
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
            
        self.config = self._load_config(config_path)
        
        # Initialize circuit breaker
        cb_config = self.config['circuit_breaker']
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config['failure_threshold'],
            recovery_timeout=cb_config['recovery_timeout']
        )
        
        # Set up model clients
        self.primary_model = self._setup_model(self.config['models']['primary'])
        self.fallback_models = [
            self._setup_model(model_config) 
            for model_config in self.config['models']['fallback']
        ]

    def _load_config(self, config_path: str) -> Dict:
        """Load model configuration from YAML"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            raise

    def _setup_model(self, model_config: Dict):
        """Set up a model client based on configuration"""
        # Add GitHub token to config
        model_config['auth'] = {
            'token': self.github_token,
            'type': 'github'
        }
        return model_config

    @contextmanager
    def _model_context(self):
        """Context manager for model operations with circuit breaker"""
        if not self.circuit_breaker.can_execute():
            raise ServiceDegradationError("Circuit breaker is open")
        
        try:
            yield
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise

    def get_completion(self, prompt: str, **kwargs) -> AIResponseSchema:
        """Get completion from model with fallback handling"""
        with self._model_context():
            # Try primary model first
            try:
                response = self._try_model(self.primary_model, prompt, **kwargs)
                self.circuit_breaker.reset()  # Success, reset circuit breaker
                return response
            except Exception as e:
                self.logger.warning(f"Primary model failed: {str(e)}")
                
                # Try fallback models in order
                for fallback_model in self.fallback_models:
                    try:
                        response = self._try_model(fallback_model, prompt, **kwargs)
                        self.logger.info(f"Fallback succeeded with model: {fallback_model['model']}")
                        return response
                    except Exception as fallback_e:
                        self.logger.warning(f"Fallback model failed: {str(fallback_e)}")
                        continue
                
                # All models failed
                raise ServiceDegradationError("All models failed to provide completion")

    def _try_model(self, model_config: Dict, prompt: str, **kwargs) -> AIResponseSchema:
        """Try to get completion from a specific model"""
        # Here we'd implement the actual model call
        # For now, we'll just simulate it
        try:
            # Simulate model call
            time.sleep(0.1)  # Simulate processing
            
            # Validate response
            response = AIResponseSchema(
                content="Simulated response",
                confidence=0.95,
                error=None
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Model error: {str(e)}")
            raise ModelRuntimeError(f"Failed to get completion: {str(e)}")

    def reset_circuit(self):
        """Reset the circuit breaker"""
        self.circuit_breaker.reset() 