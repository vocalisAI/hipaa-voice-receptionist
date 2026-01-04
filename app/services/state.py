from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime

class CallStage(Enum):
    CONNECTING = "connecting"
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING_QUERY = "processing_query"
    RESPONDING = "responding"
    ENDING = "ending"

class CallState:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.stage: CallStage = CallStage.CONNECTING
        self.last_prompt: Optional[str] = None
        self.retry_count: int = 0
        self.max_retries: int = 3
        self.start_time: datetime = datetime.utcnow()
        self.messages: list = [] # Keep conversation history for context (HIPAA: be careful not to log this persistent, just in memory)
    
    def log_state(self):
        # HIPAA Safe log - no content
        print(f"[{datetime.utcnow().isoformat()}] Call {self.connection_id}: Stage={self.stage.value}, Retries={self.retry_count}")

# Global In-Memory State
# Key: call_connection_id, Value: CallState object
_CALL_STORE: Dict[str, CallState] = {}

def get_call_state(connection_id: str) -> Optional[CallState]:
    return _CALL_STORE.get(connection_id)

def create_call_state(connection_id: str) -> CallState:
    state = CallState(connection_id)
    _CALL_STORE[connection_id] = state
    print(f"Call State Created: {connection_id}")
    return state

def update_call_stage(connection_id: str, stage: CallStage):
    state = get_call_state(connection_id)
    if state:
        state.stage = stage
        state.log_state()

def clear_call_state(connection_id: str):
    if connection_id in _CALL_STORE:
        del _CALL_STORE[connection_id]
        print(f"Call State Cleared: {connection_id}")
