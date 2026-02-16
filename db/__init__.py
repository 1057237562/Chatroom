"""
Database module for chat message persistence.
"""

from db.message_db import init_db, save_message, get_history, MessageDB

__all__ = ['init_db', 'save_message', 'get_history', 'MessageDB']
