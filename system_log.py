import logging

# Basic configuration without StreamHandler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log')  # Only log to file
    ]
)

# Create a logger
logger = logging.getLogger('WTM')

# Set the logging level for the logger
logger.setLevel(logging.DEBUG)

# Create a handler (console in this case)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG) 

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)