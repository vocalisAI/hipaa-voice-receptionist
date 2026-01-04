from fastapi import FastAPI
from app.routes import voice
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Initialize App
app = FastAPI()

# Include Routes
app.include_router(voice.router, prefix="/api")

# Startup Event (Optional: Check config)
@app.on_event("startup")
async def startup_event():
    from app.core.config import settings
    logger.info("Application starting up...")
    logger.info(f"ACS Connection String present: {bool(settings.ACS_CONNECTION_STRING)}")
    logger.info(f"OpenAI Key present: {bool(settings.AZURE_OPENAI_KEY)}")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"message": "HIPAA Voice Receptionist API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
