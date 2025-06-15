import logging
import os
from datetime import datetime

def setup_logging():
    """Configure centralized logging for the Risk Analytics application"""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create log filename with timestamp
    log_filename = os.path.join(log_dir, f"risk_analytics_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ],
        force=True  # Override any existing configuration
    )
    
    # Set specific log levels for different modules
    logging.getLogger('database').setLevel(logging.INFO)
    logging.getLogger('alphavantage_service').setLevel(logging.INFO)
    logging.getLogger('var_calculator').setLevel(logging.INFO)
    logging.getLogger('streamlit_app').setLevel(logging.INFO)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('streamlit').setLevel(logging.WARNING)
    
    root_logger = logging.getLogger()
    root_logger.info("=== Risk Analytics Application Started ===")
    root_logger.info(f"Logging configured - Log file: {log_filename}")
    
    return root_logger

def get_logger(name):
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)

# Performance tracking decorator
def log_performance(func):
    """Decorator to log function execution time"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()
        logger.debug(f"Starting {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"{func.__name__} completed successfully in {duration:.2f} seconds")
            return result
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {duration:.2f} seconds: {str(e)}")
            raise
    
    return wrapper

def log_api_call(endpoint, params, response_size=None):
    """Log API call details"""
    logger = logging.getLogger('api')
    logger.info(f"API Call - Endpoint: {endpoint}, Params: {params}")
    if response_size:
        logger.info(f"API Response - Size: {response_size} records")

def log_data_operation(operation, table, record_count=None):
    """Log database operations"""
    logger = logging.getLogger('database')
    if record_count:
        logger.info(f"Database {operation} - Table: {table}, Records: {record_count}")
    else:
        logger.info(f"Database {operation} - Table: {table}")

def log_calculation(calculation_type, input_size, result_keys):
    """Log calculation operations"""
    logger = logging.getLogger('calculations')
    logger.info(f"Calculation {calculation_type} - Input size: {input_size}, Results: {list(result_keys)}")