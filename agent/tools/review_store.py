"""
Simple storage for review records.
"""
import json
from pathlib import Path
from uuid import uuid4
from agent.models import ReviewRecord


class ReviewStorage:
    """Manages review record storage."""

    def __init__(self, storage_dir: str = "data/reviews"):
        self.storage_path = Path(storage_dir)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def generate_id(self) -> str:
        """Generate unique review ID."""
        return f"review-{uuid4().hex[:8]}"

    def _file_path(self, review_id: str) -> Path:
        """Get file path for review ID."""
        return self.storage_path / f"{review_id}.json"

    def save(self, record: ReviewRecord) -> None:
        """Save review record."""
        path = self._file_path(record.review_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(record.serialize(), f, indent=2)

    def load(self, review_id: str) -> ReviewRecord:
        """Load review record."""
        path = self._file_path(review_id)
        if not path.exists():
            raise FileNotFoundError(f"Review {review_id} not found")
        
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ReviewRecord.deserialize(data)

    def list_all(self) -> list[ReviewRecord]:
        """List all reviews."""
        records = []
        for path in self.storage_path.glob("*.json"):
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            records.append(ReviewRecord.deserialize(data))
        return records
