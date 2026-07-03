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
    # Nota: os.getenv devuelve string; un string no vacio como "false" es truthy,
    # por eso hay que parsear el booleano de forma explicita.
    reload_env = os.getenv("RELOAD", "true" if os.getenv("ENVIRONMENT") == "development" else "false")
    reload = reload_env.strip().lower() in ("1", "true", "yes", "on")

    logger.info(f"Config: Host={host}, Port={port}, Reload={reload}")

    # Run the uvicorn server
    # Will serve API routes at /api/* and frontend static files at root /
    # El reloader solo debe vigilar codigo fuente (backend/*.py); nunca los datos
    # (uploads/cache.db y sus WAL/journal), que se escriben casi en tiempo real y
    # dispararian un reinicio del server -> peticiones caidas ("Failed to fetch").
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["backend"],
        reload_includes=["*.py"],
        reload_excludes=[
            "uploads/*",
            "*.db",
            "*.db-journal",
            "*.db-wal",
            "*.db-shm",
            "*.sqlite*",
        ],
    )
