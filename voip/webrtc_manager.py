from typing import Optional
import logging
import json
from fastapi import WebSocket
from .signaling import SignalingManager, CallSession, CallState
from .models import VOIPMessage, VOIPMessageType

logger = logging.getLogger(__name__)


class WebRTCManager:
    def __init__(self):
        self.signaling = SignalingManager()
        self._connections: dict[str, WebSocket] = {}
    
    def register_connection(self, username: str, websocket: WebSocket) -> None:
        self._connections[username] = websocket
        logger.info(f"VOIP connection registered for user: {username}")
    
    def unregister_connection(self, username: str) -> None:
        if username in self._connections:
            del self._connections[username]
            logger.info(f"VOIP connection unregistered for user: {username}")
        
        ended_sessions = self.signaling.cleanup_user(username)
        for session in ended_sessions:
            other_user = session.callee if session.caller == username else session.caller
            if other_user in self._connections:
                asyncio.create_task(
                    self._send_message(
                        other_user,
                        VOIPMessage(
                            type=VOIPMessageType.CALL_END,
                            from_user=username,
                            to_user=other_user,
                            call_id=session.call_id
                        )
                    )
                )
    
    async def _send_message(self, to_user: str, message: VOIPMessage) -> bool:
        if to_user not in self._connections:
            logger.warning(f"User {to_user} not connected for VOIP")
            return False
        
        try:
            websocket = self._connections[to_user]
            await websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.error(f"Failed to send VOIP message to {to_user}: {e}")
            return False
    
    async def handle_message(self, websocket: WebSocket, username: str, data: dict) -> None:
        try:
            msg_type_str = data.get("type")
            if not msg_type_str:
                logger.warning("VOIP message missing type")
                return
            
            msg_type = VOIPMessageType(msg_type_str)
            
            if msg_type == VOIPMessageType.CALL_REQUEST:
                await self._handle_call_request(websocket, username, data)
            elif msg_type == VOIPMessageType.CALL_ACCEPT:
                await self._handle_call_accept(websocket, username, data)
            elif msg_type == VOIPMessageType.CALL_REJECT:
                await self._handle_call_reject(websocket, username, data)
            elif msg_type == VOIPMessageType.CALL_END:
                await self._handle_call_end(websocket, username, data)
            elif msg_type == VOIPMessageType.SDP_OFFER:
                await self._handle_sdp_offer(websocket, username, data)
            elif msg_type == VOIPMessageType.SDP_ANSWER:
                await self._handle_sdp_answer(websocket, username, data)
            elif msg_type == VOIPMessageType.ICE_CANDIDATE:
                await self._handle_ice_candidate(websocket, username, data)
            else:
                logger.warning(f"Unknown VOIP message type: {msg_type}")
        
        except ValueError as e:
            logger.error(f"Invalid VOIP message type: {e}")
        except Exception as e:
            logger.error(f"Error handling VOIP message: {e}")
    
    async def _handle_call_request(self, websocket: WebSocket, username: str, data: dict) -> None:
        to_user = data.get("to_user")
        call_type = data.get("call_type", "audio")
        
        if not to_user:
            await self._send_error(websocket, username, "Missing target user")
            return
        
        if self.signaling.is_user_busy(username):
            await self._send_message(
                username,
                VOIPMessage(
                    type=VOIPMessageType.CALL_ERROR,
                    from_user="system",
                    to_user=username,
                    payload={"error": "You already have an active call"}
                )
            )
            return
        
        if self.signaling.is_user_busy(to_user):
            await self._send_message(
                username,
                VOIPMessage(
                    type=VOIPMessageType.CALL_BUSY,
                    from_user=to_user,
                    to_user=username
                )
            )
            return
        
        session = self.signaling.create_call(
            caller=username,
            callee=to_user,
            call_type=call_type
        )
        
        await self._send_message(
            to_user,
            VOIPMessage(
                type=VOIPMessageType.CALL_REQUEST,
                from_user=username,
                to_user=to_user,
                call_id=session.call_id,
                payload={"call_type": call_type}
            )
        )
        
        logger.info(f"Call request from {username} to {to_user} ({call_type})")
    
    async def _handle_call_accept(self, websocket: WebSocket, username: str, data: dict) -> None:
        call_id = data.get("call_id")
        
        if not call_id:
            await self._send_error(websocket, username, "Missing call_id")
            return
        
        session = self.signaling.accept_call(call_id)
        if not session:
            await self._send_error(websocket, username, "Call not found or already ended")
            return
        
        await self._send_message(
            session.caller,
            VOIPMessage(
                type=VOIPMessageType.CALL_ACCEPT,
                from_user=username,
                to_user=session.caller,
                call_id=call_id
            )
        )
        
        logger.info(f"Call {call_id} accepted by {username}")
    
    async def _handle_call_reject(self, websocket: WebSocket, username: str, data: dict) -> None:
        call_id = data.get("call_id")
        
        if not call_id:
            await self._send_error(websocket, username, "Missing call_id")
            return
        
        session = self.signaling.reject_call(call_id)
        if not session:
            await self._send_error(websocket, username, "Call not found")
            return
        
        await self._send_message(
            session.caller,
            VOIPMessage(
                type=VOIPMessageType.CALL_REJECT,
                from_user=username,
                to_user=session.caller,
                call_id=call_id
            )
        )
        
        logger.info(f"Call {call_id} rejected by {username}")
    
    async def _handle_call_end(self, websocket: WebSocket, username: str, data: dict) -> None:
        call_id = data.get("call_id")
        
        if not call_id:
            await self._send_error(websocket, username, "Missing call_id")
            return
        
        session = self.signaling.end_call(call_id)
        if not session:
            return
        
        other_user = session.callee if session.caller == username else session.caller
        
        await self._send_message(
            other_user,
            VOIPMessage(
                type=VOIPMessageType.CALL_END,
                from_user=username,
                to_user=other_user,
                call_id=call_id
            )
        )
        
        logger.info(f"Call {call_id} ended by {username}")
    
    async def _handle_sdp_offer(self, websocket: WebSocket, username: str, data: dict) -> None:
        to_user = data.get("to_user")
        sdp = data.get("sdp")
        call_id = data.get("call_id")
        
        if not to_user or not sdp:
            await self._send_error(websocket, username, "Missing SDP offer data")
            return
        
        await self._send_message(
            to_user,
            VOIPMessage(
                type=VOIPMessageType.SDP_OFFER,
                from_user=username,
                to_user=to_user,
                call_id=call_id,
                payload={"sdp": sdp}
            )
        )
    
    async def _handle_sdp_answer(self, websocket: WebSocket, username: str, data: dict) -> None:
        to_user = data.get("to_user")
        sdp = data.get("sdp")
        call_id = data.get("call_id")
        
        if not to_user or not sdp:
            await self._send_error(websocket, username, "Missing SDP answer data")
            return
        
        await self._send_message(
            to_user,
            VOIPMessage(
                type=VOIPMessageType.SDP_ANSWER,
                from_user=username,
                to_user=to_user,
                call_id=call_id,
                payload={"sdp": sdp}
            )
        )
    
    async def _handle_ice_candidate(self, websocket: WebSocket, username: str, data: dict) -> None:
        to_user = data.get("to_user")
        candidate = data.get("candidate")
        call_id = data.get("call_id")
        
        if not to_user or not candidate:
            await self._send_error(websocket, username, "Missing ICE candidate data")
            return
        
        await self._send_message(
            to_user,
            VOIPMessage(
                type=VOIPMessageType.ICE_CANDIDATE,
                from_user=username,
                to_user=to_user,
                call_id=call_id,
                payload={"candidate": candidate}
            )
        )
    
    async def _send_error(self, websocket: WebSocket, username: str, error_msg: str) -> None:
        await self._send_message(
            username,
            VOIPMessage(
                type=VOIPMessageType.CALL_ERROR,
                from_user="system",
                to_user=username,
                payload={"error": error_msg}
            )
        )


import asyncio
