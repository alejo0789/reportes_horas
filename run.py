import os
import uvicorn
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server_entrypoint")

if __name__ == "__main__":
    logger.info("Starting Sales per Hour Dashboard Server...")
    
    # Retrieve configuration from environment or use production-ready defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8032"))
    reload = os.getenv("RELOAD", "true" if os.getenv("ENVIRONMENT") == "development" else "false")
    
    logger.info(f"Config: Host={host}, Port={port}, Reload={reload}")
    
    # Run the uvicorn server
    # Will serve API routes at /api/* and frontend static files at root /
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)
