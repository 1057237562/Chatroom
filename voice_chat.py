import asyncio
import logging
from typing import Optional
from fastapi import WebSocket
from collections import defaultdict

logger = logging.getLogger(__name__)


class VoiceRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.participants: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
    
    async def add_participant(self, username: str, websocket: WebSocket) -> None:
        async with self._lock:
            self.participants[username] = websocket
            logger.info(f"User {username} joined voice room {self.room_id}")
            await self._broadcast_user_list()
    
    async def remove_participant(self, username: str) -> None:
        async with self._lock:
            if username in self.participants:
                del self.participants[username]
                logger.info(f"User {username} left voice room {self.room_id}")
                await self._broadcast_user_list()
    
    async def _broadcast_user_list(self) -> None:
        user_list = list(self.participants.keys())
        message = {
            "type": "user_list",
            "users": user_list
        }
        await self._broadcast(message)
    
    async def _broadcast(self, message: dict, exclude: Optional[str] = None) -> None:
        disconnected = []
        for username, ws in self.participants.items():
            if username == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to {username}: {e}")
                disconnected.append(username)
        
        for username in disconnected:
            if username in self.participants:
                del self.participants[username]
    
    async def broadcast_audio(self, sender: str, audio_data: list) -> None:
        message = {
            "type": "audio",
            "from_user": sender,
            "data": audio_data
        }
        await self._broadcast(message, exclude=sender)
    
    def get_participants(self) -> list[str]:
        return list(self.participants.keys())
    
    def is_empty(self) -> bool:
        return len(self.participants) == 0


class VoiceChatManager:
    def __init__(self):
        self._rooms: dict[str, VoiceRoom] = {}
        self._user_rooms: dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def join_room(self, room_id: str, username: str, websocket: WebSocket) -> VoiceRoom:
        async with self._lock:
            if username in self._user_rooms:
                old_room_id = self._user_rooms[username]
                if old_room_id in self._rooms:
                    await self._rooms[old_room_id].remove_participant(username)
                    if self._rooms[old_room_id].is_empty():
                        del self._rooms[old_room_id]
            
            if room_id not in self._rooms:
                self._rooms[room_id] = VoiceRoom(room_id)
            
            room = self._rooms[room_id]
            self._user_rooms[username] = room_id
            await room.add_participant(username, websocket)
            
            return room
    
    async def leave_room(self, username: str) -> None:
        async with self._lock:
            if username in self._user_rooms:
                room_id = self._user_rooms[username]
                if room_id in self._rooms:
                    await self._rooms[room_id].remove_participant(username)
                    if self._rooms[room_id].is_empty():
                        del self._rooms[room_id]
                        logger.info(f"Room {room_id} deleted (empty)")
                del self._user_rooms[username]
    
    def get_room(self, room_id: str) -> Optional[VoiceRoom]:
        return self._rooms.get(room_id)
    
    def get_user_room(self, username: str) -> Optional[str]:
        return self._user_rooms.get(username)
    
    def get_all_rooms(self) -> dict[str, list[str]]:
        return {room_id: room.get_participants() for room_id, room in self._rooms.items()}
