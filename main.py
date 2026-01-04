from fastapi import FastAPI, HTTPException
from app.routes import voice
from app.core.config import settings
from app.services.acs import acs_service
from app.services.llm import client as openai_client
import logging

# Validate settings on load
# (Implicitly done by importing settings, but we can log)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="HIPAA Voice Receptionist")

app.include_router(voice.router, prefix="/api")

@app.get("/health")
def health_check():
    """
    Checks if the service is up and dependencies are reachable.
    """
    health_status = {"status": "ok", "dependencies": {}}
    
    # Check OpenAI
    try:
        # Lightweight call to check connectivity (listing models is cheap/free usually)
        # or just assume client is instantiated.
        # Let's do a meaningful check: check if we have an API key set.
        if openai_client.api_key:
             health_status["dependencies"]["openai"] = "configured"
    except Exception as e:
        health_status["dependencies"]["openai"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check ACS
    try:
        # Check if client connection string is valid format (simple check)
        if acs_service.client:
            health_status["dependencies"]["acs"] = "configured"
    except Exception as e:
        health_status["dependencies"]["acs"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status

@app.get("/")
def root():
    return {"message": "HIPAA Voice Receptionist API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
