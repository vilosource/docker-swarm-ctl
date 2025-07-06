import logging
import sys
import os
import socket

# Get container hostname to detect self-monitoring
CONTAINER_HOSTNAME = socket.gethostname()

class SelfMonitoringFilter(logging.Filter):
    """Filter out logs that would cause feedback loops when monitoring our own container."""
    
    def __init__(self):
        super().__init__()
        # Check if we're running in a container that looks like our backend
        self.is_backend_container = any(pattern in CONTAINER_HOSTNAME.lower() 
                                      for pattern in ['backend', 'api', 'fastapi'])
    
    def filter(self, record):
        # If we're not in a backend container, allow all logs
        if not self.is_backend_container:
            return True
        
        # Filter out uvicorn access logs that could cause loops
        if record.name == "uvicorn.access":
            # Check if this is a request to our own container endpoints
            message = record.getMessage()
            if any(endpoint in message for endpoint in [
                "/api/v1/containers/",
                "/ws/containers/",
                "/inspect",
                "/logs",
                "/exec",
                "/stats"
            ]):
                return False
        
        # Filter out our own WebSocket connection logs (already handled in the code)
        if "WebSocket connected:" in record.getMessage() or "WebSocket disconnected:" in record.getMessage():
            return False
        
        # Filter out WebSocket error logs to prevent feedback loops
        if record.name == "app.api.v1.websocket.base" and "Error sending WebSocket message" in record.getMessage():
            return False
            
        # Allow all other logs
        return True


def setup_logging():
    """Configure logging with self-monitoring filter."""
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Add self-monitoring filter to prevent loops
    console_handler.addFilter(SelfMonitoringFilter())
    
    # Clear existing handlers and add our configured handler
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # Configure uvicorn loggers specifically
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    
    # Apply filter to uvicorn loggers as well
    for handler in uvicorn_logger.handlers:
        handler.addFilter(SelfMonitoringFilter())
    
    for handler in uvicorn_access_logger.handlers:
        handler.addFilter(SelfMonitoringFilter())
    
    return root_logger