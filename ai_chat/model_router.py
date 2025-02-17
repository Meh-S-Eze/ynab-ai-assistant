from typing import Dict, Optional, List
import yaml
import logging
from pydantic import BaseModel, Field
from contextlib import contextmanager
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

class ModelRuntimeError(Exception):
    """Raised when model execution fails"""
    pass

class TokenLimitError(Exception):
    """Raised when input exceeds token limit"""
    pass

class TimeoutError(Exception):
    """Raised when model execution times out"""
    pass

class ServiceDegradationError(Exception):
    """Raised when service quality is degraded"""
    pass

class AIResponseSchema(BaseModel):
    """Schema for validated AI responses"""
    content: str
    confidence: float = Field(..., gt=0, lt=1)
    error: Optional[str] = None

class CircuitBreaker:
    """Implements circuit breaker pattern for model calls"""
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"
        
    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = "open"
            self.last_failure_time = time.time()
            
    def record_success(self):
        """Record a success and reset failure count"""
        self.failures = 0
        self.state = "closed"
        
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True
            
        if time.time() - self.last_failure_time >= self.recovery_timeout:
            self.state = "half-open"
            return True
            
        return False

class ModelWrapper:
    """Wraps a model with resource management"""
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.model = None
        self.tokenizer = None
        
    @contextmanager
    def load(self):
        """Context manager for model loading and cleanup"""
        try:
            if not self.model:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.name,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                self.tokenizer = AutoTokenizer.from_pretrained(self.name)
            yield self
        finally:
            # Resource cleanup happens on context exit
            torch.cuda.empty_cache()
            
    def generate(self, prompt: str) -> str:
        """Generate response from the model"""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                pad_token_id=self.tokenizer.eos_token_id
            )
            
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

class ModelRouter:
    """Routes requests to appropriate models with fallback"""
    def __init__(self, config_path: str):
        self.logger = logging.getLogger('model_router')
        
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Initialize models
        self.primary = ModelWrapper(
            self.config["models"]["primary"]["name"],
            self.config["models"]["primary"]
        )
        
        self.fallbacks = [
            ModelWrapper(m["name"], m)
            for m in self.config["models"]["fallback"]
        ]
        
        # Initialize circuit breaker
        self.circuit = CircuitBreaker(
            self.config["circuit_breaker"]["failure_threshold"],
            self.config["circuit_breaker"]["recovery_timeout"]
        )
        
    def query(self, prompt: str, retries: int = 3) -> AIResponseSchema:
        """Query models with fallback and validation"""
        if not self.circuit.can_execute():
            raise ServiceDegradationError("Service temporarily degraded")
            
        errors = []
        
        # Try primary model
        try:
            with self.primary.load() as model:
                response = model.generate(prompt)
                self.circuit.record_success()
                return self._validate_response(response)
        except Exception as e:
            self.logger.error(f"Primary model failed: {str(e)}")
            self.circuit.record_failure()
            errors.append(f"Primary - {str(e)}")
            
        # Try fallbacks
        for fallback in self.fallbacks:
            try:
                with fallback.load() as model:
                    response = model.generate(prompt)
                    self.circuit.record_success()
                    return self._validate_response(response)
            except Exception as e:
                self.logger.error(f"Fallback {fallback.name} failed: {str(e)}")
                errors.append(f"Fallback {fallback.name} - {str(e)}")
                
        raise ModelRuntimeError(f"All models failed: {'; '.join(errors)}")
        
    def _validate_response(self, response: str) -> AIResponseSchema:
        """Validate model response against schema"""
        try:
            # TODO: Implement proper response parsing
            return AIResponseSchema(
                content=response,
                confidence=0.8,  # TODO: Implement proper confidence scoring
                error=None
            )
        except Exception as e:
            self.logger.error(f"Response validation failed: {str(e)}")
            raise 