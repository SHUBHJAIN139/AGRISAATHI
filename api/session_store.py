"""
AgriSaathi — SQLite Session Store
===================================
WHY: Farmers visit the app across multiple days. Session memory ensures
the AI remembers "you grow tomatoes on 1.5 acres near Pune" without
asking every time. SQLite is the local-dev backend; production swaps
to Firestore for scalability and replication.

This module provides an ADK-compatible session service backed by SQLite.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)

# WHY: Default database path. Created automatically on first use.
DEFAULT_DB_PATH = os.environ.get("SQLITE_DB_PATH", "./data/sessions.db")


class SQLiteSessionStore:
    """Async SQLite-backed session store for AgriSaathi.

    WHY: Provides persistent session memory across visits without
    requiring Google Cloud credentials. Compatible with ADK's
    SessionService interface pattern.

    Schema:
    - sessions: (session_id, user_id, app_name, created_at, updated_at, state)
    - state is a JSON blob containing conversation context
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Create the sessions table if it doesn't exist.

        WHY: Lazy initialization means the DB file is only created when
        first needed, not at import time.
        """
        if self._initialized:
            return

        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    app_name TEXT NOT NULL DEFAULT 'agri_saathi',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT '{}'
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions(user_id)
            """)
            await db.commit()

        self._initialized = True
        logger.info("session_store_initialized", db_path=self.db_path)

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        app_name: str = "agri_saathi",
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new session or return existing one.

        WHY: Idempotent — calling create_session with an existing session_id
        returns the existing session without modification. This prevents
        data loss if the frontend retries a failed session creation.
        """
        await self._ensure_initialized()

        now = datetime.now(timezone.utc).isoformat()
        state = json.dumps(initial_state or {}, ensure_ascii=False)

        async with aiosqlite.connect(self.db_path) as db:
            # Check if session already exists
            cursor = await db.execute(
                "SELECT session_id, user_id, app_name, created_at, updated_at, state "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()

            if row:
                logger.debug("session_exists", session_id=session_id)
                return {
                    "session_id": row[0],
                    "user_id": row[1],
                    "app_name": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                    "state": json.loads(row[5]),
                }

            # Create new session
            await db.execute(
                "INSERT INTO sessions (session_id, user_id, app_name, created_at, updated_at, state) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, user_id, app_name, now, now, state),
            )
            await db.commit()

        logger.info("session_created", session_id=session_id, user_id=user_id)
        return {
            "session_id": session_id,
            "user_id": user_id,
            "app_name": app_name,
            "created_at": now,
            "updated_at": now,
            "state": initial_state or {},
        }

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session by ID.

        WHY: Used by the API gateway to load session context before
        passing a message to the agent runner.
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT session_id, user_id, app_name, created_at, updated_at, state "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return {
                "session_id": row[0],
                "user_id": row[1],
                "app_name": row[2],
                "created_at": row[3],
                "updated_at": row[4],
                "state": json.loads(row[5]),
            }

    async def update_session_state(
        self,
        session_id: str,
        state_update: dict[str, Any],
    ) -> bool:
        """Merge new state into an existing session.

        WHY: After each agent interaction, we store the conversation context
        (detected language, farmer's crop, location, etc.) so the next visit
        doesn't start from scratch.
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            # Fetch current state
            cursor = await db.execute(
                "SELECT state FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning("session_not_found", session_id=session_id)
                return False

            current_state = json.loads(row[0])
            current_state.update(state_update)

            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "UPDATE sessions SET state = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps(current_state, ensure_ascii=False), now, session_id),
            )
            await db.commit()

        logger.debug("session_updated", session_id=session_id)
        return True

    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List all sessions for a user.

        WHY: Allows the frontend to show session history and let the
        farmer resume a previous conversation.
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT session_id, app_name, created_at, updated_at "
                "FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = await cursor.fetchall()

            return [
                {
                    "session_id": row[0],
                    "app_name": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                }
                for row in rows
            ]

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        WHY: GDPR-style right to deletion. A farmer should be able to
        delete their conversation history.
        """
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            await db.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info("session_deleted", session_id=session_id)
        return deleted
