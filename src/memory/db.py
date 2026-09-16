import json
import sqlite3
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from src.config import settings


class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Memória compartilhada entre bots (contexto, aprendizados, preferências)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)

            # Histórico de conversas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    agent_name TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Rotinas de automação salvas ("Show a Bot how it's done")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    prompt_template TEXT NOT NULL,
                    schedule TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Histórico de aprovações (Human-in-the-loop)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    status TEXT DEFAULT 'pending', -- pending, approved, rejected
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # --- Memórias Globais / Compartilhadas ---
    def set_memory(self, category: str, key: str, value: Any) -> None:
        val_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (category, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (category, key, val_str))
            conn.commit()

    def get_memory(self, category: str, key: str) -> Optional[Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM memories WHERE category = ? AND key = ?", (category, key))
            row = cursor.fetchone()
            if not row:
                return None
            try:
                return json.loads(row["value"])
            except Exception:
                return row["value"]

    def list_memories(self, category: Optional[str] = None) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute("SELECT category, key, value, updated_at FROM memories WHERE category = ?", (category,))
            else:
                cursor.execute("SELECT category, key, value, updated_at FROM memories ORDER BY category, key")
            results = []
            for row in cursor.fetchall():
                val = row["value"]
                try:
                    val = json.loads(val)
                except Exception:
                    pass
                results.append({
                    "category": row["category"],
                    "key": row["key"],
                    "value": val,
                    "updated_at": row["updated_at"]
                })
            return results

    # --- Histórico de Mensagens ---
    def add_message(self, session_id: str, role: str, content: str, agent_name: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (session_id, role, agent_name, content)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, agent_name, content))
            conn.commit()

    def get_messages(self, session_id: str, limit: int = 30) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, agent_name, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]

    # --- Rotinas ---
    def save_routine(self, name: str, description: str, prompt_template: str, schedule: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO routines (name, description, prompt_template, schedule)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    prompt_template = excluded.prompt_template,
                    schedule = excluded.schedule
            """, (name, description, prompt_template, schedule))
            conn.commit()

    def list_routines(self) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, prompt_template, schedule, enabled FROM routines")
            return [dict(r) for r in cursor.fetchall()]

    def get_routine(self, name: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, prompt_template, schedule, enabled FROM routines WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None


memory_store = MemoryStore()
