from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EntryType(str, Enum):
    NOTE = "note"
    ACTION = "action"
    DECISION = "decision"
    WAITING = "waiting"


class EntryStatus(str, Enum):
    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Entry:
    id: str
    ts: str
    project: str
    type: EntryType
    text: str
    meeting: Optional[str] = None
    due: Optional[str] = None
    status: Optional[EntryStatus] = None
    person: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    updated_ts: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.id,
            "ts": self.ts,
            "project": self.project,
            "type": self.type.value,
            "text": self.text,
        }
        if self.meeting is not None:
            d["meeting"] = self.meeting
        if self.due is not None:
            d["due"] = self.due
        if self.status is not None:
            d["status"] = self.status.value
        if self.person is not None:
            d["person"] = self.person
        if self.tags:
            d["tags"] = self.tags
        if self.updated_ts is not None:
            d["updated_ts"] = self.updated_ts
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Entry:
        return cls(
            id=d["id"],
            ts=d["ts"],
            project=d["project"],
            type=EntryType(d["type"]),
            text=d["text"],
            meeting=d.get("meeting"),
            due=d.get("due"),
            status=EntryStatus(d["status"]) if d.get("status") else None,
            person=d.get("person"),
            tags=d.get("tags", []),
            updated_ts=d.get("updated_ts"),
        )

    @staticmethod
    def make_id() -> str:
        return uuid.uuid4().hex[:4]

    @staticmethod
    def now_ts() -> str:
        return datetime.now().strftime("%Y-%m-%dT%H:%M")
