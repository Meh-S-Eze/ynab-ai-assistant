import logging
import sys
from datetime import datetime
import os

def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with both file and console output"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Prevent duplicate handlers
    if not logger.handlers:
        # Create file handler
        today = datetime.now().strftime('%Y-%m-%d')
        fh = logging.FileHandler(f'logs/app_{today}.log')
        fh.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add formatter to handlers
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(fh)
        logger.addHandler(ch)
    
    return logger 