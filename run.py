"""Run the FastAPI application."""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
