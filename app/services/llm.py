from openai import AzureOpenAI
from app.core.config import settings

# FAQ Knowledge Base (Hardcoded for latency/reliability)
FAQ_KB = {
    "hours": "We are open Monday to Friday from 9 AM to 5 PM.",
    "timings": "We are open Monday to Friday from 9 AM to 5 PM.",
    "location": "We are located at 123 Health Way, Wellness City.",
    "address": "We are located at 123 Health Way, Wellness City.",
    "insurance": "We accept blue cross, aetna, and united healthcare.",
    "cost": "Consultations start at $150.",
}

# System Prompt with Guardrails
SYSTEM_PROMPT = """
You are a polite, professional medical clinic receptionist.
Your role is to help schedule appointments and answer basic questions.

GUARDRAILS:
1. DO NOT give medical advice or diagnosis. If the user asks for medical advice, say: "I cannot provide medical advice. Please speak with a doctor."
2. DO NOT hallucinate. stick to general clinic info.
3. Keep responses SHORT and CONVERSATIONAL (1-2 sentences max). This is for a voice call.
4. If asked about emergency symptoms (chest pain, trouble breathing), tell them to hang up and call 911 immediately.
5. If you do not understand, politely ask them to repeat.
"""

client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_KEY,
    api_version="2024-02-01",
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
)

def check_faq(text: str) -> str | None:
    text_lower = text.lower()
    for key, answer in FAQ_KB.items():
        if key in text_lower:
            return answer
    return None

def get_llm_response(user_text: str, conversation_history: list = None) -> str:
    # 1. Check FAQ first (Guardrail: Prevent unnecessary LLM calls)
    faq_response = check_faq(user_text)
    if faq_response:
        return faq_response

    # 2. Call LLM
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
             # Limit history to last 4 turns to keep context tight and cheap
            messages.extend(conversation_history[-4:])
        
        messages.append({"role": "user", "content": user_text})

        response = client.chat.completions.create(
            model="gpt-4o-mini", # Deployment name in Azure
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        return "I'm having trouble connecting to the system right now. Please try again later."
