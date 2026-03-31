from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astra.types import Usage

DEFAULT_SESSION_DIR = Path.home() / ".astra" / "sessions"


class SessionStorage:
    def __init__(self, session_dir: Path | None = None) -> None:
        self.session_dir = session_dir or DEFAULT_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, messages: list[dict], usage: Usage) -> str:
        path = self.session_dir / f"{session_id}.json"
        data = {
            "session_id": session_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "messages": messages,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
        }
        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)

    def load(self, session_id: str) -> dict[str, Any]:
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        return json.loads(path.read_text())

    def list_sessions(self) -> list[dict[str, str]]:
        sessions = []
        for p in sorted(self.session_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(p.read_text())
                sessions.append(
                    {
                        "id": data.get("session_id", p.stem),
                        "saved_at": data.get("saved_at", "unknown"),
                    }
                )
            except Exception:
                pass
        return sessions
