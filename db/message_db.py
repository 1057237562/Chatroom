"""
SQLite database module for persisting and querying chat messages.
"""

import sqlite3
import aiosqlite
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Database path
DB_PATH = "chatroom.db"


class MessageDB:
    """Database manager for chat messages."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._initialized = False
    
    async def init(self) -> None:
        """Initialize database with required tables and indices."""
        if self._initialized:
            return
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create messages table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        message_type TEXT DEFAULT 'normal',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indices for performance
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_username 
                    ON chat_messages(username)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON chat_messages(timestamp)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at 
                    ON chat_messages(created_at DESC)
                """)
                
                await db.commit()
                self._initialized = True
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def save_message(
        self,
        username: str,
        content: str,
        timestamp: str,
        message_type: str = "normal"
    ) -> bool:
        """
        Save a chat message to database.
        
        Args:
            username: Username of the sender
            content: Message content
            timestamp: Timestamp string (HH:MM:SS format)
            message_type: Type of message (default: 'normal')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO chat_messages 
                    (username, content, timestamp, message_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, content, timestamp, message_type)
                )
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    async def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        username: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        keyword: str | None = None
    ) -> tuple[list[dict], int]:
        """
        Retrieve chat history with optional filters.
        
        Args:
            limit: Number of messages to retrieve
            offset: Pagination offset
            username: Filter by username (optional)
            start_time: Filter by start timestamp (format: YYYY-MM-DD HH:MM:SS)
            end_time: Filter by end timestamp (format: YYYY-MM-DD HH:MM:SS)
            keyword: Filter by keyword in content (optional)
            
        Returns:
            Tuple of (messages list, total count)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Build query
                query = "SELECT * FROM chat_messages WHERE 1=1"
                params = []
                
                if username:
                    query += " AND username = ?"
                    params.append(username)
                
                if start_time:
                    query += " AND created_at >= ?"
                    params.append(start_time)
                
                if end_time:
                    query += " AND created_at <= ?"
                    params.append(end_time)
                
                if keyword:
                    query += " AND content LIKE ?"
                    params.append(f"%{keyword}%")
                
                # Get total count
                count_query = f"SELECT COUNT(*) FROM ({query})"
                count_cursor = await db.execute(count_query, params)
                total = await count_cursor.fetchone()
                total_count = total[0] if total else 0
                
                # Get paginated results ordered by newest first
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                # Convert to dict format
                messages = []
                for row in rows:
                    messages.append({
                        'id': row[0],
                        'username': row[1],
                        'content': row[2],
                        'timestamp': row[3],
                        'message_type': row[4],
                        'created_at': row[5]
                    })
                
                # Reverse to get chronological order
                messages.reverse()
                return messages, total_count
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")
            return [], 0
    
    async def get_total_count(self) -> int:
        """Get total number of messages in database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM chat_messages")
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get total count: {e}")
            return 0


# Global instance
_db_instance: MessageDB | None = None


def get_message_db() -> MessageDB:
    """Get or create global MessageDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = MessageDB()
    return _db_instance


async def init_db() -> MessageDB:
    """Initialize and return the message database."""
    db = get_message_db()
    await db.init()
    return db


async def save_message(
    username: str,
    content: str,
    timestamp: str,
    message_type: str = "normal"
) -> bool:
    """Convenience function to save message."""
    db = get_message_db()
    return await db.save_message(username, content, timestamp, message_type)


async def get_history(
    limit: int = 50,
    offset: int = 0,
    username: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    keyword: str | None = None
) -> tuple[list[dict], int]:
    """Convenience function to get history."""
    db = get_message_db()
    return await db.get_history(limit, offset, username, start_time, end_time, keyword)
