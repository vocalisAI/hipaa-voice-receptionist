from azure.communication.callautomation import (
    CallAutomationClient,
    CallInvite,
    CallConnection,
    TextSource,
    SsmlSource,
    CallMediaRecognizeSpeechOptions,
    RecognizeInputType,
    PhoneNumberIdentifier
)
from app.core.config import settings
from app.services.speech import generate_ssml

class ACSService:
    def __init__(self):
        self.client = CallAutomationClient.from_connection_string(settings.ACS_CONNECTION_STRING)

    def get_call_connection(self, call_connection_id: str) -> CallConnection:
        return self.client.get_call_connection(call_connection_id)

    def answer_call(self, incoming_call_context: str, callback_uri: str):
        self.client.answer_call(incoming_call_context, callback_uri)

    def play_text(self, call_connection_id: str, text: str):
        """
        Synthesizes text to speech (using Azure Speech via ACS) and plays it.
        Using SSML for better control.
        """
        ssml = generate_ssml(text)
        target = SsmlSource(ssml_text=ssml)
        
        call_connection = self.get_call_connection(call_connection_id)
        # We assume one participant (the caller) is the target, but play_media_to_all is safer/easier for 1:1
        call_connection.play_media_to_all(target)

    def recognize_speech(self, call_connection_id: str):
        """
        Starts listening for speech input.
        """
        call_connection = self.get_call_connection(call_connection_id)
        
        # Configure speech recognition
        # We want to stop recognizing when the user pauses (endpointing)
        recognize_options = CallMediaRecognizeSpeechOptions(
            target_participant=PhoneNumberIdentifier("+1..."), # Caller ID is dynamic, actually better to use 'any' or capture from event
            # Logic: We usually target the caller. But 'recognize' on the connection needs a target.
            # However, ACS helper usually infers target if not passed, OR we grab it from state.
            # Simplified: ACS Python SDK 'start_recognizing_media' usually takes 'target_participant'.
            # We'll fix this in the main flow by passing the caller ID from the event data.
        )
        # REVISION: We need the caller's identifier to target them specifically.
        # So we will change the signature to accept target_participant.
        pass

    def recognize_from_caller(self, call_connection_id: str, caller_id: str):
        call_connection = self.get_call_connection(call_connection_id)
        
        # Use PhoneNumberIdentifier or CommunicationUserIdentifier based on caller format
        # For PSTN it's PhoneNumberIdentifier.
        # We can construct it blindly from the raw ID string if we are careful, 
        # but the SDK might need the object.
        # Simpler approach: Event Payload -> 'from' field -> Identifier object.
        
        # Note: In a real app, we parse the raw dictionary back to an Identifier. 
        # For now, we will assume caller_id is a PhoneNumberIdentifier object or we construct one.
        target = PhoneNumberIdentifier(caller_id)

        recognize_options = CallMediaRecognizeSpeechOptions(
            target_participant=target,
            end_silence_timeout=2 # Wait 2s of silence to consider input done
        )
        
        call_connection.start_recognizing_media(
            input_type=RecognizeInputType.SPEECH,
            target_participant=target,
            speech_language="en-US", # Can be configurable
            recognize_options=recognize_options
        )

    def hang_up(self, call_connection_id: str):
        call_connection = self.get_call_connection(call_connection_id)
        call_connection.hang_up(is_for_everyone=True)

acs_service = ACSService()
