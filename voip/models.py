from enum import Enum
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VOIPMessageType(str, Enum):
    CALL_REQUEST = "call_request"
    CALL_ACCEPT = "call_accept"
    CALL_REJECT = "call_reject"
    CALL_END = "call_end"
    SDP_OFFER = "sdp_offer"
    SDP_ANSWER = "sdp_answer"
    ICE_CANDIDATE = "ice_candidate"
    CALL_BUSY = "call_busy"
    CALL_TIMEOUT = "call_timeout"
    CALL_ERROR = "call_error"


class VOIPMessage(BaseModel):
    type: VOIPMessageType
    from_user: str
    to_user: str
    payload: Optional[dict] = None
    timestamp: str = ""
    call_id: Optional[str] = None
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().strftime("%H:%M:%S")
        super().__init__(**data)
    
    def to_json(self) -> str:
        return self.model_dump_json()
