from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CollectionMigrationSummary:
    collection: str
    run_id: str
    dry_run: bool
    scanned: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    unresolved: int = 0
    malformed: int = 0
    conflicts: int = 0
    validation_failures: int = 0
    batches: int = 0
    start_after_id: Optional[str] = None
    last_processed_id: Optional[str] = None
    started_at: datetime = field(default_factory=utcnow)
    ended_at: Optional[datetime] = None
    unresolved_examples: list[dict[str, Any]] = field(default_factory=list)
    malformed_examples: list[dict[str, Any]] = field(default_factory=list)
    conflict_examples: list[dict[str, Any]] = field(default_factory=list)

    def finish(self):
        self.ended_at = utcnow()

    def add_unresolved(self, *, record_id: str, reason: str, **details: Any):
        self.unresolved += 1
        if len(self.unresolved_examples) < 25:
            self.unresolved_examples.append({"record_id": record_id, "reason": reason, **details})

    def add_malformed(self, *, record_id: str, reason: str, **details: Any):
        self.malformed += 1
        if len(self.malformed_examples) < 25:
            self.malformed_examples.append({"record_id": record_id, "reason": reason, **details})

    def add_conflict(self, *, record_id: str, reason: str, **details: Any):
        self.conflicts += 1
        if len(self.conflict_examples) < 25:
            self.conflict_examples.append({"record_id": record_id, "reason": reason, **details})

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["ended_at"] = self.ended_at.isoformat() if self.ended_at else None
        return data


@dataclass
class BackfillReport:
    run_id: str
    dry_run: bool
    started_at: datetime = field(default_factory=utcnow)
    ended_at: Optional[datetime] = None
    collections: dict[str, CollectionMigrationSummary] = field(default_factory=dict)

    def add_summary(self, summary: CollectionMigrationSummary):
        self.collections[summary.collection] = summary

    def finish(self):
        self.ended_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dry_run": self.dry_run,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "collections": {name: summary.to_dict() for name, summary in self.collections.items()},
        }


@dataclass
class ParitySummary:
    run_id: str
    started_at: datetime = field(default_factory=utcnow)
    ended_at: Optional[datetime] = None
    sections: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_section(self, name: str, data: dict[str, Any]):
        self.sections[name] = data

    def finish(self):
        self.ended_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "sections": self.sections,
        }
