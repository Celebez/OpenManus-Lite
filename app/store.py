"""Pluggable memory / state storage (Hermes-style extensibility).

OpenManus-Lite runs with **zero setup** by default: memory is in-memory and
ephemeral (lives for one agent run). If a user wants durable memory — across
runs, sessions, or a shared store — they plug in a backend here.

Backends shipped:
  - InMemoryStore : default, no deps, nothing to configure.
  - SqliteStore    : stdlib sqlite3, file-backed, zero extra deps.

Users can add their own (Postgres, Redis, a vector DB, a file tree, whatever)
by subclassing ``StoreBackend`` and registering it in ``STORE_BACKENDS`` or
passing it directly to ``get_store()``. Nothing in the framework forces a
backend — the default path never touches disk.

Enable in config.toml / config.example.toml:

    [store]
    type = "sqlite"          # "memory" (default) | "sqlite" | <custom>
    path = "memory.db"       # backend-specific options

Or via env: OML_STORE_TYPE=sqlite OML_STORE_PATH=memory.db
"""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any, Dict, Optional

from app.config import config

# --------------------------------------------------------------------------
# Backend interface
# --------------------------------------------------------------------------


class StoreBackend:
    """Minimal key/value + list interface a memory backend must implement.

    Users subclass this to add Postgres, Redis, a vector store, a JSON file,
    or anything else. Only get/set/list are required; everything else is
    opt-in. The framework never assumes a specific backend.
    """

    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def set(self, key: str, value: str) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def keys(self, prefix: str = "") -> list[str]:
        raise NotImplementedError

    def close(self) -> None:
        """Release resources (connections, file handles). Default: no-op."""
        return None


# --------------------------------------------------------------------------
# Built-in backends
# --------------------------------------------------------------------------


class InMemoryStore(StoreBackend):
    """Default backend. Ephemeral, process-local, nothing persisted."""

    def __init__(self, **kwargs: Any) -> None:
        self._data: Dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def keys(self, prefix: str = "") -> list[str]:
        with self._lock:
            return [k for k in self._data if k.startswith(prefix)]


class SqliteStore(StoreBackend):
    """File-backed store using the stdlib sqlite3 module (no extra deps).

    Users who want durability without a server start here. Swap for Postgres
    by writing a ``PostgresStore(StoreBackend)`` with the same methods.
    """

    def __init__(self, path: str = "memory.db", **kwargs: Any) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE key=?", (key,)
            ).fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO kv(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self._conn.commit()

    def delete(self, key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM kv WHERE key=?", (key,))
            self._conn.commit()

    def keys(self, prefix: str = "") -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key FROM kv WHERE key LIKE ?", (prefix + "%",)
            ).fetchall()
            return [r[0] for r in rows]

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Registry + factory
# --------------------------------------------------------------------------

STORE_BACKENDS: Dict[str, type[StoreBackend]] = {
    "memory": InMemoryStore,
    "sqlite": SqliteStore,
}


def get_store() -> StoreBackend:
    """Return the configured store backend.

    Resolution order: env OML_STORE_TYPE -> [store] section in config ->
    "memory" (default). Unknown types fall back to in-memory with a warning.
    """
    store_type = os.environ.get("OML_STORE_TYPE")
    opts: Dict[str, Any] = {}
    cfg_store = getattr(config, "store", None)
    if cfg_store and getattr(cfg_store, "type", None):
        store_type = store_type or cfg_store.type
        opts = dict(getattr(cfg_store, "options", None) or {})
    store_type = (store_type or "memory").lower()

    # env path overrides any file-based backend option
    if os.environ.get("OML_STORE_PATH"):
        opts["path"] = os.environ["OML_STORE_PATH"]

    backend_cls = STORE_BACKENDS.get(store_type)
    if backend_cls is None:
        # User-supplied custom backend not registered: fall back safely.
        import logging

        logging.getLogger("openmanus_lite").warning(
            f"Unknown store type '{store_type}', falling back to in-memory."
        )
        backend_cls = InMemoryStore
    return backend_cls(**opts)
