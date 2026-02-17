from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class CallState(str, Enum):
    IDLE = "idle"
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    ACTIVE = "active"
    ENDED = "ended"


class CallSession:
    def __init__(
        self,
        caller: str,
        callee: str,
        call_type: str = "audio",
        call_id: Optional[str] = None
    ):
        self.call_id = call_id or str(uuid.uuid4())
        self.caller = caller
        self.callee = callee
        self.call_type = call_type
        self.state = CallState.IDLE
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
    
    def start(self) -> None:
        self.state = CallState.ACTIVE
        self.started_at = datetime.now()
    
    def end(self) -> None:
        self.state = CallState.ENDED
        self.ended_at = datetime.now()
    
    def set_outgoing(self) -> None:
        self.state = CallState.OUTGOING
    
    def set_incoming(self) -> None:
        self.state = CallState.INCOMING
    
    @property
    def duration(self) -> Optional[int]:
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None
    
    def to_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "caller": self.caller,
            "callee": self.callee,
            "call_type": self.call_type,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
        }


class SignalingManager:
    def __init__(self):
        self._pending_calls: dict[str, CallSession] = {}
        self._active_calls: dict[str, CallSession] = {}
        self._user_calls: dict[str, str] = {}
    
    def create_call(self, caller: str, callee: str, call_type: str = "audio") -> CallSession:
        session = CallSession(caller=caller, callee=callee, call_type=call_type)
        session.set_outgoing()
        self._pending_calls[session.call_id] = session
        self._user_calls[caller] = session.call_id
        return session
    
    def accept_call(self, call_id: str) -> Optional[CallSession]:
        if call_id not in self._pending_calls:
            return None
        
        session = self._pending_calls.pop(call_id)
        session.start()
        self._active_calls[call_id] = session
        self._user_calls[session.callee] = call_id
        return session
    
    def reject_call(self, call_id: str) -> Optional[CallSession]:
        if call_id not in self._pending_calls:
            return None
        
        session = self._pending_calls.pop(call_id)
        session.end()
        if session.caller in self._user_calls:
            del self._user_calls[session.caller]
        return session
    
    def end_call(self, call_id: str) -> Optional[CallSession]:
        session = None
        
        if call_id in self._pending_calls:
            session = self._pending_calls.pop(call_id)
        elif call_id in self._active_calls:
            session = self._active_calls.pop(call_id)
        
        if session:
            session.end()
            if session.caller in self._user_calls:
                del self._user_calls[session.caller]
            if session.callee in self._user_calls:
                del self._user_calls[session.callee]
        
        return session
    
    def get_call(self, call_id: str) -> Optional[CallSession]:
        return self._pending_calls.get(call_id) or self._active_calls.get(call_id)
    
    def get_user_active_call(self, username: str) -> Optional[CallSession]:
        call_id = self._user_calls.get(username)
        if call_id:
            return self.get_call(call_id)
        return None
    
    def is_user_busy(self, username: str) -> bool:
        return username in self._user_calls
    
    def get_pending_call_for_user(self, username: str) -> Optional[CallSession]:
        for session in self._pending_calls.values():
            if session.callee == username:
                return session
        return None
    
    def cleanup_user(self, username: str) -> list[CallSession]:
        ended_sessions = []
        
        call_id = self._user_calls.get(username)
        if call_id:
            session = self.end_call(call_id)
            if session:
                ended_sessions.append(session)
        
        for call_id, session in list(self._pending_calls.items()):
            if session.callee == username:
                ended = self.reject_call(call_id)
                if ended:
                    ended_sessions.append(ended)
        
        return ended_sessions
