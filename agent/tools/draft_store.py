"""
Simple storage for draft records.
"""
import json
from pathlib import Path
from uuid import uuid4
from agent.models import DraftRecord


class DraftStorage:
    """Manages draft record storage."""

    def __init__(self, storage_dir: str = "data/drafts"):
        self.storage_path = Path(storage_dir)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_id() -> str:
        """Generate unique draft ID."""
        return f"draft-{uuid4().hex[:8]}"

    def _file_path(self, draft_id: str) -> Path:
        """Get file path for draft ID."""
        return self.storage_path / f"{draft_id}.json"

    def save(self, record: DraftRecord) -> None:
        """Save draft record."""
        path = self._file_path(record.draft_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(record.serialize(), f, indent=2)

    def load(self, draft_id: str) -> DraftRecord:
        """Load draft record."""
        path = self._file_path(draft_id)
        if not path.exists():
            raise FileNotFoundError(f"Draft {draft_id} not found")
        
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return DraftRecord.deserialize(data)

    def update(self, record: DraftRecord) -> None:
        """Update draft record."""
        self.save(record)

    def list_all(self) -> list[DraftRecord]:
        """List all drafts."""
        records = []
        for path in self.storage_path.glob("*.json"):
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            records.append(DraftRecord.deserialize(data))
        return records
