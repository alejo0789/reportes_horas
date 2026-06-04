import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server_entrypoint")

if __name__ == "__main__":
    logger.info("Starting Sales per Hour Dashboard Server...")
    # Run the uvicorn development server
    # Will serve API routes at /api/* and frontend static files at root /
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, reload=True)
