# HIPAA-Compliant AI Voice Receptionist

This project implements a stateless, HIPAA-compliant backend for an AI voice receptionist using Azure Communication Services (ACS), Azure OpenAI, and Azure Speech Services.

## Architecture

- **Hosting**: Azure App Service (Linux / Python 3.13)
- **Telephony**: Azure Communication Services (Call Automation)
- **AI**: Azure OpenAI (GPT-4o-mini) with Guardrails
- **Speech**: Azure Speech Services (Neural TTS) for voice output
- **Framework**: FastAPI

## Features

- **Event-Driven Call Flow**: Handles incoming calls, speech recognition, and playback via ACS callbacks.
- **In-Memory State Management**: Tracks call stage (Greeting, Listening, Responding) without persistent storage for HIPAA compliance.
- **Guardrails**: System prompt restricts AI to non-medical queries.
- **Robustness**: Handles silence, timeouts, and retries.
- **FAQ Routing**: Fast path for common questions (Hours, Location) bypassing LLM.

## Environment Variables

Ensure these are set in your Azure App Service Configuration:

- `ACS_CONNECTION_STRING`: Connection string for your ACS resource.
- `AZURE_OPENAI_ENDPOINT`: Endpoint for Azure OpenAI.
- `AZURE_OPENAI_KEY`: API Key for Azure OpenAI.
- `AZURE_SPEECH_KEY`: Key for Azure Speech Service.
- `AZURE_SPEECH_REGION`: Region for Azure Speech Service.
- `CALLBACK_URI_HOST`: (Optional) Hostname of your deployed app (e.g. `https://my-voice-app.azurewebsites.net`). Used to construct callback URLs.

## Deployment

1. **Deploy to Azure App Service**:
   - Create a Python 3.13 Web App on Linux.
   - Connect this GitHub repository via Deployment Center.

2. **Configure Networking**:
   - Ensure the App Service uses a public endpoint reachable by ACS.
   - Set the `CALLBACK_URI_HOST` to your App Service URL.

3. **Map ACS**:
   - In ACS Event Grid or Call Automation settings (if applicable), or simply ensuring the code registers the callback URI correctly during `answer_call`.

## Local Development

1. Create a `.env` file with the required variables.
2. Run `pip install -r requirements.txt`.
3. Run `python main.py`.
4. Expose your local server via ngrok (`ngrok http 8000`) and update `CALLBACK_URI_HOST` to testing.

## Health Check

GET `/health` to verify service status and dependency configuration.
