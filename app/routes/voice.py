from fastapi import APIRouter, Request, Response
from azure.communication.callautomation import CallAutomationEventParser
from app.services.acs import acs_service
from app.services import state, llm
from app.core.config import settings
import logging

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback callback URI if not set in config (e.g. for testing, but ACS needs a real one)
CALLBACK_URI = f"{settings.CALLBACK_URI_HOST}/api/callbacks"

@router.post("/callbacks")
async def acs_callback(request: Request):
    # Parse the CloudEvent from ACS
    payload = await request.json()
    # In some environments, payload might be a list or dict. ACS typically sends a list of events or single event.
    # The SDK parser handles the body/signature logic if we passed the raw request, 
    # but strictly speaking `parse_events` takes the body content.
    
    events = CallAutomationEventParser.parse_events(payload)
    
    for event in events:
        call_connection_id = event.call_connection_id
        logger.info(f"Received event: {type(event).__name__} for call {call_connection_id}")
        
        if event.type == "Microsoft.Communication.CallConnected":
            handle_call_connected(event)
            
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            handle_recognize_completed(event)
            
        elif event.type == "Microsoft.Communication.RecognizeFailed":
            handle_recognize_failed(event)
            
        elif event.type == "Microsoft.Communication.PlayCompleted":
            handle_play_completed(event)
            
        elif event.type == "Microsoft.Communication.CallDisconnected":
            state.clear_call_state(call_connection_id)
            
    return Response(status_code=200)

def handle_call_connected(event):
    call_connection_id = event.call_connection_id
    # Create State
    call_state = state.create_call_state(call_connection_id)
    state.update_call_stage(call_connection_id, state.CallStage.GREETING)
    
    # Capture caller ID for future 'recognize' usage
    # Note: Event object from SDK might have 'participants' or we assume 'from' from incoming call hook.
    # But for 'CallConnected', we don't always get the caller ID directly in the simplified event model 
    # unless we stored it from the 'IncomingCall' event (which hits a different webhook usually, or same).
    # FOR SIMPLICITY: We will assume we can get participants from the call connection or the event.
    
    # Workaround: App Service creates the call or answers it. 
    # If we answered, we should've stored the caller ID. 
    # BUT, the IncomingCall event is separate.
    # To keep it stateless helper, specific logic for 'Identify caller' is needed.
    # We will assume we just reply to the 'event.correlation_id' or invoke 'recognize' on the 'server call id' 
    # Actually 'recognize' needs a target. 
    # We'll use a trick: ACS can recognize from 'any' participant if we don't specify target (in some SDK versions)
    # OR we use the participants list from the event.
    
    greeting_text = "Hello, thanks for calling Wellness Clinic. How can I help you today?"
    call_state.last_prompt = greeting_text
    acs_service.play_text(call_connection_id, greeting_text)

def handle_play_completed(event):
    call_connection_id = event.call_connection_id
    call_state = state.get_call_state(call_connection_id)
    
    if not call_state:
        logger.warning(f"State lost for {call_connection_id}")
        return

    if call_state.stage == state.CallStage.ENDING:
        acs_service.hang_up(call_connection_id)
        return

    # If we just played a prompt, now we listen
    state.update_call_stage(call_connection_id, state.CallStage.LISTENING)
    
    # We need the caller ID to recognize. 
    # In a full impl, we'd store this during incoming/answer phase.
    # For now, we'll try to let ACS handle it or assume we saved it.
    # Let's assume we saved it in `call_state` during IncomingCall (if we handled it)
    # BUT IncomingCall handling is not shown here (it happens before CallConnected).
    # FIX: We will add an `IncomingCall` handler if this script is the answerer.
    # But often IncomingCall comes to Event Grid -> Webhook. 
    # Let's pretend we pass the caller phone number in `call_state` if possible.
    # Given the constraints, we will fetch participants from connection if needed, 
    # OR rely on `IncomingCall` webhook logic to populate the state.
    
    # HACK for "Recognize from Caller": 
    # We will try to fetch participants from the `acs_service.client.get_call_connection(id).get_call_connection_properties().source_identity` (maybe unavailable)
    # The most robust way is handling IncomingCall.
    
    # Let's assume we proceed with a Placeholder for caller_id logic
    # As usually: Event Grid -> Your Service (Answer) -> CallConnected
    
    # Re-using the caller object logic
    # We will just call 'recognize' and let the service helper deal with the 'target' 
    # (By default SDK requires it, we'll try a dummy or assume we fixed the service to use 'participants[0]')
    call_connection = acs_service.get_call_connection(call_connection_id)
    props = call_connection.get_call_connection_properties()
    # The 'targets' are usually the other person.
    target = props.targets[0] # The caller
    
    acs_service.recognize_from_caller(call_connection_id, target.raw_id)

def handle_recognize_completed(event):
    call_connection_id = event.call_connection_id
    call_state = state.get_call_state(call_connection_id)
    if not call_state: return

    # Get speech text
    text = event.recognize_result.text
    logger.info(f"User said: {text}")
    
    if not text:
        handle_recognize_failed(event) # Treat empty as failure
        return

    # Check for quit keywords to graceful exit
    if any(x in text.lower() for x in ["goodbye", "bye", "hang up"]):
        state.update_call_stage(call_connection_id, state.CallStage.ENDING)
        acs_service.play_text(call_connection_id, "Goodbye! Have a great day.")
        return

    state.update_call_stage(call_connection_id, state.CallStage.PROCESSING_QUERY)
    
    # Get AI Response
    response_text = llm.get_llm_response(text, call_state.messages)
    
    # Update History
    call_state.messages.append({"role": "user", "content": text})
    call_state.messages.append({"role": "assistant", "content": response_text})
    
    # Play Response
    state.update_call_stage(call_connection_id, state.CallStage.RESPONDING)
    call_state.last_prompt = response_text
    acs_service.play_text(call_connection_id, response_text)


def handle_recognize_failed(event):
    # Silence or No Match
    call_connection_id = event.call_connection_id
    call_state = state.get_call_state(call_connection_id)
    if not call_state: return
    
    call_state.retry_count += 1
    logger.info(f"Recognize failed. Retry {call_state.retry_count}")

    if call_state.retry_count > call_state.max_retries:
        state.update_call_stage(call_connection_id, state.CallStage.ENDING)
        acs_service.play_text(call_connection_id, "I am having trouble hearing you. Please call back later. Goodbye.")
        return

    # Re-prompt
    reprompt = "I didn't catch that. Could you please repeat?"
    if call_state.last_prompt and call_state.retry_count == 1:
        # First retry, maybe just repeat the specific question? 
        # Or just generic reprompt is safer.
        pass
        
    acs_service.play_text(call_connection_id, reprompt)

# ADDING Incoming Call Handler (Webhook for Event Grid triggers when call comes in)
# This is usually distinct from 'callbacks' which are for in-call events.
# But for simplicity, we map both or Assume Event Grid posts here too.
# The 'IncomingCall' event payload structure is slightly different.

@router.post("/incoming")
async def incoming_call_handler(request: Request):
    # Event Grid Validation Handshake (often required)
    # If validation event, respond appropriately.
    payload = await request.json()
    # Simple check for validation
    if isinstance(payload, list) and payload[0].get('eventType') == 'Microsoft.EventGrid.SubscriptionValidationEvent':
        code = payload[0]['data']['validationCode']
        return {"validationResponse": code}

    # Handle Incoming Call
    for event in payload:
        if event.get('eventType') == 'Microsoft.Communication.IncomingCall':
            data = event['data']
            incoming_call_context = data['incomingCallContext']
            caller_id = data['from']['rawId'] # Store this!
            
            # We can't easily create 'CallState' here because we don't have connection_id yet.
            # ACS AnswerCall returns connection_id, but it's async.
            # Best practice: Pass caller_id in 'callback_uri' query params? 
            # Or just wait for CallConnected and fetch participant then.
            # We will use the 'fetch participant' approach in CallConnected.
            
            # Answer
            acs_service.answer_call(incoming_call_context, CALLBACK_URI)
            logger.info("Answered incoming call.")
            
    return Response(status_code=200)
